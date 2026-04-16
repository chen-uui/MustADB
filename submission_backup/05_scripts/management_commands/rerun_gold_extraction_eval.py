import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.organic_alignment import align_organic_compounds_for_evaluation
from pdf_processor.extraction_postprocess import ExtractionFieldPostprocessor
from pdf_processor.full_rag_service import full_rag_service
from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateVectorService


class Command(BaseCommand):
    help = "Re-run the eval-linked extraction path on gold documents and compare baseline vs rerun."

    REQUIRED_COLUMNS = (
        "doc_id",
        "doc_name",
        "pred_meteorite_name",
        "pred_organic_compounds",
        "pred_contamination_controls",
        "gold_meteorite_name",
        "gold_organic_compounds",
        "gold_contamination_controls",
    )
    OPTIONAL_COLUMNS = ("in_scope", "skip_row", "notes")
    EXTRA_COLUMNS = (
        "rerun_status",
        "rerun_strategy",
        "rerun_selected_chunk_ids",
        "rerun_selected_chunk_count",
        "rerun_success_chunk_count",
        "pred_organic_compounds_raw",
        "pred_organic_compounds_filtered",
        "pred_organic_compounds_projected",
        "pred_organic_filter_projection_notes",
    )
    YES_VALUES = {"yes", "y", "true", "1"}
    NO_VALUES = {"no", "n", "false", "0"}

    TITLE_STOPWORDS = {
        "about",
        "after",
        "against",
        "among",
        "between",
        "from",
        "into",
        "through",
        "under",
        "with",
        "within",
        "using",
        "study",
        "evidence",
        "analysis",
        "assessment",
        "effects",
        "insights",
        "implications",
        "approach",
        "system",
        "paper",
        "article",
        "matter",
    }
    CHUNK_KEYWORDS = (
        "meteorite",
        "meteorites",
        "chondrite",
        "chondrites",
        "organic",
        "organics",
        "amino",
        "amine",
        "nucleobase",
        "nucleobases",
        "pah",
        "hydrocarbon",
        "contamination",
        "sterile",
        "blank",
        "dnase",
        "curation",
        "terrestrial",
        "extraterrestrial",
        "martian",
        "ryugu",
        "bennu",
        "orgueil",
        "murchison",
    )
    FRONT_MATTER_HINTS = (
        "article history",
        "received ",
        "accepted ",
        "available online",
        "department of",
        "university",
        "corresponding author",
        "keywords:",
        "email:",
    )
    BROAD_ORGANIC_TOKENS = {
        "organic compounds",
        "organic matter",
        "hydrocarbons",
        "aliphatic compounds",
        "aromatic compounds",
        "insoluble organic matter",
        "soluble organic matter",
    }
    NORMALIZATION_PATTERNS = {
        "insoluble organic matter": (r"\biom\b", r"\binsoluble organic matter\b"),
        "soluble organic matter": (r"\bsom\b", r"\bsoluble organic matter\b"),
        "PAHs": (r"\bpahs?\b", r"\bpolycyclic aromatic hydrocarbons?\b"),
        "amino acids": (r"\bamino acids?\b",),
        "nucleobases": (r"\bnucleobases?\b",),
        "aliphatic compounds": (r"\baliphatic (?:organic )?(?:compounds?|hydrocarbons?)\b",),
        "aromatic compounds": (r"\baromatic (?:organic )?(?:compounds?|hydrocarbons?)\b",),
    }
    DUPLICATE_CONFLICT_PAIRS = (
        ("PAHs", "hydrocarbons"),
        ("PAHs", "aromatic compounds"),
    )
    FIELD_TO_PRED_COLUMN = {
        "meteorite_name": "pred_meteorite_name",
        "organic_compounds": "pred_organic_compounds",
        "contamination_controls": "pred_contamination_controls",
    }
    METEORITE_HINTS = (
        "meteorite",
        "chondrite",
        "sample",
        "samples",
        "classification",
        "classified",
        "fall",
        "fell",
        "recovered",
        "asteroid",
    )
    ORGANIC_SPECIFIC_HINTS = (
        "amino acid",
        "amino acids",
        "amine",
        "amines",
        "monoamine",
        "nucleobase",
        "nucleobases",
        "pah",
        "pahs",
        "polycyclic aromatic hydrocarbon",
        "carboxylic acid",
        "carboxylic acids",
        "hydrocarbon",
        "hydrocarbons",
        "aliphatic amine",
        "aliphatic compounds",
        "aromatic compounds",
        "organosulfide",
        "dimethylsulfide",
        "glycine",
        "alanine",
        "valine",
        "isovaline",
        "aib",
        "anthracene",
        "phenanthrene",
    )
    ORGANIC_GENERIC_HINTS = (
        "organic matter",
        "organics",
        "prebiotic compounds",
        "indigenous organics",
        "organic inventory",
        "organic-rich",
        "organic rich",
        "carbonaceous material",
        "soluble organics",
    )
    ORGANIC_ANALYTICAL_HINTS = (
        "detected",
        "identified",
        "measured",
        "observed",
        "abundance",
        "concentration",
        "chromatography",
        "gc-ms",
        "lc-ms",
        "mass spectrometry",
        "spectroscopy",
        "spectra",
        "peak",
        "peaks",
    )
    CONTAMINATION_HINTS = (
        "contamination",
        "blank",
        "control",
        "sterile",
        "dnase",
        "clean room",
        "curation",
        "handling",
        "quality control",
        "quality-control",
        "freezer",
        "foil",
        "protocol",
        "assessment",
    )
    METHODS_HINTS = (
        "materials and methods",
        "methods",
        "experimental",
        "procedure",
        "protocol",
        "sample preparation",
        "qa/qc",
        "quality assurance",
    )
    TABLE_CAPTION_HINTS = (
        "table ",
        "tables ",
        "table 1",
        "table 2",
        "fig.",
        "figure ",
        "caption",
    )
    ANALYTICAL_RESULT_HINTS = (
        "detected",
        "identified",
        "quantitation limit",
        "detection limit",
        "abundance",
        "abundances",
        "peak",
        "peaks",
        "gc-ms",
        "gc×gc",
        "lc-ms",
        "mass spectrometry",
        "extracts",
        "analytes",
    )
    ORGANIC_CLASS_RECALL_PATTERNS = (
        (re.compile(r"\b(dimethylsulfides?|dimethyl sulfides?)\b", re.IGNORECASE), "dimethylsulfides"),
        (re.compile(r"\b(volatile organic compounds?)\b", re.IGNORECASE), "volatile organic compounds"),
        (re.compile(r"\b(primordial organic matter)\b", re.IGNORECASE), "primordial organic matter"),
    )
    CATEGORY_ORDER = (
        "field_empty_or_missing",
        "missed_extraction",
        "wrong_extraction",
        "over_broad_or_generalized",
        "normalization_or_projection_issue",
        "duplicate_or_conflict",
    )

    def add_arguments(self, parser):
        parser.add_argument("--gold", type=str, required=True, help="Baseline gold CSV path.")
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_rerun_<timestamp>/",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional cap on rerun rows after skip filtering.",
        )
        parser.add_argument(
            "--max-fetch-chunks",
            type=int,
            default=80,
            help="Maximum document chunks to load from Weaviate per document.",
        )
        parser.add_argument(
            "--max-selected-chunks",
            type=int,
            default=5,
            help="Maximum chunks to actually send to the extractor per document.",
        )
        parser.add_argument(
            "--strict-organics-prompt",
            action="store_true",
            help="Use a stricter closed-world organics prompt.",
        )
        parser.add_argument(
            "--field-specific-evidence",
            action="store_true",
            help="Select evidence separately for meteorite_name, organic_compounds, and contamination_controls.",
        )
        parser.add_argument(
            "--meteorite-name-strategy",
            type=str,
            default="field_specific",
            choices=("field_specific", "title_first_shared"),
            help="Meteorite-name strategy when field-specific evidence is enabled.",
        )
        parser.add_argument(
            "--organic-filter",
            action="store_true",
            help="Filter obvious non-organic or generic organic items before evaluation.",
        )
        parser.add_argument(
            "--organic-projection",
            action="store_true",
            help="Project fine-grained organic items to gold-level classes for evaluation alignment.",
        )
        parser.add_argument(
            "--expand-organic-evidence",
            action="store_true",
            help="Add table/caption/analytical-result candidates to the organic evidence pool.",
        )
        parser.add_argument(
            "--expand-contamination-evidence",
            action="store_true",
            help="Add methods/table/caption control-related candidates to the contamination evidence pool.",
        )
        parser.add_argument(
            "--organic-explicit-class-recall",
            action="store_true",
            help="Promote and harvest explicit gold-level organic class mentions from organics evidence.",
        )

    def handle(self, *args, **options):
        gold_path = Path(str(options["gold"])).expanduser().resolve()
        if not gold_path.exists():
            raise CommandError(f"gold csv not found: {gold_path}")

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        rows = self._load_gold_rows(gold_path)
        target_rows = self._select_rerun_rows(rows, limit=options.get("limit"))
        if not target_rows:
            raise CommandError("no rerun rows selected from gold csv")

        self.stdout.write(f"gold_path={gold_path}")
        self.stdout.write(f"total_rows={len(rows)}")
        self.stdout.write(f"target_rows={len(target_rows)}")

        if not full_rag_service.initialize():
            raise CommandError("failed to initialize full_rag_service")

        vector_service = WeaviateVectorService()
        rerun_doc_ids = {row["doc_id"] for row in target_rows}

        raw_predictions_path = out_dir / "raw_chunk_predictions.jsonl"
        rerun_csv_path = out_dir / "gold_seed_rerun.csv"
        comparison_path = out_dir / "before_after_comparison.csv"
        change_rows_path = out_dir / "prediction_changes.csv"
        baseline_organic_summary_path = out_dir / "baseline_organic_error_summary.csv"
        baseline_organic_cases_path = out_dir / "baseline_organic_error_cases.csv"
        rerun_organic_summary_path = out_dir / "organic_error_summary.csv"
        rerun_organic_cases_path = out_dir / "organic_error_cases.csv"
        organic_comparison_path = out_dir / "organic_error_comparison.csv"
        organic_summary_path = out_dir / "organic_error_summary.csv"
        organic_cases_path = out_dir / "organic_error_cases.csv"
        baseline_eval_dir = out_dir / "baseline_eval"
        rerun_eval_dir = out_dir / "rerun_eval"

        updated_rows: List[Dict[str, str]] = []
        change_rows: List[Dict[str, str]] = []

        with raw_predictions_path.open("w", encoding="utf-8") as raw_file:
            for row in rows:
                updated = dict(row)
                if row["doc_id"] not in rerun_doc_ids:
                    updated.update(
                        {
                            "rerun_status": "not_rerun",
                            "rerun_strategy": "",
                            "rerun_selected_chunk_ids": "",
                            "rerun_selected_chunk_count": "",
                            "rerun_success_chunk_count": "",
                        }
                    )
                    updated_rows.append(updated)
                    continue

                prediction = self._rerun_prediction_for_row(
                    row=row,
                    vector_service=vector_service,
                    max_fetch_chunks=int(options["max_fetch_chunks"]),
                    max_selected_chunks=int(options["max_selected_chunks"]),
                    strict_organics_prompt=bool(options.get("strict_organics_prompt")),
                    field_specific_evidence=bool(options.get("field_specific_evidence")),
                    meteorite_name_strategy=str(options.get("meteorite_name_strategy") or "field_specific"),
                    organic_filter=bool(options.get("organic_filter")),
                    organic_projection=bool(options.get("organic_projection")),
                    expand_organic_evidence=bool(options.get("expand_organic_evidence")),
                    expand_contamination_evidence=bool(options.get("expand_contamination_evidence")),
                    organic_explicit_class_recall=bool(options.get("organic_explicit_class_recall")),
                )
                raw_file.write(json.dumps(prediction["raw"], ensure_ascii=False) + "\n")

                updated["pred_meteorite_name"] = prediction["pred_meteorite_name"]
                updated["pred_organic_compounds"] = prediction["pred_organic_compounds"]
                updated["pred_contamination_controls"] = prediction["pred_contamination_controls"]
                updated["pred_organic_compounds_raw"] = prediction["pred_organic_compounds_raw"]
                updated["pred_organic_compounds_filtered"] = prediction["pred_organic_compounds_filtered"]
                updated["pred_organic_compounds_projected"] = prediction["pred_organic_compounds_projected"]
                updated["pred_organic_filter_projection_notes"] = prediction["pred_organic_filter_projection_notes"]
                updated["rerun_status"] = prediction["status"]
                updated["rerun_strategy"] = prediction["strategy"]
                updated["rerun_selected_chunk_ids"] = prediction["selected_chunk_ids"]
                updated["rerun_selected_chunk_count"] = str(prediction["selected_chunk_count"])
                updated["rerun_success_chunk_count"] = str(prediction["success_chunk_count"])
                updated_rows.append(updated)

                change_rows.append(
                    {
                        "doc_id": row["doc_id"],
                        "doc_name": row["doc_name"],
                        "old_pred_meteorite_name": row["pred_meteorite_name"],
                        "new_pred_meteorite_name": updated["pred_meteorite_name"],
                        "old_pred_organic_compounds": row["pred_organic_compounds"],
                        "new_pred_organic_compounds": updated["pred_organic_compounds"],
                        "old_pred_contamination_controls": row["pred_contamination_controls"],
                        "new_pred_contamination_controls": updated["pred_contamination_controls"],
                        "rerun_status": prediction["status"],
                        "rerun_strategy": prediction["strategy"],
                    }
                )

        rerun_fieldnames = list(rows[0].keys()) + list(self.EXTRA_COLUMNS)
        self._write_csv(rerun_csv_path, rerun_fieldnames, updated_rows)
        self._write_csv(change_rows_path, list(change_rows[0].keys()) if change_rows else [], change_rows)

        call_command("eval_extraction_accuracy", gold=str(gold_path), out=str(baseline_eval_dir))
        call_command("eval_extraction_accuracy", gold=str(rerun_csv_path), out=str(rerun_eval_dir))

        baseline_summary_path = baseline_eval_dir / "accuracy_summary.csv"
        rerun_summary_path = rerun_eval_dir / "accuracy_summary.csv"
        self._build_comparison(
            baseline_summary_path=baseline_summary_path,
            rerun_summary_path=rerun_summary_path,
            out_path=comparison_path,
        )
        self._build_organic_error_analysis(
            rows=rows,
            out_summary_path=baseline_organic_summary_path,
            out_cases_path=baseline_organic_cases_path,
        )
        self._build_organic_error_analysis(
            rows=updated_rows,
            out_summary_path=rerun_organic_summary_path,
            out_cases_path=rerun_organic_cases_path,
        )
        self._build_organic_error_comparison(
            baseline_summary_path=baseline_organic_summary_path,
            rerun_summary_path=rerun_organic_summary_path,
            out_path=organic_comparison_path,
        )

        self.stdout.write(f"rerun_csv={rerun_csv_path}")
        self.stdout.write(f"raw_chunk_predictions={raw_predictions_path}")
        self.stdout.write(f"prediction_changes={change_rows_path}")
        self.stdout.write(f"baseline_eval_dir={baseline_eval_dir}")
        self.stdout.write(f"rerun_eval_dir={rerun_eval_dir}")
        self.stdout.write(f"comparison_path={comparison_path}")
        self.stdout.write(f"baseline_organic_error_summary={baseline_organic_summary_path}")
        self.stdout.write(f"baseline_organic_error_cases={baseline_organic_cases_path}")
        self.stdout.write(f"organic_error_summary={organic_summary_path}")
        self.stdout.write(f"organic_error_cases={organic_cases_path}")
        self.stdout.write(f"organic_error_comparison={organic_comparison_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_rerun_{ts}").resolve()

    def _load_gold_rows(self, gold_path: Path) -> List[Dict[str, str]]:
        with gold_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise CommandError(f"gold csv has no header: {gold_path}")
            missing = [col for col in self.REQUIRED_COLUMNS if col not in reader.fieldnames]
            if missing:
                raise CommandError(f"gold csv missing required columns: {', '.join(missing)}")

            rows: List[Dict[str, str]] = []
            for row in reader:
                normalized = {key: str(row.get(key, "") or "").strip() for key in reader.fieldnames}
                rows.append(normalized)
        if not rows:
            raise CommandError(f"gold csv has no rows: {gold_path}")
        return rows

    def _select_rerun_rows(self, rows: Sequence[Dict[str, str]], limit: Optional[int]) -> List[Dict[str, str]]:
        selected = []
        for row in rows:
            if self._should_skip_row(row):
                continue
            selected.append(row)
        if limit is not None:
            return selected[: int(limit)]
        return selected

    def _should_skip_row(self, row: Dict[str, str]) -> bool:
        skip_value = self._normalize_bool_value(row.get("skip_row", ""))
        if skip_value is True:
            return True
        in_scope_value = self._normalize_bool_value(row.get("in_scope", ""))
        if in_scope_value is False:
            return True
        return False

    def _normalize_bool_value(self, value: str) -> Optional[bool]:
        lowered = str(value or "").strip().lower()
        if lowered in self.YES_VALUES:
            return True
        if lowered in self.NO_VALUES:
            return False
        return None

    def _rerun_prediction_for_row(
        self,
        *,
        row: Dict[str, str],
        vector_service: WeaviateVectorService,
        max_fetch_chunks: int,
        max_selected_chunks: int,
        strict_organics_prompt: bool,
        field_specific_evidence: bool,
        meteorite_name_strategy: str,
        organic_filter: bool,
        organic_projection: bool,
        expand_organic_evidence: bool,
        expand_contamination_evidence: bool,
        organic_explicit_class_recall: bool,
    ) -> Dict[str, Any]:
        doc_id = str(row["doc_id"])
        doc = PDFDocument.objects.filter(id=doc_id).only("id", "title", "filename").first()
        if not doc:
            return self._empty_prediction(row, status="missing_pdf_document")

        doc_name = self._build_doc_name(doc, row.get("doc_name", ""))
        chunks = vector_service.get_document_chunks(doc_id, limit=max_fetch_chunks)
        if not chunks:
            return self._empty_prediction(row, status="missing_weaviate_chunks")

        if field_specific_evidence:
            return self._rerun_prediction_field_specific(
                row=row,
                doc_name=doc_name,
                doc_id=doc_id,
                chunks=chunks,
                max_selected_chunks=max_selected_chunks,
                strict_organics_prompt=strict_organics_prompt,
                meteorite_name_strategy=meteorite_name_strategy,
                organic_filter=organic_filter,
                organic_projection=organic_projection,
                expand_organic_evidence=expand_organic_evidence,
                expand_contamination_evidence=expand_contamination_evidence,
                organic_explicit_class_recall=organic_explicit_class_recall,
            )
        return self._rerun_prediction_shared(
            row=row,
            doc_name=doc_name,
            doc_id=doc_id,
            chunks=chunks,
            max_selected_chunks=max_selected_chunks,
            strict_organics_prompt=strict_organics_prompt,
            organic_filter=organic_filter,
            organic_projection=organic_projection,
            organic_explicit_class_recall=organic_explicit_class_recall,
        )

    def _rerun_prediction_shared(
        self,
        *,
        row: Dict[str, str],
        doc_name: str,
        doc_id: str,
        chunks: Sequence[Dict[str, Any]],
        max_selected_chunks: int,
        strict_organics_prompt: bool,
        organic_filter: bool,
        organic_projection: bool,
        organic_explicit_class_recall: bool,
    ) -> Dict[str, Any]:
        selected_chunks = self._select_candidate_chunks(
            doc_name=doc_name,
            chunks=chunks,
            max_selected_chunks=max_selected_chunks,
            field_name="shared",
            boost_explicit_organic_class=organic_explicit_class_recall,
        )
        if not selected_chunks:
            return self._empty_prediction(row, status="no_candidate_chunks")

        route = self._run_extraction_route(
            selected_chunks=selected_chunks,
            strict_organics_prompt=strict_organics_prompt,
            relevant_fields=tuple(self.FIELD_TO_PRED_COLUMN.values()),
        )
        if organic_explicit_class_recall:
            route["aggregated"]["pred_organic_compounds"] = self._augment_organic_raw_with_explicit_classes(
                existing_value=route["aggregated"].get("pred_organic_compounds", ""),
                doc_name=doc_name,
                selected_chunks=selected_chunks,
            )
        aggregated = self._apply_organic_alignment(
            route["aggregated"],
            use_filter=organic_filter,
            use_projection=organic_projection,
        )
        raw = {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "status": "ok" if route["chunk_results"] else "no_prediction",
            "strategy": route["strategy"],
            "selected_chunks": self._serialize_selected_chunks(selected_chunks),
            "chunk_results": route["chunk_results"],
            "aggregated_prediction": aggregated,
        }
        return {
            "pred_meteorite_name": aggregated["pred_meteorite_name"],
            "pred_organic_compounds": aggregated["pred_organic_compounds"],
            "pred_contamination_controls": aggregated["pred_contamination_controls"],
            "pred_organic_compounds_raw": aggregated["pred_organic_compounds_raw"],
            "pred_organic_compounds_filtered": aggregated["pred_organic_compounds_filtered"],
            "pred_organic_compounds_projected": aggregated["pred_organic_compounds_projected"],
            "pred_organic_filter_projection_notes": aggregated["pred_organic_filter_projection_notes"],
            "status": raw["status"],
            "strategy": route["strategy"],
            "selected_chunk_ids": self._join_chunk_ids(doc_id, selected_chunks),
            "selected_chunk_count": len(selected_chunks),
            "success_chunk_count": route["success_chunk_count"],
            "raw": raw,
        }

    def _rerun_prediction_field_specific(
        self,
        *,
        row: Dict[str, str],
        doc_name: str,
        doc_id: str,
        chunks: Sequence[Dict[str, Any]],
        max_selected_chunks: int,
        strict_organics_prompt: bool,
        meteorite_name_strategy: str,
        organic_filter: bool,
        organic_projection: bool,
        expand_organic_evidence: bool,
        expand_contamination_evidence: bool,
        organic_explicit_class_recall: bool,
    ) -> Dict[str, Any]:
        combined_prediction = {
            "pred_meteorite_name": "",
            "pred_organic_compounds": "",
            "pred_contamination_controls": "",
        }
        raw_routes: Dict[str, Any] = {}
        route_id_parts: List[str] = []
        unique_selected_ids = set()
        success_chunk_count = 0

        for field_name, pred_column in self.FIELD_TO_PRED_COLUMN.items():
            if field_name == "meteorite_name" and meteorite_name_strategy == "title_first_shared":
                route = self._predict_meteorite_name_title_first_shared(
                    doc_name=doc_name,
                    doc_id=doc_id,
                    chunks=chunks,
                    max_selected_chunks=max_selected_chunks,
                    strict_organics_prompt=strict_organics_prompt,
                )
                combined_prediction[pred_column] = route["value"]
                raw_routes[field_name] = route["raw"]
                if route["selected_chunk_ids"]:
                    route_id_parts.append(f"{field_name}={route['selected_chunk_ids']}")
                    unique_selected_ids.update(route["selected_chunk_ids"].split("; "))
                success_chunk_count += int(route["success_chunk_count"])
                continue

            selected_chunks = self._select_candidate_chunks(
                doc_name=doc_name,
                chunks=chunks,
                max_selected_chunks=max_selected_chunks,
                field_name=field_name,
                expand_special_evidence=(
                    (field_name == "organic_compounds" and expand_organic_evidence)
                    or (field_name == "contamination_controls" and expand_contamination_evidence)
                ),
                boost_explicit_organic_class=(field_name == "organic_compounds" and organic_explicit_class_recall),
            )
            route = self._run_extraction_route(
                selected_chunks=selected_chunks,
                strict_organics_prompt=strict_organics_prompt,
                relevant_fields=(pred_column,),
            )
            if field_name == "organic_compounds" and organic_explicit_class_recall:
                route["aggregated"][pred_column] = self._augment_organic_raw_with_explicit_classes(
                    existing_value=route["aggregated"].get(pred_column, ""),
                    doc_name=doc_name,
                    selected_chunks=selected_chunks,
                )
            combined_prediction[pred_column] = route["aggregated"].get(pred_column, "")
            raw_routes[field_name] = {
                "strategy": route["strategy"],
                "selected_chunks": self._serialize_selected_chunks(selected_chunks),
                "chunk_results": route["chunk_results"],
                "aggregated_prediction": route["aggregated"],
            }
            if selected_chunks:
                route_id_parts.append(f"{field_name}={self._join_chunk_ids(doc_id, selected_chunks)}")
                unique_selected_ids.update(
                    f"{doc_id}:{int(chunk.get('chunk_index', 0) or 0)}" for chunk in selected_chunks
                )
            success_chunk_count += route["success_chunk_count"]

        combined_prediction = self._apply_organic_alignment(
            combined_prediction,
            use_filter=organic_filter,
            use_projection=organic_projection,
        )
        status = "ok" if self._has_relevant_signal(combined_prediction, tuple(self.FIELD_TO_PRED_COLUMN.values())) else "no_prediction"
        raw = {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "status": status,
            "strategy": "field_specific_evidence",
            "field_routes": raw_routes,
            "aggregated_prediction": combined_prediction,
        }
        return {
            "pred_meteorite_name": combined_prediction["pred_meteorite_name"],
            "pred_organic_compounds": combined_prediction["pred_organic_compounds"],
            "pred_contamination_controls": combined_prediction["pred_contamination_controls"],
            "pred_organic_compounds_raw": combined_prediction["pred_organic_compounds_raw"],
            "pred_organic_compounds_filtered": combined_prediction["pred_organic_compounds_filtered"],
            "pred_organic_compounds_projected": combined_prediction["pred_organic_compounds_projected"],
            "pred_organic_filter_projection_notes": combined_prediction["pred_organic_filter_projection_notes"],
            "status": status,
            "strategy": "field_specific_evidence",
            "selected_chunk_ids": " | ".join(route_id_parts),
            "selected_chunk_count": len(unique_selected_ids),
            "success_chunk_count": success_chunk_count,
            "raw": raw,
        }

    def _run_extraction_route(
        self,
        *,
        selected_chunks: Sequence[Dict[str, Any]],
        strict_organics_prompt: bool,
        relevant_fields: Sequence[str],
    ) -> Dict[str, Any]:
        chunk_results: List[Dict[str, Any]] = []
        for chunk in selected_chunks:
            extracted = full_rag_service.extract_meteorite_data(
                str(chunk.get("content", "")),
                strict_organics_prompt=strict_organics_prompt,
            )
            if not extracted:
                continue
            chunk_results.append(
                {
                    "chunk_index": int(chunk.get("chunk_index", 0) or 0),
                    "page_number": int(chunk.get("page_number", 0) or 0),
                    "selection_score": int(chunk.get("selection_score", 0) or 0),
                    "data": self._serialize_extraction_result(extracted),
                }
            )

        strategy = "chunk_vote"
        aggregated = self._aggregate_chunk_predictions(chunk_results)
        if not chunk_results or not self._has_relevant_signal(aggregated, relevant_fields):
            fallback_result = self._run_combined_fallback(
                selected_chunks=selected_chunks,
                strict_organics_prompt=strict_organics_prompt,
                relevant_fields=relevant_fields,
            )
            if fallback_result:
                chunk_results = [fallback_result]
                aggregated = self._aggregate_chunk_predictions(chunk_results)
                strategy = str(fallback_result.get("strategy") or "combined_fallback")

        return {
            "strategy": strategy,
            "aggregated": aggregated,
            "chunk_results": chunk_results,
            "success_chunk_count": len(chunk_results),
        }

    def _predict_meteorite_name_title_first_shared(
        self,
        *,
        doc_name: str,
        doc_id: str,
        chunks: Sequence[Dict[str, Any]],
        max_selected_chunks: int,
        strict_organics_prompt: bool,
    ) -> Dict[str, Any]:
        title_prediction = ExtractionFieldPostprocessor.normalize_meteorite_name(doc_name)
        if title_prediction:
            return {
                "value": title_prediction,
                "selected_chunk_ids": "",
                "success_chunk_count": 0,
                "raw": {
                    "strategy": "title_first_shared:title_only",
                    "selected_chunks": [],
                    "chunk_results": [],
                    "aggregated_prediction": {"pred_meteorite_name": title_prediction},
                },
            }

        selected_chunks = self._select_candidate_chunks(
            doc_name=doc_name,
            chunks=chunks,
            max_selected_chunks=max_selected_chunks,
            field_name="shared",
        )
        route = self._run_extraction_route(
            selected_chunks=selected_chunks,
            strict_organics_prompt=strict_organics_prompt,
            relevant_fields=("pred_meteorite_name",),
        )
        return {
            "value": route["aggregated"].get("pred_meteorite_name", ""),
            "selected_chunk_ids": self._join_chunk_ids(doc_id, selected_chunks) if selected_chunks else "",
            "success_chunk_count": route["success_chunk_count"],
            "raw": {
                "strategy": "title_first_shared:shared_fallback",
                "selected_chunks": self._serialize_selected_chunks(selected_chunks),
                "chunk_results": route["chunk_results"],
                "aggregated_prediction": route["aggregated"],
            },
        }

    def _run_combined_fallback(
        self,
        *,
        selected_chunks: Sequence[Dict[str, Any]],
        strict_organics_prompt: bool,
        relevant_fields: Sequence[str],
    ) -> Optional[Dict[str, Any]]:
        for combine_count in (2, 3):
            if len(selected_chunks) < combine_count:
                continue
            combined_content = "\n\n".join(
                str(chunk.get("content", "")) for chunk in selected_chunks[:combine_count]
            )
            extracted = full_rag_service.extract_meteorite_data(
                combined_content,
                strict_organics_prompt=strict_organics_prompt,
            )
            if not extracted:
                continue
            serialized = self._serialize_extraction_result(extracted)
            aggregated = self._aggregate_chunk_predictions(
                [{"chunk_index": -1, "page_number": 0, "selection_score": 0, "data": serialized}]
            )
            if not self._has_relevant_signal(aggregated, relevant_fields):
                continue
            return {
                "chunk_index": -1,
                "page_number": 0,
                "selection_score": 0,
                "strategy": f"combined_fallback_top_{combine_count}",
                "data": serialized,
            }
        return None

    def _has_relevant_signal(self, aggregated: Dict[str, str], relevant_fields: Sequence[str]) -> bool:
        return any(str(aggregated.get(field, "") or "").strip() for field in relevant_fields)

    def _serialize_selected_chunks(self, chunks: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "chunk_index": int(chunk.get("chunk_index", 0) or 0),
                "page_number": int(chunk.get("page_number", 0) or 0),
                "selection_score": int(chunk.get("selection_score", 0) or 0),
                "content_preview": self._preview_text(chunk.get("content", "")),
            }
            for chunk in chunks
        ]

    def _join_chunk_ids(self, doc_id: str, chunks: Sequence[Dict[str, Any]]) -> str:
        return "; ".join(
            f"{doc_id}:{int(chunk.get('chunk_index', 0) or 0)}"
            for chunk in chunks
        )

    def _empty_prediction(self, row: Dict[str, str], *, status: str) -> Dict[str, Any]:
        raw = {
            "doc_id": row["doc_id"],
            "doc_name": row.get("doc_name", ""),
            "status": status,
            "strategy": "",
            "selected_chunks": [],
            "chunk_results": [],
            "aggregated_prediction": {
                "pred_meteorite_name": "",
                "pred_organic_compounds": "",
                "pred_contamination_controls": "",
            },
        }
        return {
            "pred_meteorite_name": "",
            "pred_organic_compounds": "",
            "pred_contamination_controls": "",
            "pred_organic_compounds_raw": "",
            "pred_organic_compounds_filtered": "",
            "pred_organic_compounds_projected": "",
            "pred_organic_filter_projection_notes": "",
            "status": status,
            "strategy": "",
            "selected_chunk_ids": "",
            "selected_chunk_count": 0,
            "success_chunk_count": 0,
            "raw": raw,
        }

    def _build_doc_name(self, doc: PDFDocument, fallback: str) -> str:
        candidates = [doc.title, doc.filename, fallback]
        for candidate in candidates:
            text = str(candidate or "").strip()
            if text:
                return doc.clean_title(text)
        return str(doc.id)

    def _select_candidate_chunks(
        self,
        *,
        doc_name: str,
        chunks: Sequence[Dict[str, Any]],
        max_selected_chunks: int,
        field_name: str = "shared",
        expand_special_evidence: bool = False,
        boost_explicit_organic_class: bool = False,
    ) -> List[Dict[str, Any]]:
        title_tokens = self._extract_title_tokens(doc_name)
        ordered_chunks = sorted(
            chunks,
            key=lambda item: (
                int(item.get("page_number", 0) or 0),
                int(item.get("chunk_index", 0) or 0),
            ),
        )
        scored_chunks: List[Dict[str, Any]] = []
        for chunk in ordered_chunks:
            content = " ".join(str(chunk.get("content", "")).split())
            if not content:
                continue
            score = self._score_chunk(
                content=content,
                title_tokens=title_tokens,
                chunk_index=int(chunk.get("chunk_index", 0) or 0),
                page_number=int(chunk.get("page_number", 0) or 0),
                field_name=field_name,
                boost_explicit_organic_class=boost_explicit_organic_class,
            )
            scored_chunk = dict(chunk)
            scored_chunk["content"] = content
            scored_chunk["selection_score"] = score
            scored_chunks.append(scored_chunk)

        scored_chunks.sort(
            key=lambda item: (
                int(item.get("selection_score", 0) or 0),
                len(str(item.get("content", ""))),
                -int(item.get("chunk_index", 0) or 0),
            ),
            reverse=True,
        )

        selected = [item for item in scored_chunks if int(item.get("selection_score", 0) or 0) > 0]
        selected = selected[:max_selected_chunks]
        if expand_special_evidence:
            selected = self._inject_special_evidence_candidates(
                selected=selected,
                scored_chunks=scored_chunks,
                max_selected_chunks=max_selected_chunks,
                field_name=field_name,
                boost_explicit_organic_class=boost_explicit_organic_class,
            )
        if len(selected) < min(3, max_selected_chunks):
            selected_indices = {int(item.get("chunk_index", 0) or 0) for item in selected}
            for item in scored_chunks:
                chunk_index = int(item.get("chunk_index", 0) or 0)
                if chunk_index in selected_indices:
                    continue
                if self._looks_like_reference_chunk(str(item.get("content", ""))):
                    continue
                selected.append(item)
                selected_indices.add(chunk_index)
                if len(selected) >= min(3, max_selected_chunks):
                    break

        selected.sort(key=lambda item: int(item.get("chunk_index", 0) or 0))
        return selected[:max_selected_chunks]

    def _extract_title_tokens(self, doc_name: str) -> List[str]:
        tokens = []
        for token in re.findall(r"[A-Za-z0-9]+", str(doc_name or "").lower()):
            if len(token) < 4:
                continue
            if token in self.TITLE_STOPWORDS:
                continue
            tokens.append(token)
        return list(dict.fromkeys(tokens))

    def _score_chunk(
        self,
        *,
        content: str,
        title_tokens: Sequence[str],
        chunk_index: int,
        page_number: int,
        field_name: str,
        boost_explicit_organic_class: bool = False,
    ) -> int:
        lower = content.lower()
        score = 0
        title_overlap = sum(4 for token in title_tokens if token in lower)
        generic_keyword_hits = sum(1 for keyword in self.CHUNK_KEYWORDS if keyword in lower)
        score += title_overlap
        score += generic_keyword_hits * 2

        if field_name == "meteorite_name":
            score += sum(3 for keyword in self.METEORITE_HINTS if keyword in lower)
            if ExtractionFieldPostprocessor.normalize_meteorite_name(content):
                score += 8
            if "abstract" in lower:
                score += 8
            if "introduction" in lower:
                score += 3
            if page_number <= 2:
                score += 6
            elif page_number <= 4:
                score += 3
            elif page_number >= 7:
                score -= 4
            if chunk_index <= 3:
                score += 4
            elif chunk_index <= 6:
                score += 2
        elif field_name == "organic_compounds":
            specific_hits = sum(1 for keyword in self.ORGANIC_SPECIFIC_HINTS if keyword in lower)
            generic_hits = sum(1 for phrase in self.ORGANIC_GENERIC_HINTS if phrase in lower)
            analytical_hits = sum(1 for hint in self.ORGANIC_ANALYTICAL_HINTS if hint in lower)
            explicit_class_hits = len(self._extract_explicit_organic_classes_from_text(content))
            score += specific_hits * 6
            score += analytical_hits * 3
            if boost_explicit_organic_class and explicit_class_hits:
                score += explicit_class_hits * 8
                if chunk_index <= 1:
                    score += 6
            if self._looks_like_table_or_caption(content):
                score += 4
                if boost_explicit_organic_class and explicit_class_hits:
                    score += 4
            if self._looks_like_analytical_result_snippet(content):
                score += 5
                if boost_explicit_organic_class and explicit_class_hits:
                    score += 4
            if "results" in lower or "discussion" in lower:
                score += 5
            if "abstract" in lower:
                score += 2
            if page_number <= 4:
                score += 2
            if generic_hits:
                score -= generic_hits * 4
                if specific_hits == 0:
                    score -= 8
            if any(hint in lower for hint in self.CONTAMINATION_HINTS) and specific_hits == 0:
                score -= 6
        elif field_name == "contamination_controls":
            contam_hits = sum(1 for keyword in self.CONTAMINATION_HINTS if keyword in lower)
            method_hits = sum(1 for keyword in self.METHODS_HINTS if keyword in lower)
            score += contam_hits * 5
            score += method_hits * 4
            if self._looks_like_table_or_caption(content) and contam_hits > 0:
                score += 4
            if "materials and methods" in lower or "methods" in lower or "experimental" in lower:
                score += 8
            if page_number <= 3:
                score += 3
            if ("results" in lower or "discussion" in lower) and contam_hits == 0:
                score -= 4
        else:
            if "abstract" in lower:
                score += 8
            if "results" in lower or "discussion" in lower:
                score += 3
            if page_number <= 2:
                score += 6
            elif page_number <= 4:
                score += 3
            elif page_number >= 7:
                score -= 6
            if chunk_index <= 3:
                score += 4
            elif chunk_index <= 6:
                score += 2
            elif chunk_index >= 20:
                score -= 4
        if len(content.split()) < 80:
            score -= 2
        if self._looks_like_front_matter(content):
            score -= 10
        if self._looks_like_reference_chunk(content):
            score -= 18
        return score

    def _looks_like_front_matter(self, content: str) -> bool:
        lower = str(content or "").lower()
        return any(hint in lower for hint in self.FRONT_MATTER_HINTS)

    def _looks_like_reference_chunk(self, content: str) -> bool:
        lower = str(content or "").lower()
        year_hits = len(re.findall(r"\b(?:19|20)\d{2}\b", lower))
        if "references" in lower:
            return True
        if lower.count(" et al") >= 2:
            return True
        if "doi" in lower and year_hits >= 2:
            return True
        if year_hits >= 5:
            return True
        return False

    def _looks_like_table_or_caption(self, content: str) -> bool:
        lower = str(content or "").lower()
        return any(hint in lower for hint in self.TABLE_CAPTION_HINTS)

    def _looks_like_analytical_result_snippet(self, content: str) -> bool:
        lower = str(content or "").lower()
        return any(hint in lower for hint in self.ANALYTICAL_RESULT_HINTS)

    def _inject_special_evidence_candidates(
        self,
        *,
        selected: Sequence[Dict[str, Any]],
        scored_chunks: Sequence[Dict[str, Any]],
        max_selected_chunks: int,
        field_name: str,
        boost_explicit_organic_class: bool = False,
    ) -> List[Dict[str, Any]]:
        selected_list = list(selected)
        selected_indices = {int(item.get("chunk_index", 0) or 0) for item in selected_list}

        def _is_special(item: Dict[str, Any]) -> bool:
            content = str(item.get("content", ""))
            if field_name == "organic_compounds":
                return (
                    (boost_explicit_organic_class and bool(self._extract_explicit_organic_classes_from_text(content)))
                    or self._looks_like_table_or_caption(content)
                    or self._looks_like_analytical_result_snippet(content)
                )
            if field_name == "contamination_controls":
                return (
                    self._looks_like_table_or_caption(content)
                    or any(hint in content.lower() for hint in self.METHODS_HINTS)
                    or any(hint in content.lower() for hint in self.CONTAMINATION_HINTS)
                )
            return False

        if any(_is_special(item) for item in selected_list):
            if field_name != "organic_compounds" or not boost_explicit_organic_class:
                return selected_list[:max_selected_chunks]
            if any(self._extract_explicit_organic_classes_from_text(str(item.get("content", ""))) for item in selected_list):
                return selected_list[:max_selected_chunks]

        for item in scored_chunks:
            chunk_index = int(item.get("chunk_index", 0) or 0)
            if chunk_index in selected_indices:
                continue
            if self._looks_like_reference_chunk(str(item.get("content", ""))):
                continue
            if not _is_special(item):
                continue
            if len(selected_list) >= max_selected_chunks and selected_list:
                selected_list[-1] = item
            else:
                selected_list.append(item)
            break

        return selected_list[:max_selected_chunks]

    def _extract_explicit_organic_classes_from_text(self, text: str) -> List[str]:
        content = re.sub(r"\s+", " ", str(text or "")).strip()
        if not content:
            return []
        found: List[str] = []
        for pattern, target in self.ORGANIC_CLASS_RECALL_PATTERNS:
            if pattern.search(content):
                self._append_unique(found, target, max_items=8)
        return found

    def _augment_organic_raw_with_explicit_classes(
        self,
        *,
        existing_value: str,
        doc_name: str,
        selected_chunks: Sequence[Dict[str, Any]],
    ) -> str:
        combined: List[str] = []
        for token in ExtractionFieldPostprocessor.normalize_organic_compounds_list(existing_value):
            self._append_unique(combined, token, max_items=16)

        evidence_texts: List[str] = [doc_name]
        for chunk in selected_chunks:
            content = str(chunk.get("content", ""))
            if self._looks_like_reference_chunk(content):
                continue
            evidence_texts.append(content)

        for text in evidence_texts:
            for token in self._extract_explicit_organic_classes_from_text(text):
                self._append_unique(combined, token, max_items=16)

        return "; ".join(combined[:16])

    def _serialize_extraction_result(self, extracted: Any) -> Dict[str, Any]:
        if is_dataclass(extracted):
            return asdict(extracted)
        if hasattr(extracted, "__dict__"):
            return dict(extracted.__dict__)
        return dict(extracted)

    def _aggregate_chunk_predictions(self, chunk_results: Sequence[Dict[str, Any]]) -> Dict[str, str]:
        names: List[str] = []
        organics: List[str] = []
        controls: List[str] = []

        for result in chunk_results:
            data = result.get("data") or {}
            self._append_delimited_unique(
                names,
                ExtractionFieldPostprocessor.normalize_meteorite_name(data.get("name", "")),
                max_items=3,
            )
            for token in ExtractionFieldPostprocessor.normalize_organic_compounds_list(
                data.get("organic_compounds")
            ):
                self._append_unique(organics, token, max_items=12)
            for token in ExtractionFieldPostprocessor.normalize_contamination_controls_tokens(
                data.get("contamination_exclusion_method", "")
            ):
                self._append_unique(controls, token, max_items=8)

        return {
            "pred_meteorite_name": "; ".join(names[:3]),
            "pred_organic_compounds": "; ".join(organics[:12]),
            "pred_contamination_controls": "; ".join(controls[:8]),
        }

    def _apply_organic_alignment(
        self,
        aggregated: Dict[str, str],
        *,
        use_filter: bool,
        use_projection: bool,
    ) -> Dict[str, str]:
        aligned = dict(aggregated)
        raw_tokens = ExtractionFieldPostprocessor.normalize_organic_compounds_list(
            aggregated.get("pred_organic_compounds", "")
        )
        raw_tokens, filtered_tokens, projected_tokens, notes = align_organic_compounds_for_evaluation(
            raw_tokens,
            use_filter=use_filter,
            use_projection=use_projection,
        )
        aligned["pred_organic_compounds_raw"] = "; ".join(raw_tokens)
        aligned["pred_organic_compounds_filtered"] = "; ".join(filtered_tokens)
        aligned["pred_organic_compounds_projected"] = "; ".join(projected_tokens)
        aligned["pred_organic_filter_projection_notes"] = "; ".join(notes)
        if use_projection:
            aligned["pred_organic_compounds"] = aligned["pred_organic_compounds_projected"]
        elif use_filter:
            aligned["pred_organic_compounds"] = aligned["pred_organic_compounds_filtered"]
        else:
            aligned["pred_organic_compounds"] = aligned["pred_organic_compounds_raw"]
        return aligned

    def _append_delimited_unique(self, values: List[str], text: str, max_items: int) -> None:
        for part in re.split(r"[;,]", str(text or "")):
            self._append_unique(values, part, max_items=max_items)

    def _append_unique(self, values: List[str], item: str, max_items: int) -> None:
        cleaned = re.sub(r"\s+", " ", str(item or "")).strip()
        if not cleaned:
            return
        lowered = cleaned.lower()
        if any(existing.lower() == lowered for existing in values):
            return
        if len(values) >= max_items:
            return
        values.append(cleaned)

    def _preview_text(self, value: Any, max_chars: int = 180) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _build_comparison(
        self,
        *,
        baseline_summary_path: Path,
        rerun_summary_path: Path,
        out_path: Path,
    ) -> None:
        baseline = self._load_summary_rows(baseline_summary_path)
        rerun = self._load_summary_rows(rerun_summary_path)
        fields = (
            "meteorite_name",
            "organic_compounds",
            "contamination_controls",
            "overall_macro_avg",
        )
        rows = []
        for field in fields:
            before = baseline.get(field, {})
            after = rerun.get(field, {})
            row = {
                "field": field,
                "baseline_precision": before.get("precision", ""),
                "baseline_recall": before.get("recall", ""),
                "baseline_f1": before.get("f1", ""),
                "baseline_n_samples": before.get("n_samples", ""),
                "rerun_precision": after.get("precision", ""),
                "rerun_recall": after.get("recall", ""),
                "rerun_f1": after.get("f1", ""),
                "rerun_n_samples": after.get("n_samples", ""),
                "delta_precision": self._delta(before.get("precision"), after.get("precision")),
                "delta_recall": self._delta(before.get("recall"), after.get("recall")),
                "delta_f1": self._delta(before.get("f1"), after.get("f1")),
            }
            rows.append(row)
        self._write_csv(out_path, list(rows[0].keys()), rows)

    def _load_summary_rows(self, path: Path) -> Dict[str, Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return {
                str(row.get("field", "") or "").strip(): {k: str(v or "").strip() for k, v in row.items()}
                for row in reader
            }

    def _delta(self, before: Any, after: Any) -> str:
        try:
            return f"{float(after) - float(before):.4f}"
        except (TypeError, ValueError):
            return ""

    def _build_organic_error_analysis(
        self,
        *,
        rows: Sequence[Dict[str, str]],
        out_summary_path: Path,
        out_cases_path: Path,
    ) -> None:
        evaluated_rows = [row for row in rows if not self._should_skip_row(row)]
        category_counts = Counter()
        category_examples: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        cases: List[Dict[str, str]] = []

        for row in evaluated_rows:
            pred_eval_raw = row.get("pred_organic_compounds", "")
            pred_raw = row.get("pred_organic_compounds_raw", pred_eval_raw)
            pred_filtered = row.get("pred_organic_compounds_filtered", pred_raw)
            pred_projected = row.get("pred_organic_compounds_projected", pred_eval_raw)
            projection_notes = row.get("pred_organic_filter_projection_notes", "")
            gold_raw = row.get("gold_organic_compounds", "")
            pred_tokens = ExtractionFieldPostprocessor.normalize_organic_compounds_list(pred_eval_raw)
            pred_raw_tokens = ExtractionFieldPostprocessor.normalize_organic_compounds_list(pred_raw)
            gold_tokens = ExtractionFieldPostprocessor.normalize_organic_compounds_list(gold_raw)
            categories = self._categorize_organic_errors(
                pred_raw=pred_eval_raw,
                pred_tokens=pred_tokens,
                gold_tokens=gold_tokens,
                pred_raw_tokens=pred_raw_tokens,
                pred_filtered_raw=pred_filtered,
                pred_projected_raw=pred_projected,
                projection_notes=projection_notes,
            )
            if not categories:
                continue

            case = {
                "doc_id": row.get("doc_id", ""),
                "doc_name": row.get("doc_name", ""),
                "categories": "; ".join(categories),
                "pred_raw": pred_raw,
                "pred_filtered": pred_filtered,
                "pred_projected": pred_projected,
                "projection_notes": projection_notes,
                "gold_raw": gold_raw,
                "pred_tokens": "; ".join(pred_tokens),
                "pred_raw_tokens": "; ".join(pred_raw_tokens),
                "gold_tokens": "; ".join(gold_tokens),
                "missing_tokens": "; ".join(sorted(set(gold_tokens) - set(pred_tokens))),
                "extra_tokens": "; ".join(sorted(set(pred_tokens) - set(gold_tokens))),
            }
            cases.append(case)

            for category in categories:
                category_counts[category] += 1
                if len(category_examples[category]) < 3:
                    category_examples[category].append(case)

        summary_rows = []
        for category in self.CATEGORY_ORDER:
            examples = category_examples.get(category, [])
            summary_rows.append(
                {
                    "category": category,
                    "count": str(category_counts.get(category, 0)),
                    "example_doc_ids": "; ".join(example["doc_id"] for example in examples),
                }
            )

        self._write_csv(out_summary_path, ["category", "count", "example_doc_ids"], summary_rows)
        self._write_csv(
            out_cases_path,
            [
                "doc_id",
                "doc_name",
                "categories",
                "pred_raw",
                "pred_filtered",
                "pred_projected",
                "projection_notes",
                "gold_raw",
                "pred_tokens",
                "pred_raw_tokens",
                "gold_tokens",
                "missing_tokens",
                "extra_tokens",
            ],
            cases,
        )

    def _build_organic_error_comparison(
        self,
        *,
        baseline_summary_path: Path,
        rerun_summary_path: Path,
        out_path: Path,
    ) -> None:
        baseline_rows = self._load_error_summary_rows(baseline_summary_path)
        rerun_rows = self._load_error_summary_rows(rerun_summary_path)
        rows = []
        for category in self.CATEGORY_ORDER:
            before = int(baseline_rows.get(category, {}).get("count", "0") or 0)
            after = int(rerun_rows.get(category, {}).get("count", "0") or 0)
            rows.append(
                {
                    "category": category,
                    "baseline_count": str(before),
                    "rerun_count": str(after),
                    "delta_count": str(after - before),
                }
            )
        self._write_csv(out_path, ["category", "baseline_count", "rerun_count", "delta_count"], rows)

    def _load_error_summary_rows(self, path: Path) -> Dict[str, Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return {
                str(row.get("category", "") or "").strip(): {k: str(v or "").strip() for k, v in row.items()}
                for row in reader
            }

    def _categorize_organic_errors(
        self,
        pred_raw: str,
        pred_tokens: Sequence[str],
        gold_tokens: Sequence[str],
        pred_raw_tokens: Sequence[str],
        pred_filtered_raw: str,
        pred_projected_raw: str,
        projection_notes: str,
    ) -> List[str]:
        pred_set = set(pred_tokens)
        gold_set = set(gold_tokens)
        categories: List[str] = []

        if not pred_set and gold_set:
            categories.append("field_empty_or_missing")

        if gold_set - pred_set:
            categories.append("missed_extraction")

        extras = pred_set - gold_set
        if extras:
            if any(token in self.BROAD_ORGANIC_TOKENS for token in extras):
                categories.append("over_broad_or_generalized")
            else:
                categories.append("wrong_extraction")

        if self._has_normalization_or_projection_issue(
            pred_raw=pred_raw,
            pred_tokens=pred_tokens,
            pred_raw_tokens=pred_raw_tokens,
            pred_filtered_raw=pred_filtered_raw,
            pred_projected_raw=pred_projected_raw,
            projection_notes=projection_notes,
        ):
            categories.append("normalization_or_projection_issue")

        if self._has_duplicate_or_conflict(pred_raw, pred_tokens):
            categories.append("duplicate_or_conflict")

        return categories

    def _has_normalization_or_projection_issue(
        self,
        *,
        pred_raw: str,
        pred_tokens: Sequence[str],
        pred_raw_tokens: Sequence[str],
        pred_filtered_raw: str,
        pred_projected_raw: str,
        projection_notes: str,
    ) -> bool:
        raw_text = str(pred_raw or "").strip()
        if raw_text and not pred_tokens:
            return True
        lower_raw = raw_text.lower()
        pred_set = set(pred_tokens)
        for canonical, patterns in self.NORMALIZATION_PATTERNS.items():
            if any(re.search(pattern, lower_raw, re.IGNORECASE) for pattern in patterns):
                if canonical not in pred_set:
                    return True
        filtered_text = str(pred_filtered_raw or "").strip()
        projected_text = str(pred_projected_raw or "").strip()
        if filtered_text and projected_text and filtered_text != projected_text:
            return True
        if list(pred_raw_tokens) and list(pred_raw_tokens) != list(pred_tokens):
            return True
        if str(projection_notes or "").strip():
            return True
        return False

    def _has_duplicate_or_conflict(self, pred_raw: str, pred_tokens: Sequence[str]) -> bool:
        raw_parts = [
            re.sub(r"\s+", " ", part).strip().lower()
            for part in re.split(r"[;,\uFF0C\uFF1B\u3001]+", str(pred_raw or ""))
            if re.sub(r"\s+", " ", part).strip()
        ]
        if len(raw_parts) != len(set(raw_parts)):
            return True

        pred_set = set(pred_tokens)
        for left, right in self.DUPLICATE_CONFLICT_PAIRS:
            if left in pred_set and right in pred_set:
                return True
        return False

    def _write_csv(
        self,
        path: Path,
        fieldnames: Sequence[str],
        rows: Sequence[Dict[str, str]],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
