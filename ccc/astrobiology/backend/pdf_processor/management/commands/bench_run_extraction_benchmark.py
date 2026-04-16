import csv
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import numpy as np
import weaviate
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from meteorite_search.models import DataExtractionTask
from pdf_processor.bench_logging import append_bench_log, normalize_config
from pdf_processor.models import PDFDocument
from pdf_processor.pdf_utils import PDFUtils
from pdf_processor.weaviate_services import WeaviateVectorService


class Command(BaseCommand):
    help = "Run real extraction/ingestion benchmark with per-document stage timings."

    DOC_STAGE_KEYS = ("ocr", "chunk", "embed", "vector_write", "db_write", "total")

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of documents to benchmark. Default: 10.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/extraction_<timestamp>/",
        )
        parser.add_argument(
            "--sample-mode",
            choices=("recent", "all"),
            default="recent",
            help="Document sampling mode. recent: latest docs, all: oldest-first pool.",
        )
        parser.add_argument(
            "--task-ids",
            nargs="+",
            default=None,
            help="Optional task_id/run_id filter for fallback historical summary.",
        )

    def handle(self, *args, **options):
        limit = int(options["limit"])
        if limit <= 0:
            raise CommandError("--limit must be >= 1")

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        raw_doc_path = out_dir / "raw_extraction_doc.jsonl"
        summary_doc_path = out_dir / "summary_extraction_doc.csv"
        raw_task_path = out_dir / "raw_extraction_task.jsonl"
        summary_task_path = out_dir / "summary_extraction_task.csv"
        raw_doc_path.write_text("", encoding="utf-8")
        raw_task_path.write_text("", encoding="utf-8")

        sample_mode = str(options["sample_mode"]).strip()
        task_ids = self._normalize_id_set(options.get("task_ids"))
        run_id = str(uuid.uuid4())
        bench_log_path = self._resolve_bench_log_path()

        self.stdout.write(f"bench_log_path={bench_log_path}")
        self.stdout.write(f"sample_mode={sample_mode} limit={limit}")

        doc_rows: List[Dict[str, Any]] = []
        task_rows: List[Dict[str, Any]] = []

        docs = self._select_documents(limit=limit, sample_mode=sample_mode)
        self.stdout.write(f"selected_docs={len(docs)}")

        if docs:
            real_doc_rows, real_task_rows = self._run_real_document_benchmark(
                docs=docs,
                run_id=run_id,
                raw_doc_path=raw_doc_path,
                raw_task_path=raw_task_path,
            )
            doc_rows.extend(real_doc_rows)
            task_rows.extend(real_task_rows)
        else:
            self.stdout.write("no documents selected from PDFDocument; fallback to historical task_db records")

        if not doc_rows:
            fallback_rows = self._load_history_fallback(limit=limit, sample_mode=sample_mode, task_ids=task_ids)
            for row in fallback_rows:
                self._append_jsonl(raw_doc_path, row)
            doc_rows.extend(fallback_rows)
            self.stdout.write(f"fallback_rows={len(fallback_rows)}")

        summary_doc_row = self._build_doc_summary(doc_rows)
        self._write_doc_summary(summary_doc_path, summary_doc_row)

        if task_rows:
            summary_task_row = self._build_task_summary(task_rows)
            self._write_task_summary(summary_task_path, summary_task_row)
        else:
            summary_task_row = None

        n_success = int(summary_doc_row["n_success"])
        if n_success < 10:
            self.stdout.write("INSUFFICIENT_SAMPLE")
            self.stdout.write(
                f"available_success_docs={n_success} required_success_docs=10 attempted_docs={len(doc_rows)}"
            )

        self.stdout.write(f"completed doc_total={summary_doc_row['n_total']} doc_success={summary_doc_row['n_success']} doc_fail={summary_doc_row['n_fail']}")
        if summary_task_row:
            self.stdout.write(f"task_total={summary_task_row['n_total']} task_success={summary_task_row['n_success']} task_fail={summary_task_row['n_fail']}")
        self.stdout.write(f"out_dir={out_dir}")
        self.stdout.write(f"raw_extraction_doc={raw_doc_path}")
        self.stdout.write(f"summary_extraction_doc={summary_doc_path}")
        if summary_task_row:
            self.stdout.write(f"raw_extraction_task={raw_task_path}")
            self.stdout.write(f"summary_extraction_task={summary_task_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and out_arg.strip():
            return Path(out_arg).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"extraction_{ts}").resolve()

    def _resolve_bench_log_path(self) -> Path:
        override = os.getenv("BENCH_LOG_PATH", "").strip()
        if override:
            return Path(override).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "logs" / "bench_log.jsonl").resolve()

    def _normalize_id_set(self, values: Optional[Sequence[str]]) -> Set[str]:
        if not values:
            return set()
        return {str(v).strip() for v in values if str(v).strip()}

    def _select_documents(self, limit: int, sample_mode: str) -> List[PDFDocument]:
        order_field = "-upload_date" if sample_mode == "recent" else "upload_date"
        pool_size = max(limit * 20, limit)
        queryset = (
            PDFDocument.objects.exclude(file_path__isnull=True)
            .exclude(file_path="")
            .order_by(order_field)
        )
        candidates = list(queryset[:pool_size])

        existing: List[PDFDocument] = []
        for doc in candidates:
            path = Path(str(doc.file_path))
            if path.exists() and path.is_file():
                existing.append(doc)

        if len(existing) <= limit:
            return existing

        # Prefer smaller files from the selected pool to keep benchmark runnable.
        existing.sort(key=lambda d: int(d.file_size or 0))
        return existing[:limit]

    def _run_real_document_benchmark(
        self,
        *,
        docs: List[PDFDocument],
        run_id: str,
        raw_doc_path: Path,
        raw_task_path: Path,
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        vector_service = WeaviateVectorService()
        vector_service.create_collection_if_not_exists(vector_service.collection_name)

        doc_rows: List[Dict[str, Any]] = []
        task_rows: List[Dict[str, Any]] = []

        # Keep task-level stats meaningful by splitting into small real batches.
        task_batch_size = 5
        for start in range(0, len(docs), task_batch_size):
            task_docs = docs[start : start + task_batch_size]
            task_id = str(uuid.uuid4())
            task = DataExtractionTask.objects.create(  # type: ignore[call-arg]
                task_id=task_id,
                task_type="batch_documents",
                status="running",
                parameters={
                    "benchmark_run_id": run_id,
                    "benchmark_type": "extraction_doc",
                    "doc_ids": [str(d.id) for d in task_docs],
                },
                total_documents=len(task_docs),
                processed_documents=0,
                successful_extractions=0,
                failed_extractions=0,
                started_at=timezone.now(),
            )

            task_start = time.perf_counter()
            task_success_count = 0
            task_fail_count = 0

            for doc in task_docs:
                doc_row = self._process_single_document(
                    vector_service=vector_service,
                    run_id=run_id,
                    task_id=task_id,
                    doc=doc,
                )
                doc_rows.append(doc_row)
                self._append_jsonl(raw_doc_path, doc_row)

                if doc_row["success"]:
                    task_success_count += 1
                else:
                    task_fail_count += 1

                task.processed_documents = task_success_count + task_fail_count
                task.successful_extractions = task_success_count
                task.failed_extractions = task_fail_count
                task.save(update_fields=["processed_documents", "successful_extractions", "failed_extractions"])

            task_total_ms = (time.perf_counter() - task_start) * 1000.0
            task_success = task_success_count == len(task_docs)
            task.status = "completed" if task_success else "failed"
            task.completed_at = timezone.now()
            task.results = {
                "benchmark": True,
                "benchmark_run_id": run_id,
                "stage_ms_keys": list(self.DOC_STAGE_KEYS),
                "latest_progress": {
                    "total_documents": len(task_docs),
                    "processed_documents": len(task_docs),
                    "successful_extractions": task_success_count,
                    "failed_extractions": task_fail_count,
                },
                "processing_stats": {
                    "processing_time_seconds": task_total_ms / 1000.0,
                    "processed_documents": len(task_docs),
                    "documents_per_minute": (len(task_docs) / (task_total_ms / 60000.0))
                    if task_total_ms > 0
                    else 0.0,
                },
            }
            task.save(update_fields=["status", "completed_at", "results"])

            task_row = {
                "run_id": run_id,
                "task_id": task_id,
                "doc_count": len(task_docs),
                "success": task_success,
                "error_type": None if task_success else "PARTIAL_DOC_FAILURE",
                "total_ms": task_total_ms,
                "docs_per_min": (len(task_docs) / (task_total_ms / 60000.0))
                if task_total_ms > 0
                else 0.0,
            }
            task_rows.append(task_row)
            self._append_jsonl(raw_task_path, task_row)

        return doc_rows, task_rows

    def _process_single_document(
        self,
        *,
        vector_service: WeaviateVectorService,
        run_id: str,
        task_id: str,
        doc: PDFDocument,
    ) -> Dict[str, Any]:
        stage_ms = {k: 0.0 for k in self.DOC_STAGE_KEYS}
        doc_total_start = time.perf_counter()
        success = False
        error_type: Optional[str] = None

        try:
            pdf_path = str(doc.file_path)
            if not pdf_path or not Path(pdf_path).exists():
                raise FileNotFoundError(f"PDF_NOT_FOUND:{pdf_path}")

            # OCR stage: current default pipeline is text extraction; OCR not triggered unless dedicated OCR flow is used.
            stage_ms["ocr"] = 0.0

            chunk_start = time.perf_counter()
            extraction = PDFUtils.extract_text_and_chunks(pdf_path)
            stage_ms["chunk"] = (time.perf_counter() - chunk_start) * 1000.0
            if not extraction.get("success"):
                raise RuntimeError(str(extraction.get("error") or "EXTRACT_CHUNK_FAILED"))

            raw_chunks = extraction.get("chunks") or []
            if not raw_chunks:
                raise RuntimeError("NO_CHUNKS_EXTRACTED")

            weaviate_chunks: List[Dict[str, Any]] = []
            for chunk in raw_chunks:
                weaviate_chunks.append(
                    {
                        "content": chunk.get("chunk_text", ""),
                        "length": chunk.get("chunk_length", 0),
                        "sentences": len(str(chunk.get("chunk_text", "")).split(".")),
                        "page_number": int(chunk.get("page_number", 0) or 0),
                        "chunk_index": int(chunk.get("chunk_index", 0) or 0),
                    }
                )

            texts = [item["content"] for item in weaviate_chunks]
            embed_start = time.perf_counter()
            embeddings = vector_service.embedding_service.encode(texts)
            stage_ms["embed"] = (time.perf_counter() - embed_start) * 1000.0

            vector_start = time.perf_counter()
            vector_service.delete_documents_by_id(str(doc.id), vector_service.collection_name)

            client = vector_service.weaviate_connection.get_client()
            if client is None:
                raise RuntimeError("WEAVIATE_CLIENT_UNAVAILABLE")
            collection = client.collections.get(vector_service.collection_name)

            batch_data = []
            for item, embedding in zip(weaviate_chunks, embeddings):
                batch_data.append(
                    weaviate.classes.data.DataObject(
                        properties={
                            "content": item["content"],
                            "document_id": str(doc.id),
                            "title": str(doc.title or doc.filename or ""),
                            "page_number": item["page_number"],
                            "chunk_index": item["chunk_index"],
                        },
                        vector=embedding,
                    )
                )
            response = collection.data.insert_many(batch_data)
            if response.has_errors:
                raise RuntimeError("WEAVIATE_INSERT_FAILED")
            stage_ms["vector_write"] = (time.perf_counter() - vector_start) * 1000.0

            db_start = time.perf_counter()
            doc.processed = True
            total_pages = int(extraction.get("total_pages") or doc.page_count or 0)
            doc.page_count = total_pages
            doc.save(update_fields=["processed", "page_count"])
            stage_ms["db_write"] = (time.perf_counter() - db_start) * 1000.0

            success = True
        except Exception as exc:
            error_type = type(exc).__name__
        finally:
            stage_ms["total"] = (time.perf_counter() - doc_total_start) * 1000.0

        total_ms = float(stage_ms["total"])
        docs_per_min = 60000.0 / total_ms if total_ms > 0 else 0.0
        row = {
            "run_id": run_id,
            "task_id": task_id,
            "doc_id": str(doc.id),
            "doc_name": str(doc.filename or ""),
            "success": success,
            "error_type": error_type,
            "stage_ms": stage_ms,
            "total_ms": total_ms,
            "docs_per_min": docs_per_min,
        }

        append_bench_log(
            run_id=str(uuid.uuid4()),
            endpoint="extract_task",
            success=success,
            error_type=error_type,
            config=normalize_config(
                {
                    "retrieval_mode": "extraction_benchmark_doc",
                    "top_k": None,
                    "rerank_k": None,
                    "hybrid_alpha": None,
                    "context_token_limit": None,
                }
            ),
            stage_ms=stage_ms,
            extra={
                "task_id": task_id,
                "doc_id": str(doc.id),
                "benchmark_run_id": run_id,
            },
        )
        return row

    def _load_history_fallback(
        self, *, limit: int, sample_mode: str, task_ids: Set[str]
    ) -> List[Dict[str, Any]]:
        order = "-created_at" if sample_mode == "recent" else "created_at"
        queryset = DataExtractionTask.objects.all().order_by(order)
        if task_ids:
            queryset = queryset.filter(task_id__in=list(task_ids))

        rows: List[Dict[str, Any]] = []
        for task in queryset[:limit]:
            status = str(task.status or "").lower()
            success = status in {"completed", "preview_ready"}
            total_ms = self._task_total_ms(task)
            doc_count = int(task.processed_documents or task.total_documents or 0)
            docs_per_min = (doc_count / (total_ms / 60000.0)) if total_ms > 0 and doc_count > 0 else 0.0
            rows.append(
                {
                    "run_id": None,
                    "task_id": str(task.task_id),
                    "doc_id": None,
                    "doc_name": "",
                    "success": success,
                    "error_type": None if success else f"TASK_STATUS_{status.upper()}",
                    "stage_ms": {
                        "ocr": 0.0,
                        "chunk": 0.0,
                        "embed": 0.0,
                        "vector_write": 0.0,
                        "db_write": 0.0,
                        "total": total_ms,
                    },
                    "total_ms": total_ms,
                    "docs_per_min": docs_per_min,
                }
            )
        return rows

    def _task_total_ms(self, task: DataExtractionTask) -> float:
        results = task.results or {}
        processing_stats = results.get("processing_stats") if isinstance(results.get("processing_stats"), dict) else {}
        sec = self._as_float(processing_stats.get("processing_time_seconds"))
        if sec and sec > 0:
            return sec * 1000.0
        if task.started_at and task.completed_at:
            return (task.completed_at - task.started_at).total_seconds() * 1000.0
        return 0.0

    def _build_doc_summary(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        n_total = len(rows)
        success_rows = [r for r in rows if r.get("success")]
        n_success = len(success_rows)
        n_fail = n_total - n_success

        total_values = [float(r.get("total_ms") or 0.0) for r in success_rows]
        ocr_values = [float(r["stage_ms"].get("ocr", 0.0)) for r in success_rows]
        chunk_values = [float(r["stage_ms"].get("chunk", 0.0)) for r in success_rows]
        embed_values = [float(r["stage_ms"].get("embed", 0.0)) for r in success_rows]
        vector_values = [float(r["stage_ms"].get("vector_write", 0.0)) for r in success_rows]
        db_values = [float(r["stage_ms"].get("db_write", 0.0)) for r in success_rows]
        docs_per_min_values = [float(r.get("docs_per_min") or 0.0) for r in success_rows]

        return {
            "n_total": n_total,
            "n_success": n_success,
            "n_fail": n_fail,
            "total_ms_p50": self._fmt(self._percentile(total_values, 50)),
            "total_ms_p95": self._fmt(self._percentile(total_values, 95)),
            "ocr_ms_p50": self._fmt(self._percentile(ocr_values, 50)),
            "ocr_ms_p95": self._fmt(self._percentile(ocr_values, 95)),
            "chunk_ms_p50": self._fmt(self._percentile(chunk_values, 50)),
            "chunk_ms_p95": self._fmt(self._percentile(chunk_values, 95)),
            "embed_ms_p50": self._fmt(self._percentile(embed_values, 50)),
            "embed_ms_p95": self._fmt(self._percentile(embed_values, 95)),
            "vector_write_ms_p50": self._fmt(self._percentile(vector_values, 50)),
            "vector_write_ms_p95": self._fmt(self._percentile(vector_values, 95)),
            "db_write_ms_p50": self._fmt(self._percentile(db_values, 50)),
            "db_write_ms_p95": self._fmt(self._percentile(db_values, 95)),
            "docs_per_min_avg": self._fmt(float(np.mean(docs_per_min_values)) if docs_per_min_values else None),
        }

    def _build_task_summary(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        n_total = len(rows)
        success_rows = [r for r in rows if r.get("success")]
        n_success = len(success_rows)
        n_fail = n_total - n_success
        total_values = [float(r.get("total_ms") or 0.0) for r in success_rows]
        dpm_values = [float(r.get("docs_per_min") or 0.0) for r in success_rows]
        return {
            "n_total": n_total,
            "n_success": n_success,
            "n_fail": n_fail,
            "total_ms_p50": self._fmt(self._percentile(total_values, 50)),
            "total_ms_p95": self._fmt(self._percentile(total_values, 95)),
            "docs_per_min_avg": self._fmt(float(np.mean(dpm_values)) if dpm_values else None),
        }

    def _write_doc_summary(self, path: Path, row: Dict[str, Any]) -> None:
        fieldnames = [
            "n_total",
            "n_success",
            "n_fail",
            "total_ms_p50",
            "total_ms_p95",
            "ocr_ms_p50",
            "ocr_ms_p95",
            "chunk_ms_p50",
            "chunk_ms_p95",
            "embed_ms_p50",
            "embed_ms_p95",
            "vector_write_ms_p50",
            "vector_write_ms_p95",
            "db_write_ms_p50",
            "db_write_ms_p95",
            "docs_per_min_avg",
        ]
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row)

    def _write_task_summary(self, path: Path, row: Dict[str, Any]) -> None:
        fieldnames = [
            "n_total",
            "n_success",
            "n_fail",
            "total_ms_p50",
            "total_ms_p95",
            "docs_per_min_avg",
        ]
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(row)

    def _append_jsonl(self, path: Path, row: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _percentile(self, values: List[float], q: float) -> Optional[float]:
        if not values:
            return None
        return float(np.percentile(np.asarray(values, dtype=float), q, method="linear"))

    def _fmt(self, value: Optional[float]) -> str:
        if value is None:
            return ""
        return f"{value:.3f}"

    def _as_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
