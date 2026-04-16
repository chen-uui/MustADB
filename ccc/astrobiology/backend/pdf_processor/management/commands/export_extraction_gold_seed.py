import csv
import re
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from meteorite_search.models import SingleTaskExtractionSession
from meteorite_search.review_models import ApprovedMeteorite, PendingMeteorite, RejectedMeteorite
from pdf_processor.extraction_postprocess import ExtractionFieldPostprocessor
from pdf_processor.models import DirectProcessingResult, DocumentChunk, PDFDocument


class Command(BaseCommand):
    help = "Export seed CSV for manual extraction gold annotation."

    CSV_COLUMNS = [
        "doc_id",
        "doc_name",
        "doc_filename",
        "doc_year",
        "doc_journal",
        "prediction_sources",
        "evidence_document_id",
        "evidence_title",
        "evidence_segment_ids",
        "evidence_snippet",
        "pred_meteorite_name",
        "pred_organic_compounds",
        "pred_contamination_controls",
        "in_scope",
        "skip_row",
        "notes",
        "gold_meteorite_name",
        "gold_organic_compounds",
        "gold_contamination_controls",
    ]
    ANNOTATION_COLUMNS = [
        "in_scope",
        "skip_row",
        "notes",
        "gold_meteorite_name",
        "gold_organic_compounds",
        "gold_contamination_controls",
    ]
    PLACEHOLDER_TEXTS = {
        "",
        "unknown",
        "not specified",
        "none",
        "null",
        "n/a",
        "na",
    }
    DOMAIN_KEYWORDS = (
        "meteorite",
        "martian",
        "mars",
        "chondrite",
        "asteroid",
        "ryugu",
        "bennu",
        "organic",
        "extraterrestrial",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session_cache: Dict[str, Optional[SingleTaskExtractionSession]] = {}

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of samples to export. Default: 10.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output CSV path. Default: evaluation/gold_seed.csv",
        )

    def handle(self, *args, **options):
        limit = int(options["limit"])
        if limit < 1:
            raise CommandError("--limit must be >= 1")

        out_path = self._resolve_out_path(options.get("out"))
        out_path.parent.mkdir(parents=True, exist_ok=True)

        existing_rows = self._load_existing_rows(out_path)
        pred_by_doc = self._collect_doc_predictions()
        docs = self._select_documents(limit=limit, pred_by_doc=pred_by_doc, existing_rows=existing_rows)
        if not docs:
            raise CommandError("no PDFDocument rows available for export")

        rows: List[Dict[str, str]] = []
        with_pred = 0
        domain_hit_count = 0
        restored_annotation_rows = 0

        for doc in docs:
            doc_id = str(doc.id)
            pred = pred_by_doc.get(doc_id, {})
            row = {
                "doc_id": doc_id,
                "doc_name": self._build_doc_name(doc),
                "doc_filename": self._clean_export_value(doc.filename),
                "doc_year": self._clean_export_value(doc.year),
                "doc_journal": self._clean_export_value(doc.journal),
                "prediction_sources": self._clean_export_value(pred.get("prediction_sources")),
                "evidence_document_id": self._clean_export_value(pred.get("evidence_document_id")),
                "evidence_title": self._clean_export_value(pred.get("evidence_title")),
                "evidence_segment_ids": self._clean_export_value(pred.get("evidence_segment_ids")),
                "evidence_snippet": self._clean_export_value(pred.get("evidence_snippet")),
                "pred_meteorite_name": self._clean_export_value(pred.get("pred_meteorite_name")),
                "pred_organic_compounds": self._clean_export_value(pred.get("pred_organic_compounds")),
                "pred_contamination_controls": self._clean_export_value(pred.get("pred_contamination_controls")),
                "in_scope": "",
                "skip_row": "",
                "notes": "",
                "gold_meteorite_name": "",
                "gold_organic_compounds": "",
                "gold_contamination_controls": "",
            }

            existing_row = existing_rows.get(doc_id)
            if existing_row:
                for col in self.ANNOTATION_COLUMNS:
                    row[col] = str(existing_row.get(col, "") or "").strip()
                if self._row_has_annotation(existing_row):
                    restored_annotation_rows += 1

            if row["pred_meteorite_name"] or row["pred_organic_compounds"] or row["pred_contamination_controls"]:
                with_pred += 1
            if self._contains_domain_keyword(
                " ".join(
                    [
                        row["doc_name"],
                        row["pred_meteorite_name"],
                        row["pred_organic_compounds"],
                        row["pred_contamination_controls"],
                    ]
                )
            ):
                domain_hit_count += 1

            rows.append(row)

        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(f"selected_docs={len(rows)}")
        self.stdout.write(f"docs_with_prediction={with_pred}")
        self.stdout.write(f"docs_with_domain_keywords={domain_hit_count}")
        self.stdout.write(f"restored_annotation_rows={restored_annotation_rows}")
        self.stdout.write(f"out_path={out_path}")

    def _resolve_out_path(self, out_arg: Optional[str]) -> Path:
        if out_arg and out_arg.strip():
            return Path(out_arg).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation" / "gold_seed.csv").resolve()

    def _load_existing_rows(self, out_path: Path) -> Dict[str, Dict[str, str]]:
        if not out_path.exists():
            return {}
        with out_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return {}
            rows: Dict[str, Dict[str, str]] = {}
            for row in reader:
                doc_id = str(row.get("doc_id", "") or "").strip()
                if not doc_id:
                    continue
                rows[doc_id] = {k: str(row.get(k, "") or "").strip() for k in self.CSV_COLUMNS}
            return rows

    def _row_has_annotation(self, row: Dict[str, str]) -> bool:
        for col in self.ANNOTATION_COLUMNS:
            if str(row.get(col, "") or "").strip():
                return True
        return False

    def _select_documents(
        self,
        *,
        limit: int,
        pred_by_doc: Dict[str, Dict[str, str]],
        existing_rows: Dict[str, Dict[str, str]],
    ) -> List[PDFDocument]:
        processed_docs = list(PDFDocument.objects.filter(processed=True).order_by("-upload_date", "-id"))
        if not processed_docs:
            processed_docs = list(PDFDocument.objects.all().order_by("-upload_date", "-id"))
        if not processed_docs:
            return []

        ranked_rows = []
        for idx, doc in enumerate(processed_docs):
            doc_id = str(doc.id)
            pred = pred_by_doc.get(doc_id, {})
            pred_meteorite_name = self._clean_export_value(pred.get("pred_meteorite_name"))
            pred_organic = self._clean_export_value(pred.get("pred_organic_compounds"))
            pred_contam = self._clean_export_value(pred.get("pred_contamination_controls"))
            has_pred = bool(pred_meteorite_name or pred_organic or pred_contam)
            doc_name = self._build_doc_name(doc)
            domain_hit = self._contains_domain_keyword(
                " ".join([doc_name, pred_meteorite_name, pred_organic, pred_contam])
            )

            existing_row = existing_rows.get(doc_id, {})
            has_annotation = self._row_has_annotation(existing_row)

            ranked_rows.append(
                {
                    "doc": doc,
                    "idx": idx,
                    "has_annotation": has_annotation,
                    "has_pred": has_pred,
                    "domain_hit": domain_hit,
                }
            )

        ranked_rows.sort(
            key=lambda item: (
                0 if item["has_annotation"] else 1,
                0 if item["has_pred"] else 1,
                0 if item["domain_hit"] else 1,
                item["idx"],
            )
        )
        return [item["doc"] for item in ranked_rows[:limit]]

    def _collect_doc_predictions(self) -> Dict[str, Dict[str, str]]:
        buckets: Dict[str, Dict[str, List[str]]] = defaultdict(
            lambda: {
                "meteorite": [],
                "organic": [],
                "contam": [],
                "sources": [],
                "evidence_document_ids": [],
                "evidence_titles": [],
                "evidence_segment_ids": [],
                "evidence_snippets": [],
            }
        )

        self._collect_from_review_model(PendingMeteorite, buckets, source_label="pending_review")
        self._collect_from_review_model(ApprovedMeteorite, buckets, source_label="approved_review")
        self._collect_from_review_model(RejectedMeteorite, buckets, source_label="rejected_review")
        self._collect_from_direct_results(buckets)

        out: Dict[str, Dict[str, str]] = {}
        for doc_id, values in buckets.items():
            meteorite = self._join_values(values["meteorite"], max_items=3)
            organic = self._join_values(values["organic"], max_items=8)
            contam = self._join_values(values["contam"], max_items=8)
            if meteorite or organic or contam:
                out[doc_id] = {
                    "pred_meteorite_name": meteorite,
                    "pred_organic_compounds": organic,
                    "pred_contamination_controls": contam,
                    "prediction_sources": self._join_values(values["sources"], max_items=6),
                    "evidence_document_id": self._join_values(values["evidence_document_ids"], max_items=3),
                    "evidence_title": self._join_values(values["evidence_titles"], max_items=2),
                    "evidence_segment_ids": self._join_values(values["evidence_segment_ids"], max_items=6),
                    "evidence_snippet": " || ".join(values["evidence_snippets"][:2]),
                }
        return out

    def _collect_from_review_model(
        self,
        model_cls: Any,
        buckets: Dict[str, Dict[str, List[str]]],
        *,
        source_label: str,
    ) -> None:
        for row in model_cls.objects.order_by("-created_at").iterator(chunk_size=500):
            metadata = row.extraction_metadata if isinstance(row.extraction_metadata, dict) else {}
            doc_id = self._extract_doc_id_from_metadata(metadata)
            if not doc_id:
                continue

            bucket = buckets[doc_id]
            name = ExtractionFieldPostprocessor.normalize_meteorite_name(getattr(row, "name", ""))
            organic = ExtractionFieldPostprocessor.normalize_organic_compounds_text(
                getattr(row, "organic_compounds", None)
            )
            contam = ExtractionFieldPostprocessor.normalize_contamination_controls_text(
                getattr(row, "contamination_exclusion_method", "")
            )

            self._append_delimited_values(bucket["meteorite"], name)
            self._append_delimited_values(bucket["organic"], organic)
            self._append_delimited_values(bucket["contam"], contam)
            self._append_unique(bucket["sources"], source_label, max_items=6)

            evidence = self._extract_review_evidence(metadata)
            self._append_unique(bucket["evidence_document_ids"], evidence.get("document_id", ""), max_items=3)
            self._append_unique(bucket["evidence_titles"], evidence.get("title", ""), max_items=2)
            self._append_unique(bucket["evidence_snippets"], evidence.get("snippet", ""), max_items=2)
            for segment_id in evidence.get("segment_ids", []):
                self._append_unique(bucket["evidence_segment_ids"], segment_id, max_items=6)

    def _collect_from_direct_results(self, buckets: Dict[str, Dict[str, List[str]]]) -> None:
        for row in DirectProcessingResult.objects.order_by("-created_at").iterator(chunk_size=200):
            doc = (
                PDFDocument.objects.filter(file_path=str(row.document_path))
                .order_by("-upload_date")
                .only("id")
                .first()
            )
            if not doc:
                continue

            doc_id = str(doc.id)
            bucket = buckets[doc_id]
            name = self._extract_meteorite_name_from_payload(row.meteorite_data)
            organic = ExtractionFieldPostprocessor.normalize_organic_compounds_text(row.organic_compounds)
            contam = self._extract_contamination_from_payload(row.scientific_insights)

            self._append_delimited_values(bucket["meteorite"], name)
            self._append_delimited_values(bucket["organic"], organic)
            self._append_delimited_values(bucket["contam"], contam)
            self._append_unique(bucket["sources"], "direct_processing", max_items=6)

    def _extract_doc_id_from_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        direct_keys = (
            "doc_id",
            "document_id",
            "pdf_document_id",
            "source_document_id",
            "source_doc_id",
        )
        for key in direct_keys:
            normalized = self._normalize_uuid(metadata.get(key))
            if normalized:
                return normalized

        segment_ids = metadata.get("segment_ids")
        if isinstance(segment_ids, list):
            for item in segment_ids:
                text = str(item or "").strip()
                if not text:
                    continue
                normalized = self._normalize_uuid(text.split(":", 1)[0])
                if normalized:
                    return normalized
        return None

    def _normalize_uuid(self, raw: Any) -> Optional[str]:
        text = str(raw or "").strip()
        if not text:
            return None
        try:
            return str(uuid.UUID(text))
        except ValueError:
            return None

    def _extract_review_evidence(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        evidence = {
            "document_id": self._clean_export_value(
                metadata.get("source_document_id")
                or metadata.get("document_id")
                or metadata.get("doc_id")
            ),
            "title": self._clean_export_value(
                metadata.get("evidence_title") or metadata.get("source_title")
            ),
            "segment_ids": self._coerce_string_list(
                metadata.get("evidence_segment_ids") or metadata.get("segment_ids")
            ),
            "snippet": self._clean_export_value(
                self._join_snippets(metadata.get("evidence_snippets"))
            ),
        }

        session_id = self._clean_export_value(metadata.get("session_id"))
        entity_id = self._clean_export_value(metadata.get("entity_id"))
        if session_id:
            session_evidence = self._extract_session_evidence(session_id, entity_id)
            if not evidence["document_id"]:
                evidence["document_id"] = session_evidence.get("document_id", "")
            if not evidence["title"]:
                evidence["title"] = session_evidence.get("title", "")
            if not evidence["segment_ids"]:
                evidence["segment_ids"] = session_evidence.get("segment_ids", [])
            if not evidence["snippet"]:
                evidence["snippet"] = session_evidence.get("snippet", "")
        if not evidence["snippet"] and evidence["segment_ids"]:
            evidence["snippet"] = self._extract_chunk_snippet(evidence["segment_ids"])
        return evidence

    def _extract_session_evidence(self, session_id: str, entity_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            return {"document_id": "", "title": "", "segment_ids": [], "snippet": ""}

        aggregated_results = session.aggregated_results if isinstance(session.aggregated_results, dict) else {}
        agg_data = aggregated_results.get(entity_id) if entity_id else None
        if not agg_data and len(aggregated_results) == 1:
            agg_data = next(iter(aggregated_results.values()))
        if not isinstance(agg_data, dict):
            return {"document_id": "", "title": "", "segment_ids": [], "snippet": ""}

        segments = agg_data.get("segments")
        if not isinstance(segments, list):
            return {"document_id": "", "title": "", "segment_ids": [], "snippet": ""}

        document_id = ""
        title = ""
        segment_ids: List[str] = []
        snippets: List[str] = []
        segments_data = session.segments_data if isinstance(session.segments_data, dict) else {}

        for seg in segments[:3]:
            if not isinstance(seg, dict):
                continue
            segment_id = self._clean_export_value(seg.get("id"))
            if segment_id:
                segment_ids.append(segment_id)
            if not document_id:
                document_id = self._clean_export_value(seg.get("documentId"))
            if segment_id and not title:
                segment_meta = segments_data.get(segment_id)
                if isinstance(segment_meta, dict):
                    title = self._clean_export_value(segment_meta.get("title"))
            snippet = self._make_evidence_snippet(seg.get("content"))
            if snippet:
                snippets.append(snippet)

        return {
            "document_id": document_id,
            "title": title,
            "segment_ids": segment_ids[:5],
            "snippet": self._clean_export_value(" || ".join(snippets[:2])),
        }

    def _get_session(self, session_id: str) -> Optional[SingleTaskExtractionSession]:
        if session_id in self._session_cache:
            return self._session_cache[session_id]
        session = SingleTaskExtractionSession.objects.filter(session_id=session_id).first()
        self._session_cache[session_id] = session
        return session

    def _extract_chunk_snippet(self, segment_ids: List[str]) -> str:
        snippets: List[str] = []
        for segment_id in segment_ids[:2]:
            document_id, _, chunk_index_text = str(segment_id).partition(":")
            normalized_document_id = self._normalize_uuid(document_id)
            if not normalized_document_id or not chunk_index_text.isdigit():
                continue
            chunk = (
                DocumentChunk.objects.filter(
                    document_id=normalized_document_id,
                    chunk_index=int(chunk_index_text),
                )
                .only("content")
                .first()
            )
            if not chunk:
                continue
            snippet = self._make_evidence_snippet(chunk.content)
            if snippet:
                snippets.append(snippet)
        return self._clean_export_value(" || ".join(snippets[:2]))

    def _extract_meteorite_name_from_payload(self, payload: Any) -> str:
        if isinstance(payload, dict):
            for key in ("name", "meteorite_name", "details"):
                normalized = ExtractionFieldPostprocessor.normalize_meteorite_name(payload.get(key))
                if normalized:
                    return normalized
        return ExtractionFieldPostprocessor.normalize_meteorite_name(payload)

    def _extract_contamination_from_payload(self, payload: Any) -> str:
        if isinstance(payload, dict):
            for key in ("contamination_exclusion_method", "contamination_controls", "details"):
                normalized = ExtractionFieldPostprocessor.normalize_contamination_controls_text(payload.get(key))
                if normalized:
                    return normalized
        return ExtractionFieldPostprocessor.normalize_contamination_controls_text(payload)

    def _append_delimited_values(self, values: List[str], text: str, max_items: int = 12) -> None:
        if not text:
            return
        parts = re.split(r"[;,]", text)
        for part in parts:
            normalized = self._clean_export_value(part)
            if not normalized:
                continue
            self._append_unique(values, normalized, max_items=max_items)

    def _append_unique(self, values: List[str], item: str, max_items: int) -> None:
        if not item:
            return
        lowered = item.lower()
        for existing in values:
            if existing.lower() == lowered:
                return
        if len(values) >= max_items:
            return
        values.append(item)

    def _join_values(self, values: List[str], max_items: int) -> str:
        if not values:
            return ""
        return "; ".join(values[:max_items])

    def _build_doc_name(self, doc: PDFDocument) -> str:
        candidates = [
            getattr(doc, "title", ""),
            Path(str(getattr(doc, "filename", "") or "")).stem,
            getattr(doc, "filename", ""),
        ]
        for candidate in candidates:
            cleaned = self._clean_export_value(doc.clean_title(candidate) if candidate else "")
            if cleaned:
                return cleaned
        return self._clean_export_value(str(doc.id))

    def _join_snippets(self, value: Any) -> str:
        parts = [self._make_evidence_snippet(item) for item in self._coerce_string_list(value)]
        parts = [part for part in parts if part]
        return " || ".join(parts[:2])

    def _coerce_string_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._clean_export_value(item) for item in value if self._clean_export_value(item)]
        text = self._clean_export_value(value)
        if not text:
            return []
        if "||" in text:
            return [self._clean_export_value(part) for part in text.split("||") if self._clean_export_value(part)]
        if ";" in text:
            return [self._clean_export_value(part) for part in text.split(";") if self._clean_export_value(part)]
        return [text]

    def _make_evidence_snippet(self, value: Any, max_chars: int = 280) -> str:
        text = self._clean_export_value(value)
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _clean_export_value(self, value: Any) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            return ""
        lowered = text.lower()
        if lowered in self.PLACEHOLDER_TEXTS:
            return ""
        if text in {"{}", "[]"}:
            return ""
        return text

    def _contains_domain_keyword(self, text: str) -> bool:
        lowered = str(text or "").lower()
        return any(keyword in lowered for keyword in self.DOMAIN_KEYWORDS)
