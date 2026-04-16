import csv
import json
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.full_rag_service import full_rag_service
from pdf_processor.management.commands.rerun_gold_extraction_eval import (
    Command as RerunGoldEvalCommand,
)
from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateVectorService


class Command(BaseCommand):
    help = "Build a CSV candidate batch for manual gold expansion using the fixed raw-recall-improved extraction path."

    FINAL_COLUMNS = [
        "doc_id",
        "doc_name",
        "doc_filename",
        "doc_year",
        "doc_journal",
        "prediction_source",
        "review_status",
        "review_priority",
        "recommendation",
        "priority_score",
        "priority_reason",
        "candidate_tags",
        "meteorite_evidence_segment_ids",
        "meteorite_evidence_page",
        "meteorite_evidence_section_hints",
        "meteorite_evidence_snippet",
        "organic_evidence_segment_ids",
        "organic_evidence_page",
        "organic_evidence_section_hints",
        "organic_evidence_snippet",
        "contamination_evidence_segment_ids",
        "contamination_evidence_page",
        "contamination_evidence_section_hints",
        "contamination_evidence_snippet",
        "pred_meteorite_name",
        "pred_organic_compounds_raw",
        "pred_organic_compounds_filtered",
        "pred_organic_compounds_projected",
        "pred_contamination_controls",
        "rerun_status",
        "rerun_strategy",
        "rerun_selected_chunk_ids",
        "rerun_selected_chunk_count",
        "rerun_success_chunk_count",
        "in_scope",
        "scope_type",
        "skip_row",
        "notes",
        "suggested_gold_meteorite_name",
        "suggested_gold_organic_compounds",
        "suggested_gold_contamination_controls",
        "gold_meteorite_name",
        "gold_organic_compounds",
        "gold_contamination_controls",
    ]
    POOL_COLUMNS = FINAL_COLUMNS + [
        "selected_for_review",
        "selection_rank",
        "selection_bucket",
        "pool_score_metadata",
        "pool_score_prediction",
    ]
    TITLE_KEYWORDS = {
        "meteorite": 3,
        "chondrite": 3,
        "asteroid": 3,
        "comet": 2,
        "67p": 2,
        "ceres": 2,
        "viking": 2,
        "itokawa": 2,
        "sample return": 3,
        "ryugu": 4,
        "bennu": 4,
        "hayabusa": 3,
        "osiris-rex": 3,
        "orgueil": 3,
        "murchison": 3,
        "winchcombe": 3,
        "tagish": 3,
        "tissint": 3,
        "allende": 2,
        "amino acid": 3,
        "amine": 3,
        "nucleobase": 3,
        "pah": 3,
        "hydrocarbon": 3,
        "volatile organic": 4,
        "organics": 2,
        "organic-rich": 3,
        "organicrich": 3,
        "organic material": 2,
        "organosulfur": 4,
        "organic matter": 3,
        "soluble organic matter": 4,
        "insoluble organic matter": 4,
        "ribose": 4,
        "sugar": 3,
        "biosignature": 2,
        "hexamethylenetetramine": 4,
        "contamination": 4,
        "curation": 4,
        "quality control": 4,
        "witness coupon": 4,
        "blank": 2,
        "raman": 2,
        "spectroscopy": 2,
        "isotope": 2,
        "gc-ms": 2,
        "lc-ms": 2,
        "chromatography": 2,
        "imaging": 2,
    }
    TITLE_PENALTIES = (
        "academic paper",
        "microsoft word",
        ".docx",
        "trackchanges",
        "extended summary",
        "hypothesis article",
    )
    DOMAIN_REQUIRED_HINTS = (
        "meteorite",
        "meteorites",
        "chondrite",
        "chondrites",
        "asteroid",
        "sample return",
        "ryugu",
        "bennu",
        "hayabusa",
        "osiris",
        "murchison",
        "orgueil",
        "winchcombe",
        "tagish",
        "tissint",
        "allende",
        "martian",
        "mars",
        "primitive meteorites",
        "extraterrestrial",
        "astromaterial",
        "interplanetary",
        "ucamm",
        "comet",
        "67p",
        "ceres",
        "organicrich",
        "organic-rich",
        "itokawa",
        "viking",
        "biosignature",
        "biosignatures",
        "martian subsurface",
        "mars-analogue",
    )
    ORGANIC_PRIORITY_TERMS = (
        "dimethylsulfides",
        "volatile organic compounds",
        "primordial organic matter",
        "PAHs",
        "aliphatic amines",
        "carboxylic acids",
        "nucleobases",
        "amino acids",
        "hydrocarbons",
        "sugars",
        "hexamethylenetetramine",
    )
    ANALYTICAL_HINTS = (
        "table ",
        "fig.",
        "figure ",
        "caption",
        "gc-ms",
        "lc-ms",
        "mass spectrometry",
        "spectroscopy",
        "raman",
        "chromatography",
        "identified",
        "detected",
        "abundance",
        "concentration",
    )
    CONTAMINATION_HINTS = (
        "contamination",
        "blank",
        "control",
        "sterile",
        "curation",
        "handling",
        "quality control",
        "qa/qc",
        "witness coupon",
        "foil",
        "freezer",
    )
    SECTION_HINT_RULES = (
        ("table_or_caption", ("table ", "fig.", "figure ", "caption")),
        ("methods_or_qc", ("methods", "protocol", "blank", "control", "sterile", "curation", "handling")),
        ("results_or_analytical", ("detected", "identified", "abundance", "concentration", "spectrum", "chromatography", "gc-ms", "lc-ms")),
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--gold",
            type=str,
            default=None,
            help="Existing gold CSV path. Default: evaluation/gold_seed.csv",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Final number of review candidates to export. Default: 10.",
        )
        parser.add_argument(
            "--pool-size",
            type=int,
            default=18,
            help="Number of metadata-ranked docs to rerun before final selection. Default: 18.",
        )
        parser.add_argument(
            "--max-fetch-chunks",
            type=int,
            default=80,
            help="Max chunks fetched from Weaviate per document. Default: 80.",
        )
        parser.add_argument(
            "--max-selected-chunks",
            type=int,
            default=3,
            help="Max selected chunks per field. Default: 3.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_expansion_<timestamp>",
        )

    def handle(self, *args, **options):
        limit = int(options["limit"])
        pool_size = max(int(options["pool_size"]), limit)
        if limit < 1:
            raise CommandError("--limit must be >= 1")

        gold_path = self._resolve_gold_path(options.get("gold"))
        gold_rows = self._load_csv_rows(gold_path)
        gold_doc_ids = {row["doc_id"] for row in gold_rows if str(row.get("doc_id", "")).strip()}
        gold_class_counts = self._build_gold_class_counts(gold_rows)

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)
        pool_path = out_dir / "candidate_pool_scoring.csv"
        final_path = out_dir / "gold_expansion_candidates.csv"
        final_xlsx_path = out_dir / "gold_expansion_candidates.xlsx"
        raw_predictions_path = out_dir / "candidate_pool_predictions.jsonl"
        summary_path = out_dir / "selection_summary.json"
        summary_md_path = out_dir / "selection_summary.md"

        candidate_pool = self._rank_metadata_candidates(gold_doc_ids=gold_doc_ids, limit=pool_size)
        if not candidate_pool:
            raise CommandError("no candidate documents available after excluding existing gold docs")

        self.stdout.write(f"gold_path={gold_path}")
        self.stdout.write(f"existing_gold_docs={len(gold_doc_ids)}")
        self.stdout.write(f"candidate_pool={len(candidate_pool)}")

        if not full_rag_service.initialize():
            raise CommandError("failed to initialize full_rag_service")

        vector_service = WeaviateVectorService()
        rerunner = RerunGoldEvalCommand()
        rerunner.stdout = self.stdout
        rerunner.stderr = self.stderr

        enriched_rows: List[Dict[str, str]] = []
        with raw_predictions_path.open("w", encoding="utf-8") as raw_file:
            for pool_item in candidate_pool:
                doc = pool_item["doc"]
                row = self._make_synthetic_row(doc)
                prediction = rerunner._rerun_prediction_for_row(
                    row=row,
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
                enriched_rows.append(
                    self._build_candidate_row(
                        doc=doc,
                        prediction=prediction,
                        raw_record=prediction["raw"],
                        gold_class_counts=gold_class_counts,
                        metadata_score=int(pool_item["metadata_score"]),
                        metadata_reasons=pool_item["metadata_reasons"],
                    )
                )

        selected_rows = self._select_diverse_candidates(enriched_rows, limit=limit)
        selected_ids = {row["doc_id"] for row in selected_rows}

        pool_rows = []
        for idx, row in enumerate(sorted(enriched_rows, key=lambda item: (-int(item["priority_score"]), item["doc_name"].lower())), start=1):
            out_row = dict(row)
            out_row["selected_for_review"] = "yes" if row["doc_id"] in selected_ids else ""
            out_row["selection_rank"] = str(idx)
            out_row["selection_bucket"] = self._selection_bucket(int(row["priority_score"]))
            pool_rows.append(out_row)

        self._write_csv(pool_path, self.POOL_COLUMNS, pool_rows)
        self._write_csv(final_path, self.FINAL_COLUMNS, selected_rows)
        self._write_xlsx(final_xlsx_path, "Candidates", self.FINAL_COLUMNS, selected_rows)
        selected_tag_counts = self._count_semicolon_values(selected_rows, "candidate_tags")
        selected_class_counts = self._count_semicolon_values(selected_rows, "pred_organic_compounds_projected")
        summary_path.write_text(
            json.dumps(
                {
                    "gold_path": str(gold_path),
                    "candidate_pool_size": len(candidate_pool),
                    "final_selected": len(selected_rows),
                    "prediction_source": "raw_recall_improved_fixed",
                    "selection_strategy": "metadata pre-rank -> fixed rerun -> explainable priority -> diversity-aware top-k",
                    "top_candidate_tags": selected_tag_counts.most_common(12),
                    "top_projected_classes": selected_class_counts.most_common(12),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        summary_md_path.write_text(
            self._build_summary_markdown(
                gold_path=gold_path,
                candidate_pool_size=len(candidate_pool),
                selected_rows=selected_rows,
                selected_tag_counts=selected_tag_counts,
                selected_class_counts=selected_class_counts,
            ),
            encoding="utf-8",
        )

        self.stdout.write(f"candidate_pool_csv={pool_path}")
        self.stdout.write(f"candidate_csv={final_path}")
        self.stdout.write(f"candidate_xlsx={final_xlsx_path}")
        self.stdout.write(f"raw_predictions={raw_predictions_path}")
        self.stdout.write(f"summary_json={summary_path}")
        self.stdout.write(f"summary_md={summary_md_path}")

    def _resolve_gold_path(self, gold_arg: Optional[str]) -> Path:
        if gold_arg and str(gold_arg).strip():
            return Path(str(gold_arg)).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation" / "gold_seed.csv").resolve()

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_expansion_{ts}").resolve()

    def _load_csv_rows(self, csv_path: Path) -> List[Dict[str, str]]:
        if not csv_path.exists():
            raise CommandError(f"csv not found: {csv_path}")
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise CommandError(f"csv has no header: {csv_path}")
            return [{key: str(row.get(key, "") or "").strip() for key in reader.fieldnames} for row in reader]

    def _build_gold_class_counts(self, rows: Sequence[Dict[str, str]]) -> Counter:
        counts: Counter = Counter()
        for row in rows:
            value = str(row.get("gold_organic_compounds", "") or "").strip()
            if not value:
                continue
            for token in self._split_semicolon_list(value):
                counts[token] += 1
        return counts

    def _rank_metadata_candidates(self, *, gold_doc_ids: Sequence[str], limit: int) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for doc in PDFDocument.objects.filter(processed=True).exclude(id__in=gold_doc_ids).only(
            "id",
            "title",
            "filename",
            "year",
            "journal",
        ):
            title = self._build_doc_name(doc)
            metadata_score, metadata_reasons = self._metadata_score(doc=doc, title=title)
            if metadata_score <= 0:
                continue
            candidates.append(
                {
                    "doc": doc,
                    "title": title,
                    "metadata_score": metadata_score,
                    "metadata_reasons": metadata_reasons,
                }
            )
        candidates.sort(
            key=lambda item: (
                -int(item["metadata_score"]),
                -(item["doc"].year or 0),
                item["title"].lower(),
            )
        )
        return candidates[:limit]

    def _metadata_score(self, *, doc: PDFDocument, title: str) -> Tuple[int, List[str]]:
        text = " ".join(
            [
                title,
                str(getattr(doc, "filename", "") or ""),
                str(getattr(doc, "journal", "") or ""),
            ]
        ).lower()
        if not any(keyword in text for keyword in self.DOMAIN_REQUIRED_HINTS):
            return 0, ["missing_domain_signal"]
        score = 0
        reasons: List[str] = []
        for keyword, weight in self.TITLE_KEYWORDS.items():
            if keyword in text:
                score += weight
                reasons.append(f"title:{keyword}")
        if getattr(doc, "year", None) and int(doc.year or 0) >= 2018:
            score += 1
            reasons.append("recent_enough")
        if any(term in text for term in ("ryugu", "bennu", "hayabusa", "sample return")):
            score += 3
            reasons.append("sample_return_relevance")
        if any(term in text for term in ("contamination", "curation", "quality control", "witness coupon")):
            score += 3
            reasons.append("contamination_or_qc")
        if any(term in text for term in ("pah", "dimethylsulfide", "volatile organic", "ribose", "hexamethylenetetramine", "organic matter")):
            score += 3
            reasons.append("organics_class_signal")
        if any(penalty in text for penalty in self.TITLE_PENALTIES):
            score -= 6
            reasons.append("noisy_title_penalty")
        if len(re.sub(r"[^A-Za-z0-9]+", "", title)) < 12:
            score -= 4
            reasons.append("very_short_or_noisy_title")
        return score, reasons

    def _make_synthetic_row(self, doc: PDFDocument) -> Dict[str, str]:
        return {
            "doc_id": str(doc.id),
            "doc_name": self._build_doc_name(doc),
            "pred_meteorite_name": "",
            "pred_organic_compounds": "",
            "pred_contamination_controls": "",
            "gold_meteorite_name": "",
            "gold_organic_compounds": "",
            "gold_contamination_controls": "",
            "in_scope": "",
            "skip_row": "",
            "notes": "",
        }

    def _build_candidate_row(
        self,
        *,
        doc: PDFDocument,
        prediction: Dict[str, Any],
        raw_record: Dict[str, Any],
        gold_class_counts: Counter,
        metadata_score: int,
        metadata_reasons: Sequence[str],
    ) -> Dict[str, str]:
        meteorite_ev = self._summarize_field_evidence(raw_record, "meteorite_name", str(doc.id))
        organic_ev = self._summarize_field_evidence(raw_record, "organic_compounds", str(doc.id))
        contamination_ev = self._summarize_field_evidence(raw_record, "contamination_controls", str(doc.id))

        projected = self._split_semicolon_list(prediction.get("pred_organic_compounds_projected", ""))
        raw_items = self._split_semicolon_list(prediction.get("pred_organic_compounds_raw", ""))
        filtered_items = self._split_semicolon_list(prediction.get("pred_organic_compounds_filtered", ""))
        candidate_tags = self._candidate_tags(
            doc_name=self._build_doc_name(doc),
            projected=projected,
            raw_items=raw_items,
            contamination=prediction.get("pred_contamination_controls", ""),
            evidence_text=" ".join(
                [
                    organic_ev["snippet"],
                    contamination_ev["snippet"],
                    meteorite_ev["snippet"],
                ]
            ),
        )
        prediction_score, prediction_reasons = self._prediction_score(
            projected=projected,
            raw_items=raw_items,
            contamination=prediction.get("pred_contamination_controls", ""),
            meteorite_name=prediction.get("pred_meteorite_name", ""),
            organic_evidence=organic_ev,
            contamination_evidence=contamination_ev,
            gold_class_counts=gold_class_counts,
            candidate_tags=candidate_tags,
        )
        priority_score = metadata_score + prediction_score
        priority_reasons = list(dict.fromkeys(list(metadata_reasons) + prediction_reasons))[:8]

        rerun_selected_chunk_ids = " | ".join(
            f"{field}={summary['segment_ids']}"
            for field, summary in (
                ("meteorite_name", meteorite_ev),
                ("organic_compounds", organic_ev),
                ("contamination_controls", contamination_ev),
            )
            if summary["segment_ids"]
        )

        return {
            "doc_id": str(doc.id),
            "doc_name": self._build_doc_name(doc),
            "doc_filename": str(getattr(doc, "filename", "") or ""),
            "doc_year": "" if getattr(doc, "year", None) is None else str(doc.year),
            "doc_journal": str(getattr(doc, "journal", "") or ""),
            "prediction_source": "raw_recall_improved_fixed",
            "review_status": "pending_manual_review",
            "review_priority": self._selection_bucket(priority_score),
            "recommendation": self._recommendation_label(
                doc_name=self._build_doc_name(doc),
                projected=projected,
                contamination=str(prediction.get("pred_contamination_controls", "") or ""),
                candidate_tags=candidate_tags,
            ),
            "priority_score": str(priority_score),
            "priority_reason": "; ".join(self._merge_priority_reasons(metadata_reasons, prediction_reasons)),
            "candidate_tags": "; ".join(candidate_tags),
            "meteorite_evidence_segment_ids": meteorite_ev["segment_ids"],
            "meteorite_evidence_page": meteorite_ev["pages"],
            "meteorite_evidence_section_hints": meteorite_ev["section_hints"],
            "meteorite_evidence_snippet": meteorite_ev["snippet"],
            "organic_evidence_segment_ids": organic_ev["segment_ids"],
            "organic_evidence_page": organic_ev["pages"],
            "organic_evidence_section_hints": organic_ev["section_hints"],
            "organic_evidence_snippet": organic_ev["snippet"],
            "contamination_evidence_segment_ids": contamination_ev["segment_ids"],
            "contamination_evidence_page": contamination_ev["pages"],
            "contamination_evidence_section_hints": contamination_ev["section_hints"],
            "contamination_evidence_snippet": contamination_ev["snippet"],
            "pred_meteorite_name": str(prediction.get("pred_meteorite_name", "") or ""),
            "pred_organic_compounds_raw": "; ".join(raw_items),
            "pred_organic_compounds_filtered": "; ".join(filtered_items),
            "pred_organic_compounds_projected": "; ".join(projected),
            "pred_contamination_controls": str(prediction.get("pred_contamination_controls", "") or ""),
            "rerun_status": str(prediction.get("status", "") or ""),
            "rerun_strategy": str(prediction.get("strategy", "") or ""),
            "rerun_selected_chunk_ids": rerun_selected_chunk_ids,
            "rerun_selected_chunk_count": str(prediction.get("selected_chunk_count", "") or ""),
            "rerun_success_chunk_count": str(prediction.get("success_chunk_count", "") or ""),
            "in_scope": "",
            "scope_type": "",
            "skip_row": "",
            "notes": "",
            "suggested_gold_meteorite_name": "",
            "suggested_gold_organic_compounds": "",
            "suggested_gold_contamination_controls": "",
            "gold_meteorite_name": "",
            "gold_organic_compounds": "",
            "gold_contamination_controls": "",
            "pool_score_metadata": str(metadata_score),
            "pool_score_prediction": str(prediction_score),
        }

    def _summarize_field_evidence(self, raw_record: Dict[str, Any], field_name: str, doc_id: str) -> Dict[str, str]:
        route = (raw_record.get("field_routes") or {}).get(field_name) or {}
        selected_chunks = route.get("selected_chunks") or []
        segment_ids: List[str] = []
        pages: List[str] = []
        snippets: List[str] = []
        section_hints: List[str] = []

        for chunk in selected_chunks[:3]:
            chunk_index = chunk.get("chunk_index")
            if chunk_index is None:
                continue
            try:
                chunk_index_int = int(chunk_index)
            except (TypeError, ValueError):
                continue
            segment_ids.append(f"{doc_id}:{chunk_index_int}")
            page_number = chunk.get("page_number")
            if page_number not in (None, ""):
                pages.append(str(page_number))
            preview = self._clean_text(chunk.get("content_preview"))
            if preview:
                snippets.append(preview)
                section_hints.extend(self._infer_section_hints(preview))

        return {
            "segment_ids": "; ".join(segment_ids[:5]),
            "pages": "; ".join(self._dedupe_preserve_order(pages)),
            "section_hints": "; ".join(self._dedupe_preserve_order(section_hints)),
            "snippet": " || ".join(snippets[:2]),
        }

    def _prediction_score(
        self,
        *,
        projected: Sequence[str],
        raw_items: Sequence[str],
        contamination: Any,
        meteorite_name: Any,
        organic_evidence: Dict[str, str],
        contamination_evidence: Dict[str, str],
        gold_class_counts: Counter,
        candidate_tags: Sequence[str],
    ) -> Tuple[int, List[str]]:
        score = 0
        reasons: List[str] = []

        if projected:
            score += min(len(projected), 4) * 2
            reasons.append(f"projected_organics={len(projected)}")
        elif raw_items:
            score += 2
            reasons.append("raw_only_organics")

        raw_bonus = max(len(raw_items) - len(projected), 0)
        if raw_bonus:
            score += min(raw_bonus, 3)
            reasons.append(f"rich_raw_support={len(raw_items)}")

        if str(meteorite_name or "").strip():
            score += 2
            reasons.append("meteorite_name_present")

        contamination_text = str(contamination or "").strip()
        if contamination_text:
            score += 3
            reasons.append("contamination_controls_present")

        if organic_evidence["snippet"]:
            score += 2
            reasons.append("organic_evidence_present")
        if any(hint in organic_evidence["section_hints"] for hint in ("table_or_caption", "results_or_analytical")):
            score += 2
            reasons.append("table_caption_or_analytical_evidence")
        if contamination_evidence["snippet"]:
            score += 1
            reasons.append("contamination_evidence_present")

        rare_classes = [item for item in projected if gold_class_counts.get(item, 0) <= 1]
        if rare_classes:
            score += min(len(rare_classes), 3) * 2
            reasons.append(f"underrepresented_class={'; '.join(sorted(rare_classes)[:3])}")

        if any(tag in candidate_tags for tag in ("asteroid_return", "contamination_qc", "martian_sample")):
            score += 2
            reasons.append("diversity_value")

        return score, reasons

    def _candidate_tags(
        self,
        *,
        doc_name: str,
        projected: Sequence[str],
        raw_items: Sequence[str],
        contamination: Any,
        evidence_text: str,
    ) -> List[str]:
        tags: List[str] = []
        lowered = " ".join([doc_name, evidence_text]).lower()
        contamination_text = str(contamination or "").lower()

        if any(term in lowered for term in ("ryugu", "bennu", "hayabusa", "sample return")):
            tags.append("asteroid_return")
        if any(term in lowered for term in ("mars", "martian", "tissint")):
            tags.append("martian_sample")
        if any(term in lowered for term in ("contamination", "curation", "quality control", "witness coupon")) or any(
            hint in contamination_text for hint in self.CONTAMINATION_HINTS
        ):
            tags.append("contamination_qc")
        if any(term in lowered for term in ("gc-ms", "lc-ms", "raman", "spectroscopy", "imaging", "isotope", "chromatography")):
            tags.append("analytical_methods")

        for token in list(projected) + list(raw_items):
            token_lower = token.lower()
            if "amino acids" in token_lower or "amino acid" in token_lower:
                tags.append("amino_acids")
            if "nucleobase" in token_lower:
                tags.append("nucleobases")
            if "pah" in token_lower:
                tags.append("pahs")
            if "dimethylsulfide" in token_lower or "organosulfur" in token_lower:
                tags.append("organosulfur")
            if "volatile organic" in token_lower:
                tags.append("volatile_organics")
            if "carboxylic acid" in token_lower:
                tags.append("carboxylic_acids")
            if "amine" in token_lower:
                tags.append("amines")
            if "organic matter" in token_lower:
                tags.append("organic_matter")
            if any(term in token_lower for term in ("ribose", "sugar")):
                tags.append("sugars")
        return self._dedupe_preserve_order(tags)

    def _select_diverse_candidates(self, rows: Sequence[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        remaining = list(rows)
        selected: List[Dict[str, str]] = []
        seen_tags: Counter = Counter()
        seen_docs: set[str] = set()

        while remaining and len(selected) < limit:
            best_idx = 0
            best_score = None
            for idx, row in enumerate(remaining):
                if row["doc_id"] in seen_docs:
                    continue
                base_score = int(row["priority_score"])
                tags = [tag for tag in self._split_semicolon_list(row.get("candidate_tags", "")) if tag]
                novelty = sum(1 for tag in tags if seen_tags[tag] == 0)
                repetition_penalty = sum(1 for tag in tags if seen_tags[tag] >= 2)
                composite = base_score + novelty * 2 - repetition_penalty
                if best_score is None or composite > best_score:
                    best_score = composite
                    best_idx = idx
            chosen = remaining.pop(best_idx)
            selected.append(chosen)
            seen_docs.add(chosen["doc_id"])
            for tag in self._split_semicolon_list(chosen.get("candidate_tags", "")):
                seen_tags[tag] += 1

        selected.sort(key=lambda row: (-int(row["priority_score"]), row["doc_name"].lower()))
        return selected

    def _selection_bucket(self, priority_score: int) -> str:
        if priority_score >= 24:
            return "high"
        if priority_score >= 16:
            return "medium"
        return "low"

    def _recommendation_label(
        self,
        *,
        doc_name: str,
        projected: Sequence[str],
        contamination: str,
        candidate_tags: Sequence[str],
    ) -> str:
        lowered = doc_name.lower()
        has_core_signal = bool(projected) or bool(contamination.strip())
        if any(tag in candidate_tags for tag in ("asteroid_return", "martian_sample")) and has_core_signal:
            return "likely_core_gold"
        if "sample return" in lowered and contamination.strip():
            return "likely_core_gold"
        if "witness coupon" in lowered or "quality control" in lowered or "curation" in lowered:
            return "likely_supporting_gold"
        if any(term in lowered for term in ("model compounds", "analog ices", "interstellar analog", "simulation")):
            return "likely_supporting_gold"
        if not has_core_signal:
            return "likely_out_of_scope"
        return "likely_supporting_gold"

    def _merge_priority_reasons(
        self,
        metadata_reasons: Sequence[str],
        prediction_reasons: Sequence[str],
        max_items: int = 8,
    ) -> List[str]:
        merged: List[str] = []
        max_meta = min(4, len(metadata_reasons))
        max_pred = min(4, len(prediction_reasons))
        for reason in list(metadata_reasons[:max_meta]) + list(prediction_reasons[:max_pred]):
            if reason not in merged:
                merged.append(reason)
        for reason in list(metadata_reasons[max_meta:]) + list(prediction_reasons[max_pred:]):
            if len(merged) >= max_items:
                break
            if reason not in merged:
                merged.append(reason)
        return merged[:max_items]

    def _build_doc_name(self, doc: PDFDocument) -> str:
        candidates = [
            getattr(doc, "title", ""),
            Path(str(getattr(doc, "filename", "") or "")).stem,
            getattr(doc, "filename", ""),
        ]
        for candidate in candidates:
            cleaned = self._clean_text(doc.clean_title(candidate) if candidate else "")
            if cleaned:
                return cleaned
        return str(doc.id)

    def _split_semicolon_list(self, value: Any) -> List[str]:
        text = str(value or "").strip()
        if not text:
            return []
        return [part.strip() for part in re.split(r"\s*;\s*", text) if part.strip()]

    def _infer_section_hints(self, text: str) -> List[str]:
        lowered = text.lower()
        hints: List[str] = []
        for label, patterns in self.SECTION_HINT_RULES:
            if any(pattern in lowered for pattern in patterns):
                hints.append(label)
        if not hints:
            hints.append("body_text")
        return hints

    def _dedupe_preserve_order(self, values: Sequence[str]) -> List[str]:
        out: List[str] = []
        seen = set()
        for value in values:
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(value)
        return out

    def _clean_text(self, value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _write_csv(self, path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})

    def _count_semicolon_values(self, rows: Sequence[Dict[str, str]], column: str) -> Counter:
        counts: Counter = Counter()
        for row in rows:
            for token in self._split_semicolon_list(row.get(column, "")):
                counts[token] += 1
        return counts

    def _build_summary_markdown(
        self,
        *,
        gold_path: Path,
        candidate_pool_size: int,
        selected_rows: Sequence[Dict[str, str]],
        selected_tag_counts: Counter,
        selected_class_counts: Counter,
    ) -> str:
        lines = [
            "# Gold Expansion Summary",
            "",
            f"- gold_path: `{gold_path}`",
            f"- candidate_pool_size: `{candidate_pool_size}`",
            f"- final_selected: `{len(selected_rows)}`",
            "- prediction_source: `raw_recall_improved_fixed`",
            "",
            "## Top Tags",
        ]
        for tag, count in selected_tag_counts.most_common(12):
            lines.append(f"- {tag}: {count}")
        lines.append("")
        lines.append("## Top Projected Classes")
        for token, count in selected_class_counts.most_common(12):
            lines.append(f"- {token}: {count}")
        lines.append("")
        lines.append("## First 10 Candidates")
        for idx, row in enumerate(selected_rows[:10], start=1):
            lines.append(
                f"- {idx}. {row.get('doc_name', '')} | priority={row.get('review_priority', '')} | recommendation={row.get('recommendation', '')}"
            )
        return "\n".join(lines) + "\n"

    def _write_xlsx(
        self,
        path: Path,
        sheet_name: str,
        fieldnames: Sequence[str],
        rows: Sequence[Dict[str, str]],
    ) -> None:
        headers = list(fieldnames)
        table_rows: List[List[Any]] = [headers]
        for row in rows:
            table_rows.append([row.get(field, "") for field in headers])

        sheet_xml = self._build_sheet_xml(table_rows)
        workbook_xml = self._build_workbook_xml(sheet_name)
        content_types_xml = self._build_content_types_xml()
        root_rels_xml = self._build_root_rels_xml()
        workbook_rels_xml = self._build_workbook_rels_xml()
        styles_xml = self._build_styles_xml()

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types_xml)
            zf.writestr("_rels/.rels", root_rels_xml)
            zf.writestr("xl/workbook.xml", workbook_xml)
            zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
            zf.writestr("xl/styles.xml", styles_xml)
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    def _build_sheet_xml(self, table_rows: Sequence[Sequence[Any]]) -> str:
        max_col = max((len(row) for row in table_rows), default=0)
        max_row = len(table_rows)
        ref = f"A1:{self._col_name(max_col)}{max_row}" if max_col and max_row else "A1:A1"

        rows_xml: List[str] = []
        for row_idx, row in enumerate(table_rows, start=1):
            cells: List[str] = []
            for col_idx, value in enumerate(row, start=1):
                cell_ref = f"{self._col_name(col_idx)}{row_idx}"
                style_id = "1" if row_idx == 1 else "0"
                cells.append(self._build_cell_xml(cell_ref, value, style_id))
            rows_xml.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'<dimension ref="{ref}"/>'
            f'<sheetData>{"".join(rows_xml)}</sheetData>'
            f'<autoFilter ref="{ref}"/>'
            "</worksheet>"
        )

    def _build_cell_xml(self, cell_ref: str, value: Any, style_id: str) -> str:
        text = "" if value is None else str(value)
        if text == "":
            return f'<c r="{cell_ref}" s="{style_id}" t="inlineStr"><is><t></t></is></c>'
        if self._is_numeric_text(text):
            return f'<c r="{cell_ref}" s="{style_id}"><v>{escape(text)}</v></c>'
        safe = escape(text)
        preserve = ' xml:space="preserve"' if text != text.strip() or "\n" in text else ""
        return f'<c r="{cell_ref}" s="{style_id}" t="inlineStr"><is><t{preserve}>{safe}</t></is></c>'

    def _is_numeric_text(self, text: str) -> bool:
        if not text:
            return False
        return bool(re.fullmatch(r"-?\d+(?:\.\d+)?", text))

    def _col_name(self, idx: int) -> str:
        out = ""
        value = idx
        while value > 0:
            value, rem = divmod(value - 1, 26)
            out = chr(65 + rem) + out
        return out or "A"

    def _build_content_types_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            "</Types>"
        )

    def _build_root_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def _build_workbook_xml(self, sheet_name: str) -> str:
        safe_name = escape(sheet_name[:31] or "Candidates")
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            f'<sheet name="{safe_name}" sheetId="1" r:id="rId1"/>'
            "</sheets>"
            "</workbook>"
        )

    def _build_workbook_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>"
        )

    def _build_styles_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
            '</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>"
        )
