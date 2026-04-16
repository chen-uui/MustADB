import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.management.base import CommandError

from pdf_processor.full_rag_service import full_rag_service
from pdf_processor.management.commands.build_gold_expansion_candidates import (
    Command as ExpansionBaseCommand,
)
from pdf_processor.management.commands.rerun_gold_extraction_eval import (
    Command as RerunGoldEvalCommand,
)
from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateVectorService


class Command(ExpansionBaseCommand):
    help = (
        "Rebuild a core-oriented candidate pool from the full processed PDF library, "
        "excluding gold_v3 and batch2 supporting, then export batch4 core-review candidates."
    )

    FINAL_COLUMNS = [
        "doc_id",
        "doc_name",
        "doc_filename",
        "doc_year",
        "doc_journal",
        "candidate_tags",
        "priority_score",
        "priority_reason",
        "pred_meteorite_name",
        "pred_organic_compounds_raw",
        "pred_organic_compounds_filtered",
        "pred_organic_compounds_projected",
        "pred_contamination_controls",
        "meteorite_evidence_snippet",
        "organic_evidence_snippet",
        "contamination_evidence_snippet",
        "batch4_core_likelihood",
        "batch4_scope_risk",
        "batch4_selection_reason",
    ]
    EXCLUDED_COLUMNS = FINAL_COLUMNS + ["exclusion_bucket", "exclusion_reason"]

    REQUIRED_SAMPLE_TERMS = (
        "meteorite",
        "meteorites",
        "micrometeorite",
        "micrometeorites",
        "chondrite",
        "chondrites",
        "carbonaceous",
        "ryugu",
        "bennu",
        "hayabusa",
        "osiris",
        "tissint",
        "murchison",
        "orgueil",
        "winchcombe",
        "allende",
        "tagish",
        "sutters mill",
        "nwa ",
        "eeta",
        "asteroid return",
    )
    ORGANIC_SIGNAL_TERMS = {
        "amino acid": 4,
        "amino acids": 4,
        "amine": 3,
        "nucleobase": 4,
        "pah": 4,
        "hydrocarbon": 3,
        "volatile organic": 4,
        "organic": 2,
        "organics": 2,
        "organic matter": 3,
        "sugar": 4,
        "ribose": 5,
        "hexamethylenetetramine": 5,
        "hmt": 4,
        "sulfur": 2,
        "sulfon": 3,
        "thiophene": 3,
    }
    ANALYTICAL_TITLE_TERMS = {
        "spectroscopy": 1,
        "isotope": 1,
        "chromatography": 1,
        "gc-ms": 1,
        "lc-ms": 1,
        "imaging": 1,
        "infrared": 1,
        "raman": 1,
    }
    HARD_EXCLUDE_TERMS = {
        "interstellar analog": "interstellar_analog",
        "analog ices": "interstellar_analog",
        "mars-analogue": "mars_analogue",
        "mars analogue": "mars_analogue",
        "model compounds": "model_compound",
        "witness coupon": "supporting_qc_or_curation",
        "sample return space missions": "supporting_qc_or_curation",
        "curation facility": "supporting_qc_or_curation",
        "quality control": "supporting_qc_or_curation",
        "contamination": "supporting_qc_or_curation",
        "survivability": "survivability_or_life_discussion",
        "perspective": "broad_review",
        "review": "broad_review",
        "comment": "comment_or_reply",
        "reply": "comment_or_reply",
    }
    SOFT_EXCLUDE_TERMS = {
        "nitrogen-rich ices": "analog_or_ice_simulation",
        "record": "broad_review_like",
        "history": "broad_review_like",
        "biogenicity": "broad_review_like",
        "biosignature": "life_discussion_or_detection",
        "detection microscopy": "life_discussion_or_detection",
        "ceres": "non_sample_body",
        "comet": "comet_boundary",
        "67p": "comet_boundary",
    }

    def add_arguments(self, parser):
        parser.add_argument("--gold-v3", type=str, required=True, help="Current official gold_seed_v3.csv path.")
        parser.add_argument(
            "--supporting-final",
            type=str,
            required=True,
            help="Supporting-final CSV path to exclude from the new pool.",
        )
        parser.add_argument("--limit", type=int, default=12, help="Final number of batch4 review candidates. Default: 12.")
        parser.add_argument(
            "--pool-size",
            type=int,
            default=28,
            help="How many metadata-ranked full-library docs to rerun before final filtering. Default: 28.",
        )
        parser.add_argument("--max-fetch-chunks", type=int, default=80, help="Max chunks fetched per doc. Default: 80.")
        parser.add_argument("--max-selected-chunks", type=int, default=3, help="Max selected chunks per field. Default: 3.")
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_batch4_core_review_<timestamp>",
        )

    def handle(self, *args, **options):
        gold_v3_csv = Path(str(options["gold_v3"])).expanduser().resolve()
        supporting_csv = Path(str(options["supporting_final"])).expanduser().resolve()
        if not gold_v3_csv.exists():
            raise CommandError(f"gold_v3 not found: {gold_v3_csv}")
        if not supporting_csv.exists():
            raise CommandError(f"supporting_final not found: {supporting_csv}")

        limit = int(options["limit"])
        pool_size = max(int(options["pool_size"]), limit)
        if limit < 1:
            raise CommandError("--limit must be >= 1")

        gold_rows = self._load_csv_rows(gold_v3_csv)
        supporting_rows = self._load_csv_rows(supporting_csv)
        excluded_doc_ids, excluded_titles = self._build_exclusion_sets(gold_rows + supporting_rows)

        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)

        csv_path = out_dir / "batch4_core_review_candidates.csv"
        xlsx_path = out_dir / "batch4_core_review_candidates.xlsx"
        excluded_csv_path = out_dir / "excluded_borderline_items.csv"
        summary_md_path = out_dir / "summary.md"
        summary_json_path = out_dir / "summary.json"
        notes_md_path = out_dir / "pool_construction_notes.md"
        raw_predictions_path = out_dir / "batch4_pool_predictions.jsonl"

        cache_index = self._build_cache_index()

        metadata_pool, metadata_excluded = self._rank_core_metadata_pool(
            excluded_doc_ids=excluded_doc_ids,
            excluded_titles=excluded_titles,
            cache_index=cache_index,
            limit=pool_size,
        )
        if not metadata_pool:
            raise CommandError("no metadata pool candidates available after full-library core filtering")

        if not full_rag_service.initialize():
            raise CommandError("failed to initialize full_rag_service")

        vector_service = WeaviateVectorService()
        rerunner = RerunGoldEvalCommand()
        rerunner.stdout = self.stdout
        rerunner.stderr = self.stderr

        enriched_rows: List[Dict[str, str]] = []
        with raw_predictions_path.open("w", encoding="utf-8") as raw_file:
            for pool_item in metadata_pool:
                doc = pool_item["doc"]
                cached_row = self._lookup_cached_row(cache_index, doc)
                if cached_row is not None:
                    base_row = self._row_from_cached_candidate(
                        cached_row=cached_row,
                        doc=doc,
                        metadata_score=int(pool_item["metadata_score"]),
                        metadata_reasons=pool_item["metadata_reasons"],
                    )
                    raw_file.write(json.dumps({"doc_id": str(doc.id), "status": "cached_row_reused"}, ensure_ascii=False) + "\n")
                else:
                    synthetic = self._make_synthetic_row(doc)
                    prediction = rerunner._rerun_prediction_for_row(
                        row=synthetic,
                        vector_service=vector_service,
                        max_fetch_chunks=int(options["max_fetch_chunks"]),
                        max_selected_chunks=int(options["max_selected_chunks"]),
                        strict_organics_prompt=True,
                        field_specific_evidence=True,
                        meteorite_name_strategy="title_first_shared",
                        organic_filter=True,
                        organic_projection=True,
                        expand_organic_evidence=True,
                        expand_contamination_evidence=True,
                        organic_explicit_class_recall=True,
                    )
                    raw_file.write(json.dumps(prediction["raw"], ensure_ascii=False) + "\n")
                    base_row = self._build_candidate_row(
                        doc=doc,
                        prediction=prediction,
                        raw_record=prediction["raw"],
                        gold_class_counts=Counter(),
                        metadata_score=int(pool_item["metadata_score"]),
                        metadata_reasons=pool_item["metadata_reasons"],
                    )
                enriched_rows.append(
                    self._decorate_batch4_row(
                        row=base_row,
                        metadata_reason_bucket=pool_item["metadata_reason_bucket"],
                    )
                )

        selected_rows, excluded_rows = self._select_batch4_rows(enriched_rows, limit=limit)
        final_rows = [{field: row.get(field, "") for field in self.FINAL_COLUMNS} for row in selected_rows]
        excluded_final_rows = [
            {field: row.get(field, "") for field in self.EXCLUDED_COLUMNS}
            for row in excluded_rows + metadata_excluded
        ]

        self._write_csv(csv_path, self.FINAL_COLUMNS, final_rows)
        self._write_xlsx(xlsx_path, "Batch4Core", self.FINAL_COLUMNS, final_rows)
        self._write_csv(excluded_csv_path, self.EXCLUDED_COLUMNS, excluded_final_rows)

        summary = self._build_batch4_summary(
            gold_v3_csv=gold_v3_csv,
            supporting_csv=supporting_csv,
            metadata_pool=metadata_pool,
            selected_rows=selected_rows,
            excluded_rows=excluded_final_rows,
            current_total_rows=len(gold_rows),
            current_evaluated_rows=self._count_evaluated_rows(gold_rows),
        )
        summary_md_path.write_text(self._build_batch4_summary_markdown(summary), encoding="utf-8")
        summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        notes_md_path.write_text(self._build_pool_notes(summary), encoding="utf-8")

        self.stdout.write(f"metadata_pool={len(metadata_pool)}")
        self.stdout.write(f"selected_count={len(final_rows)}")
        self.stdout.write(f"excluded_count={len(excluded_final_rows)}")
        self.stdout.write(f"batch4_csv={csv_path}")
        self.stdout.write(f"batch4_xlsx={xlsx_path}")
        self.stdout.write(f"excluded_csv={excluded_csv_path}")
        self.stdout.write(f"summary_md={summary_md_path}")
        self.stdout.write(f"notes_md={notes_md_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_batch4_core_review_{ts}").resolve()

    def _build_exclusion_sets(self, rows: Sequence[Dict[str, str]]) -> Tuple[set[str], set[str]]:
        doc_ids = {self._norm(row.get("doc_id", "")) for row in rows if self._norm(row.get("doc_id", ""))}
        titles = {self._norm_title(row.get("doc_name", "")) for row in rows if self._norm_title(row.get("doc_name", ""))}
        return doc_ids, titles

    def _rank_core_metadata_pool(
        self,
        *,
        excluded_doc_ids: Sequence[str],
        excluded_titles: Sequence[str],
        cache_index: Dict[str, Dict[str, str]],
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        pool: List[Dict[str, Any]] = []
        excluded_rows: List[Dict[str, str]] = []
        excluded_doc_ids_set = set(excluded_doc_ids)
        excluded_titles_set = set(excluded_titles)

        for doc in PDFDocument.objects.filter(processed=True).only("id", "title", "filename", "year", "journal"):
            doc_id = self._norm(str(doc.id))
            doc_name = self._build_doc_name(doc)
            title_key = self._norm_title(doc_name)
            if doc_id in excluded_doc_ids_set or title_key in excluded_titles_set:
                continue
            cached_row = self._lookup_cached_row(cache_index, doc)
            score, reasons, reason_bucket = self._core_metadata_score(doc=doc, title=doc_name, cached_row=cached_row)
            if score <= 0:
                excluded_rows.append(
                    self._build_metadata_excluded_row(doc=doc, reason_bucket=reason_bucket, reasons=reasons)
                )
                continue
            pool.append(
                {
                    "doc": doc,
                    "metadata_score": score,
                    "metadata_reasons": reasons,
                    "metadata_reason_bucket": reason_bucket,
                }
            )

        pool.sort(
            key=lambda item: (
                -int(item["metadata_score"]),
                -(item["doc"].year or 0),
                self._build_doc_name(item["doc"]).lower(),
            )
        )
        return pool[:limit], excluded_rows

    def _core_metadata_score(
        self,
        *,
        doc: PDFDocument,
        title: str,
        cached_row: Optional[Dict[str, str]],
    ) -> Tuple[int, List[str], str]:
        text = " ".join([title, str(getattr(doc, "filename", "") or ""), str(getattr(doc, "journal", "") or "")]).lower()
        reasons: List[str] = []

        hard_hits = [label for term, label in self.HARD_EXCLUDE_TERMS.items() if term in text]
        if any(term in text for term in ("mars", "martian")) and not any(
            keep in text for keep in ("meteorite", "tissint", "nwa ", "eeta", "shergottite", "nakhlite", "chassignite")
        ):
            hard_hits.append("mars_non_sample_boundary")
        if hard_hits:
            return 0, reasons + sorted(set(hard_hits)), "hard_excluded_by_metadata"

        if not any(term in text for term in self.REQUIRED_SAMPLE_TERMS):
            return 0, ["missing_sample_anchor"], "missing_sample_anchor"

        score = 0
        reason_bucket = "core_sample_metadata"
        for term in self.REQUIRED_SAMPLE_TERMS:
            if term in text:
                score += 3
                reasons.append(f"sample:{term}")
        for term, weight in self.ORGANIC_SIGNAL_TERMS.items():
            if term in text:
                score += weight
                reasons.append(f"organic:{term}")
        for term, weight in self.ANALYTICAL_TITLE_TERMS.items():
            if term in text:
                score += weight
                reasons.append(f"analytical:{term}")

        if getattr(doc, "year", None) and int(doc.year or 0) >= 2015:
            score += 1
            reasons.append("recent_enough")

        cached_projected = self._split_semicolon_list((cached_row or {}).get("pred_organic_compounds_projected", ""))
        cached_raw = self._split_semicolon_list((cached_row or {}).get("pred_organic_compounds_raw", ""))
        if cached_projected:
            score += min(len(cached_projected), 4) * 2
            reasons.append(f"cached_projected={len(cached_projected)}")
        elif cached_raw:
            score += 2
            reasons.append(f"cached_raw={len(cached_raw)}")

        soft_hits = [label for term, label in self.SOFT_EXCLUDE_TERMS.items() if term in text]
        if soft_hits:
            score -= 4 * len(set(soft_hits))
            reasons.extend(sorted(set(soft_hits)))
            reason_bucket = "soft_scope_boundary"

        if not any(term in text for term in self.ORGANIC_SIGNAL_TERMS) and not cached_projected and not cached_raw:
            return 0, reasons + ["missing_organic_signal"], "missing_organic_signal"
        if not any(term in text for term in self.ORGANIC_SIGNAL_TERMS):
            reasons.append("organic_signal_from_cache")

        cleaned = re.sub(r"[^a-z0-9]+", "", title.lower())
        if len(cleaned) < 14 or "microsoft word" in text:
            score -= 6
            reasons.append("noisy_or_truncated_title")

        return max(score, 0), reasons, reason_bucket

    def _build_metadata_excluded_row(self, *, doc: PDFDocument, reason_bucket: str, reasons: Sequence[str]) -> Dict[str, str]:
        return {
            "doc_id": str(doc.id),
            "doc_name": self._build_doc_name(doc),
            "doc_filename": str(getattr(doc, "filename", "") or ""),
            "doc_year": "" if getattr(doc, "year", None) is None else str(doc.year),
            "doc_journal": str(getattr(doc, "journal", "") or ""),
            "candidate_tags": "",
            "priority_score": "0",
            "priority_reason": "; ".join(reasons),
            "pred_meteorite_name": "",
            "pred_organic_compounds_raw": "",
            "pred_organic_compounds_filtered": "",
            "pred_organic_compounds_projected": "",
            "pred_contamination_controls": "",
            "meteorite_evidence_snippet": "",
            "organic_evidence_snippet": "",
            "contamination_evidence_snippet": "",
            "batch4_core_likelihood": "excluded_before_rerun",
            "batch4_scope_risk": reason_bucket,
            "batch4_selection_reason": "",
            "exclusion_bucket": "metadata_pre_filter",
            "exclusion_reason": "; ".join(reasons),
        }

    def _build_cache_index(self) -> Dict[str, Dict[str, str]]:
        cache_rows: Dict[str, Dict[str, str]] = {}
        for path in self._cache_candidate_csv_paths():
            if not path.exists():
                continue
            for row in self._load_csv_rows(path):
                doc_id = self._norm(row.get("doc_id", ""))
                title = self._norm_title(row.get("doc_name", ""))
                if doc_id:
                    cache_rows[f"id:{doc_id}"] = row
                if title:
                    cache_rows[f"title:{title}"] = row
        return cache_rows

    def _cache_candidate_csv_paths(self) -> List[Path]:
        return [
            (Path(settings.BASE_DIR) / "runs" / "gold_expansion_20260312_v3" / "gold_expansion_candidates.csv").resolve(),
            (Path(settings.BASE_DIR) / "runs" / "gold_batch3_core_review_20260313_v1" / "batch3_core_review_candidates.csv").resolve(),
            (Path(settings.BASE_DIR) / "runs" / "gold_batch3_core_review_20260313_v1" / "excluded_or_borderline.csv").resolve(),
        ]

    def _lookup_cached_row(self, cache_index: Dict[str, Dict[str, str]], doc: PDFDocument) -> Optional[Dict[str, str]]:
        doc_id_key = f"id:{self._norm(str(doc.id))}"
        if doc_id_key in cache_index:
            return cache_index[doc_id_key]
        title_key = f"title:{self._norm_title(self._build_doc_name(doc))}"
        return cache_index.get(title_key)

    def _row_from_cached_candidate(
        self,
        *,
        cached_row: Dict[str, str],
        doc: PDFDocument,
        metadata_score: int,
        metadata_reasons: Sequence[str],
    ) -> Dict[str, str]:
        priority_score = max(metadata_score, int(cached_row.get("priority_score") or 0))
        priority_reason = "; ".join(self._merge_priority_reasons(metadata_reasons, self._split_semicolon_list(cached_row.get("priority_reason", ""))))
        return {
            "doc_id": str(doc.id),
            "doc_name": self._build_doc_name(doc),
            "doc_filename": str(getattr(doc, "filename", "") or cached_row.get("doc_filename", "")),
            "doc_year": "" if getattr(doc, "year", None) is None else str(doc.year),
            "doc_journal": str(getattr(doc, "journal", "") or cached_row.get("doc_journal", "")),
            "candidate_tags": cached_row.get("candidate_tags", ""),
            "priority_score": str(priority_score),
            "priority_reason": priority_reason,
            "pred_meteorite_name": cached_row.get("pred_meteorite_name", ""),
            "pred_organic_compounds_raw": cached_row.get("pred_organic_compounds_raw", ""),
            "pred_organic_compounds_filtered": cached_row.get("pred_organic_compounds_filtered", ""),
            "pred_organic_compounds_projected": cached_row.get("pred_organic_compounds_projected", ""),
            "pred_contamination_controls": cached_row.get("pred_contamination_controls", ""),
            "meteorite_evidence_snippet": cached_row.get("meteorite_evidence_snippet", ""),
            "organic_evidence_snippet": cached_row.get("organic_evidence_snippet", ""),
            "contamination_evidence_snippet": cached_row.get("contamination_evidence_snippet", ""),
            "batch4_core_likelihood": "",
            "batch4_scope_risk": "",
            "batch4_selection_reason": "",
        }

    def _decorate_batch4_row(self, *, row: Dict[str, str], metadata_reason_bucket: str) -> Dict[str, str]:
        out = {field: row.get(field, "") for field in self.FINAL_COLUMNS}
        title = self._norm(row.get("doc_name", ""))
        projected = self._split_semicolon_list(row.get("pred_organic_compounds_projected", ""))
        raw_items = self._split_semicolon_list(row.get("pred_organic_compounds_raw", ""))
        sample_anchor = bool(
            self._norm(row.get("pred_meteorite_name", ""))
            or self._norm(row.get("meteorite_evidence_snippet", ""))
            or any(term in title for term in self.REQUIRED_SAMPLE_TERMS)
        )
        boundary_labels = [label for term, label in self.SOFT_EXCLUDE_TERMS.items() if term in title]
        if any(term in title for term in ("model compounds", "interstellar", "analog", "analogue")):
            boundary_labels.append("analog_or_model_boundary")
        if "mars" in title and "meteorite" not in title and "tissint" not in title:
            boundary_labels.append("mars_non_sample_boundary")

        if not projected:
            likelihood = "exclude"
            scope_risk = "missing_projected_organics"
            reason = "excluded because the fixed extraction path did not return stable projected organics"
        elif sample_anchor and not boundary_labels and len(projected) >= 2:
            likelihood = "review_first"
            scope_risk = "low_scope_risk"
            reason = "clear sample anchor plus multiple projected organics with usable evidence"
        elif sample_anchor and not boundary_labels:
            likelihood = "review_first"
            scope_risk = "moderate_scope_risk"
            reason = "sample anchor is clear, but organics coverage is narrow or methods-heavy"
        elif sample_anchor and boundary_labels:
            likelihood = "backup"
            scope_risk = "; ".join(sorted(set(boundary_labels)))
            reason = "sample link exists, but the title or scope still looks borderline for formal core gold"
        else:
            likelihood = "backup"
            scope_risk = "weak_sample_anchor"
            reason = "organics exist, but sample anchoring is weaker than desired for core gold"

        if "review" in title or "record" in title or "history" in title:
            likelihood = "backup"
            scope_risk = "broad_review_like"
            reason = "broad or synthesis-style paper; keep only as backup if the cleaner sample pool is too small"

        if "nitrogen-rich ices" in title or ("irradiation of" in title and "ices" in title):
            likelihood = "backup"
            scope_risk = "analog_or_ice_simulation"
            reason = "simulation-style ice irradiation study; keep only as backup despite micrometeorite relevance"

        if "nanoscale infrared imaging" in title or "sulfur isotopic fractionation" in title:
            likelihood = "review_first"
            scope_risk = "moderate_scope_risk"
            reason = "direct sample paper with interpretable organics evidence, despite a methods-heavy presentation"

        out["batch4_core_likelihood"] = likelihood
        out["batch4_scope_risk"] = scope_risk
        out["batch4_selection_reason"] = f"{reason}; metadata_bucket={metadata_reason_bucket}; priority_reason={row.get('priority_reason', '')}"
        return out

    def _select_batch4_rows(
        self,
        rows: Sequence[Dict[str, str]],
        *,
        limit: int,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        selected: List[Dict[str, str]] = []
        excluded: List[Dict[str, str]] = []
        for row in rows:
            if row.get("batch4_core_likelihood", "") == "exclude":
                out = dict(row)
                out["exclusion_bucket"] = "rerun_filter"
                out["exclusion_reason"] = row.get("batch4_scope_risk", "")
                excluded.append(out)
                continue
            selected.append(dict(row))

        selected.sort(key=self._batch4_sort_key, reverse=True)
        overflow = selected[limit:]
        selected = selected[:limit]

        for row in overflow:
            out = dict(row)
            out["exclusion_bucket"] = "reserve_overflow"
            out["exclusion_reason"] = row.get("batch4_core_likelihood", "")
            excluded.append(out)
        return selected, excluded

    def _batch4_sort_key(self, row: Dict[str, str]) -> Tuple[int, int, int, str]:
        likelihood_rank = {"review_first": 3, "backup": 2}.get(row.get("batch4_core_likelihood", ""), 0)
        risk_rank = {"low_scope_risk": 3, "moderate_scope_risk": 2}.get(row.get("batch4_scope_risk", ""), 1)
        projected_count = len(self._split_semicolon_list(row.get("pred_organic_compounds_projected", "")))
        return (
            likelihood_rank,
            risk_rank,
            int(row.get("priority_score") or 0),
            projected_count,
            self._norm_title(row.get("doc_name", "")),
        )

    def _build_batch4_summary(
        self,
        *,
        gold_v3_csv: Path,
        supporting_csv: Path,
        metadata_pool: Sequence[Dict[str, Any]],
        selected_rows: Sequence[Dict[str, str]],
        excluded_rows: Sequence[Dict[str, str]],
        current_total_rows: int,
        current_evaluated_rows: int,
    ) -> Dict[str, Any]:
        review_first_titles = [row.get("doc_name", "") for row in selected_rows if row.get("batch4_core_likelihood", "") == "review_first"]
        backup_titles = [row.get("doc_name", "") for row in selected_rows if row.get("batch4_core_likelihood", "") == "backup"]
        top_review_titles = review_first_titles[:10] if review_first_titles else [row.get("doc_name", "") for row in selected_rows[: min(6, len(selected_rows))]]
        selected_details = [
            {
                "doc_name": row.get("doc_name", ""),
                "likelihood": row.get("batch4_core_likelihood", ""),
                "scope_risk": row.get("batch4_scope_risk", ""),
                "priority_score": row.get("priority_score", ""),
                "candidate_tags": row.get("candidate_tags", ""),
                "selection_reason": row.get("batch4_selection_reason", ""),
            }
            for row in selected_rows
        ]
        gap_counter = Counter()
        for row in selected_rows:
            for tag in self._split_semicolon_list(row.get("candidate_tags", "")):
                gap_counter[tag] += 1
        return {
            "gold_v3_csv": str(gold_v3_csv),
            "supporting_final_csv": str(supporting_csv),
            "metadata_pool_count": len(metadata_pool),
            "selected_count": len(selected_rows),
            "review_first_count": len(review_first_titles),
            "backup_count": len(backup_titles),
            "recommended_formal_core_first": top_review_titles,
            "backup_titles": backup_titles,
            "selected_details": selected_details,
            "excluded_reason_counts": dict(Counter(row.get("exclusion_reason", "") for row in excluded_rows if row.get("exclusion_reason", ""))),
            "tag_counts": dict(gap_counter),
            "current_core_total_rows": current_total_rows,
            "current_core_evaluated_rows": current_evaluated_rows,
            "projected_total_if_add_6": current_total_rows + 6,
            "projected_eval_if_add_6": current_evaluated_rows + 6,
            "projected_total_if_add_10": current_total_rows + 10,
            "projected_eval_if_add_10": current_evaluated_rows + 10,
        }

    def _build_batch4_summary_markdown(self, summary: Dict[str, Any]) -> str:
        lines = [
            "# Batch4 Core Review Summary",
            "",
            f"- gold_v3_csv: `{summary['gold_v3_csv']}`",
            f"- supporting_final_csv: `{summary['supporting_final_csv']}`",
            f"- metadata_pool_count: `{summary['metadata_pool_count']}`",
            f"- selected_count: `{summary['selected_count']}`",
            f"- review_first_count: `{summary['review_first_count']}`",
            f"- backup_count: `{summary['backup_count']}`",
            "",
            "## What Changed Relative To Batch3",
            "",
            "- Batch3 started from the old 50-row candidate table and tried to salvage stricter core-only items from that historical pool.",
            "- Batch4 rebuilds the pool from the full processed PDF library, then excludes gold_v3 and supporting-first records before rerun.",
            "- The new metadata gate is sample-anchor first: meteorites, micrometeorites, carbonaceous chondrites, asteroid-return samples, and real martian meteorites are favored.",
            "- Analog/model/review/survivability/supporting-QC titles are filtered or demoted before they ever become batch4 review candidates.",
            "",
            "## Most Recommended For Formal Core Review First",
        ]
        for title in summary["recommended_formal_core_first"] or ["none"]:
            lines.append(f"- {title}")

        lines.extend(["", "## Backup Only"])
        for title in summary["backup_titles"] or ["none"]:
            lines.append(f"- {title}")

        lines.extend(["", "## Candidate Details"])
        for detail in summary["selected_details"]:
            lines.append(
                f"- {detail['doc_name']} | likelihood={detail['likelihood']} | scope_risk={detail['scope_risk']} | score={detail['priority_score']}"
            )
            if detail["candidate_tags"]:
                lines.append(f"  tags: {detail['candidate_tags']}")
            if detail["selection_reason"]:
                lines.append(f"  why: {detail['selection_reason']}")

        lines.extend(["", "## Suggested Exclusions / Borderlines"])
        for reason, count in sorted(summary["excluded_reason_counts"].items()):
            lines.append(f"- {reason}: {count}")

        lines.extend(
            [
                "",
                "## Estimated Core Size After New Additions",
                f"- current_core_total_rows: `{summary['current_core_total_rows']}`",
                f"- current_core_evaluated_rows: `{summary['current_core_evaluated_rows']}`",
                f"- if_add_6_rows: total=`{summary['projected_total_if_add_6']}`, evaluated=`{summary['projected_eval_if_add_6']}`",
                f"- if_add_10_rows: total=`{summary['projected_total_if_add_10']}`, evaluated=`{summary['projected_eval_if_add_10']}`",
                "",
                "## Why This Pool Is Better Suited To Core Gold",
                "- The selected set prioritizes real-sample papers with clearer meteorite/sample anchors and usable organics evidence, instead of trying to reuse older boundary-heavy candidates.",
                "- Backup items are kept visible, but they are explicitly separated from the first-pass formal-core list.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _build_pool_notes(self, summary: Dict[str, Any]) -> str:
        lines = [
            "# Batch4 Pool Construction Notes",
            "",
            "- Source scope: full processed PDF library, not the old 50-row expansion pool.",
            "- Exclusions applied before rerun: all documents already in gold_v3, all documents already in batch2 supporting final.",
            "- Metadata emphasis: sample-anchored titles first, then organics-signal titles, then methods cues.",
            "- Hard drops: interstellar analog, model compounds, broad review/perspective/comment, survivability, supporting-QC/citation-style papers.",
            "- Soft drops or demotions: comet/Ceres/non-sample-body papers, broad organic-history papers, weakly anchored life-detection titles.",
            "",
            "## Current Pool Size Targets",
            f"- selected_count: {summary['selected_count']}",
            f"- review_first_count: {summary['review_first_count']}",
            f"- backup_count: {summary['backup_count']}",
        ]
        return "\n".join(lines) + "\n"

    def _count_evaluated_rows(self, rows: Sequence[Dict[str, str]]) -> int:
        count = 0
        for row in rows:
            if self._norm(row.get("skip_row", "")) in {"yes", "y", "true", "1"}:
                continue
            if self._norm(row.get("in_scope", "")) == "no":
                continue
            count += 1
        return count

    def _norm(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().lower()

    def _norm_title(self, value: Any) -> str:
        text = self._norm(value)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()
