import json
import time
import uuid
from contextlib import ExitStack
from typing import Any, Dict, List, Optional, Set
from unittest.mock import patch

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from meteorite_search.models import DataExtractionTask, Meteorite
from meteorite_search.review_models import PendingMeteorite
from pdf_processor.batch_extraction_service import BatchExtractionService
from pdf_processor.models import PDFDocument
from pdf_processor.rag_meteorite_extractor import RAGMeteoriteExtractor


class Command(BaseCommand):
    help = "Profile batch extraction timing and duplicate-work characteristics."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=5)
        parser.add_argument("--document-limit", type=int, default=5)
        parser.add_argument("--max-batches", type=int, default=1)
        parser.add_argument("--query-limit", type=int, default=5)
        parser.add_argument(
            "--queries",
            type=str,
            default="",
            help="Comma-separated queries. If omitted, use the first N default batch queries.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Optional path to save the JSON profile report.",
        )
        parser.add_argument(
            "--doc-sample-limit",
            type=int,
            default=20,
            help="Maximum number of document-level samples to keep.",
        )

    def handle(self, *args, **options):
        batch_size = int(options["batch_size"])
        document_limit = int(options["document_limit"])
        max_batches = int(options["max_batches"])
        query_limit = int(options["query_limit"])
        output_path = options["output"] or ""
        doc_sample_limit = int(options["doc_sample_limit"])

        if batch_size <= 0:
            raise CommandError("batch-size must be > 0")
        if document_limit <= 0:
            raise CommandError("document-limit must be > 0")
        if max_batches <= 0:
            raise CommandError("max-batches must be > 0")
        if query_limit <= 0:
            raise CommandError("query-limit must be > 0")

        service = BatchExtractionService()
        query_arg = (options.get("queries") or "").strip()
        if query_arg:
            search_queries = [q.strip() for q in query_arg.split(",") if q.strip()]
        else:
            search_queries = service.get_comprehensive_search_terms()[:query_limit]

        if not search_queries:
            raise CommandError("No search queries selected for profiling")

        target_docs = min(document_limit, batch_size * max_batches)
        subset_ids = list(
            PDFDocument.objects.order_by("id").values_list("id", flat=True)[:target_docs]  # type: ignore
        )
        if not subset_ids:
            raise CommandError("No PDFDocument rows available for profiling")

        task_id = str(uuid.uuid4())
        task = DataExtractionTask.objects.create(  # type: ignore
            task_id=task_id,
            task_type="batch_by_docs",
            status="pending",
            total_documents=0,
            processed_documents=0,
            successful_extractions=0,
            failed_extractions=0,
            parameters={
                "search_config": {
                    "batch_size": batch_size,
                    "search_queries": search_queries,
                },
                "profile_mode": True,
            },
            created_at=timezone.now(),
        )

        original_all = PDFDocument.objects.all
        original_sleep = time.sleep
        original_update = BatchExtractionService.update_task_progress
        original_log_progress = BatchExtractionService.log_progress
        original_batch = BatchExtractionService.extract_from_document_batch
        original_execute = BatchExtractionService.execute_batch_extraction
        original_search = RAGMeteoriteExtractor._search_meteorite_segments_optimized
        original_extract_segment = RAGMeteoriteExtractor.extract_from_segment
        original_extract_existing = RAGMeteoriteExtractor.extract_from_existing_documents

        profile: Dict[str, Any] = {
            "task_id": task_id,
            "selected_document_ids": subset_ids,
            "selected_documents_count": len(subset_ids),
            "batch_size": batch_size,
            "max_batches": max_batches,
            "search_queries": search_queries,
            "search_query_count": len(search_queries),
            "task": {},
            "batches": [],
            "queries": [],
            "doc_samples": [],
            "timing_totals_ms": {
                "execute_ms": 0.0,
                "search_ms": 0.0,
                "candidate_collect_ms": 0.0,
                "extract_ms": 0.0,
                "orm_write_ms": 0.0,
                "weaviate_write_ms": 0.0,
                "progress_update_ms": 0.0,
                "query_sleep_ms": 0.0,
                "batch_sleep_ms": 0.0,
            },
            "call_counts": {
                "progress_updates": 0,
                "submit_for_review_calls": 0,
                "weaviate_write_calls": 0,
            },
            "notes": [],
        }

        state: Dict[str, Any] = {
            "batch_index": None,
            "batch_input_doc_ids": [],
            "batch_query_positions": {},
            "current_query": None,
            "seen_processed_docs": set(),
            "seen_retrieved_docs": set(),
            "current_query_doc_ms": 0.0,
            "current_query_doc_count": 0,
            "query_counter": 0,
        }

        initial_meteorite_count = Meteorite.objects.count()  # type: ignore
        initial_pending_count = PendingMeteorite.objects.count()  # type: ignore
        task_start = time.perf_counter()

        def limited_all():
            return original_all().filter(id__in=subset_ids)

        def timed_update(self, task_id_arg: str, **kwargs):
            started = time.perf_counter()
            try:
                return original_update(self, task_id_arg, **kwargs)
            finally:
                elapsed = (time.perf_counter() - started) * 1000.0
                profile["timing_totals_ms"]["progress_update_ms"] += elapsed
                profile["call_counts"]["progress_updates"] += 1

        def profiled_sleep(seconds: float):
            started = time.perf_counter()
            original_sleep(seconds)
            elapsed = (time.perf_counter() - started) * 1000.0
            if seconds >= 2.5:
                profile["timing_totals_ms"]["batch_sleep_ms"] += elapsed
            else:
                profile["timing_totals_ms"]["query_sleep_ms"] += elapsed

        def quiet_log_progress(self, task_id_arg: str, message: str):
            self.extraction_log.append(f"[profile] {message}")

        def timed_search(
            self,
            query: str,
            max_segments: int = 1000,
            allowed_document_ids=None,
        ):
            current_query = state.get("current_query")
            started = time.perf_counter()
            segments = original_search(
                self,
                query,
                max_segments,
                allowed_document_ids=allowed_document_ids,
            )
            elapsed = (time.perf_counter() - started) * 1000.0
            unique_doc_ids = []
            seen_local: Set[str] = set()
            for segment in segments:
                doc_id = str(segment.get("document_id", "") or "")
                if doc_id and doc_id not in seen_local:
                    seen_local.add(doc_id)
                    unique_doc_ids.append(doc_id)
            candidate_started = time.perf_counter()
            _ = len(unique_doc_ids)
            candidate_collect_ms = (time.perf_counter() - candidate_started) * 1000.0

            profile["timing_totals_ms"]["search_ms"] += elapsed
            profile["timing_totals_ms"]["candidate_collect_ms"] += candidate_collect_ms
            if current_query is not None:
                current_query["search_ms"] = elapsed
                current_query["candidate_collect_ms"] = candidate_collect_ms
                current_query["retrieved_segments_count"] = len(segments)
                current_query["retrieved_doc_ids"] = unique_doc_ids
                current_query["retrieved_docs_count"] = len(unique_doc_ids)
                current_query["intra_query_duplicate_docs_count"] = max(0, len(segments) - len(unique_doc_ids))
            return segments

        def timed_extract_segment(self, segment: Dict[str, Any], extraction_options: Dict[str, Any]):
            started = time.perf_counter()
            result = original_extract_segment(self, segment, extraction_options)
            elapsed = (time.perf_counter() - started) * 1000.0
            profile["timing_totals_ms"]["extract_ms"] += elapsed

            current_query = state.get("current_query")
            if current_query is not None:
                state["current_query_doc_ms"] += elapsed
                state["current_query_doc_count"] += 1
                if len(profile["doc_samples"]) < doc_sample_limit:
                    profile["doc_samples"].append(
                        {
                            "batch_index": current_query["batch_index"],
                            "query_text": current_query["query_text"],
                            "document_id": segment.get("document_id", ""),
                            "file_name": segment.get("title", ""),
                            "doc_extract_ms": elapsed,
                            "doc_records_count": 1 if result.get("success") else 0,
                            "doc_write_ms": 0.0,
                            "success": bool(result.get("success")),
                        }
                    )
            return result

        def timed_extract_existing(
            self,
            search_query: str,
            max_documents: int = 100,
            preview_only: bool = False,
            allowed_document_ids=None,
            extraction_attempt_cache=None,
            max_failed_attempts_per_document: int = 3,
        ):
            query_record: Dict[str, Any] = {
                "query_index": state["query_counter"],
                "batch_index": state["batch_index"],
                "query_text": search_query,
                "requested_max_documents": max_documents,
                "preview_only": preview_only,
                "allowed_document_ids_count": len(list(allowed_document_ids or [])),
                "search_ms": 0.0,
                "candidate_collect_ms": 0.0,
                "extract_ms": 0.0,
                "orm_write_ms": 0.0,
                "weaviate_write_ms": 0.0,
                "progress_update_ms": 0.0,
                "retrieved_segments_count": 0,
                "retrieved_docs_count": 0,
                "retrieved_doc_ids": [],
                "processed_unique_docs_count": 0,
                "processed_doc_ids": [],
                "duplicate_docs_count": 0,
                "unique_new_docs_count": 0,
                "batch_input_overlap_count": 0,
                "outside_batch_doc_count": 0,
                "extracted_records_count": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
                "doc_extract_count": 0,
                "would_skip_attempts": 0,
                "would_skip_successes": 0,
                "duplicate_signature_skips": 0,
                "dominance_subset_skips": 0,
                "failed_attempt_budget_skips": 0,
            }
            state["query_counter"] += 1
            state["current_query"] = query_record
            state["current_query_doc_ms"] = 0.0
            state["current_query_doc_count"] = 0

            started = time.perf_counter()
            try:
                result = original_extract_existing(
                    self,
                    search_query,
                    max_documents,
                    preview_only,
                    allowed_document_ids,
                    extraction_attempt_cache,
                    max_failed_attempts_per_document,
                )
            finally:
                elapsed = (time.perf_counter() - started) * 1000.0
                query_record["query_ms"] = elapsed
                query_record["extract_ms"] = state["current_query_doc_ms"]
                query_record["doc_extract_count"] = state["current_query_doc_count"]
                results = result.get("results", []) if isinstance(result, dict) else []
                successful = [item for item in results if item.get("success")]
                processed_doc_ids = []
                seen_local: Set[str] = set()
                for item in results:
                    doc_id = str(item.get("document_id", "") or "")
                    if doc_id and doc_id not in seen_local:
                        seen_local.add(doc_id)
                        processed_doc_ids.append(doc_id)
                processed_doc_set = set(processed_doc_ids)
                seen_processed_docs: Set[str] = state["seen_processed_docs"]
                seen_retrieved_docs: Set[str] = state["seen_retrieved_docs"]
                retrieved_doc_ids = query_record.get("retrieved_doc_ids", [])
                retrieved_doc_set = set(retrieved_doc_ids)
                batch_input_ids = set(state.get("batch_input_doc_ids") or [])

                query_record["processed_doc_ids"] = processed_doc_ids
                query_record["processed_unique_docs_count"] = len(processed_doc_ids)
                query_record["successful_extractions"] = len(successful)
                query_record["failed_extractions"] = max(0, len(results) - len(successful))
                query_record["extracted_records_count"] = len(successful)
                query_record["would_skip_attempts"] = sum(
                    1 for item in results if item.get("would_skip_reason") == "high_overlap_low_novelty"
                )
                query_record["would_skip_successes"] = sum(
                    1
                    for item in results
                    if item.get("would_skip_reason") == "high_overlap_low_novelty" and item.get("success")
                )
                query_record["duplicate_signature_skips"] = sum(
                    1 for item in results if item.get("skip_reason") == "duplicate_signature"
                )
                query_record["dominance_subset_skips"] = sum(
                    1 for item in results if item.get("skip_reason") == "dominance_subset"
                )
                query_record["failed_attempt_budget_skips"] = sum(
                    1 for item in results if item.get("skip_reason") == "failed_attempt_budget"
                )
                query_record["duplicate_docs_count"] = len(retrieved_doc_set & seen_retrieved_docs)
                query_record["unique_new_docs_count"] = len(retrieved_doc_set - seen_retrieved_docs)
                query_record["batch_input_overlap_count"] = len(retrieved_doc_set & batch_input_ids)
                query_record["outside_batch_doc_count"] = len(retrieved_doc_set - batch_input_ids)
                query_record["per_document_ms_avg"] = (
                    query_record["extract_ms"] / query_record["doc_extract_count"]
                    if query_record["doc_extract_count"]
                    else 0.0
                )

                seen_processed_docs.update(processed_doc_set)
                seen_retrieved_docs.update(retrieved_doc_set)
                profile["queries"].append(query_record)
                profile["timing_totals_ms"]["orm_write_ms"] += float(query_record["orm_write_ms"])
                profile["timing_totals_ms"]["weaviate_write_ms"] += float(query_record["weaviate_write_ms"])
                state["current_query"] = None
            return result

        def timed_extract_batch(
            self,
            task_id_arg: str,
            documents: List[PDFDocument],
            search_queries_arg: List[str],
            *,
            batch_num: int = 0,
            total_batches: int = 0,
            total_docs: int = 0,
            processed_before_batch: int = 0,
            successful_before_batch: int = 0,
            failed_before_batch: int = 0,
        ):
            batch_record: Dict[str, Any] = {
                "batch_index": batch_num,
                "batch_docs_input": len(documents),
                "batch_input_doc_ids": [str(doc.id) for doc in documents],
                "batch_queries_count": len(search_queries_arg),
                "batch_docs_unique": 0,
                "batch_records_written": 0,
            }
            state["batch_index"] = batch_num
            state["batch_input_doc_ids"] = batch_record["batch_input_doc_ids"]
            batch_start_query_pos = len(profile["queries"])
            started = time.perf_counter()
            extracted = original_batch(
                self,
                task_id_arg,
                documents,
                search_queries_arg,
                batch_num=batch_num,
                total_batches=total_batches,
                total_docs=total_docs,
                processed_before_batch=processed_before_batch,
                successful_before_batch=successful_before_batch,
                failed_before_batch=failed_before_batch,
            )
            batch_record["batch_ms"] = (time.perf_counter() - started) * 1000.0
            batch_queries = profile["queries"][batch_start_query_pos:]
            batch_unique_doc_ids: Set[str] = set()
            batch_retrieved_doc_ids: Set[str] = set()
            for query_record in batch_queries:
                batch_unique_doc_ids.update(query_record.get("processed_doc_ids", []))
                batch_retrieved_doc_ids.update(query_record.get("retrieved_doc_ids", []))
            batch_record["batch_docs_unique"] = len(batch_unique_doc_ids)
            batch_record["batch_retrieved_unique_docs"] = len(batch_retrieved_doc_ids)
            batch_record["batch_records_written"] = 0
            batch_record["batch_extracted_records"] = sum(
                int(query_record.get("extracted_records_count", 0))
                for query_record in batch_queries
            )
            batch_record["query_indices"] = [query_record["query_index"] for query_record in batch_queries]
            profile["batches"].append(batch_record)
            return extracted

        def timed_execute(
            self,
            task_id_arg: Optional[str] = None,
            batch_size_arg: Optional[int] = None,
            search_queries_arg: Optional[List[str]] = None,
            extraction_options: Optional[Dict[str, Any]] = None,
            resume: bool = False,
            stop_event=None,
            **kwargs,
        ):
            if task_id_arg is None:
                task_id_arg = kwargs.pop("task_id")
            if batch_size_arg is None:
                batch_size_arg = kwargs.pop("batch_size")
            if search_queries_arg is None:
                search_queries_arg = kwargs.pop("search_queries")
            if extraction_options is None:
                extraction_options = kwargs.pop("extraction_options", {})
            if "resume" in kwargs:
                resume = kwargs.pop("resume")
            if "stop_event" in kwargs:
                stop_event = kwargs.pop("stop_event")
            started = time.perf_counter()
            try:
                return original_execute(
                    self,
                    task_id_arg,
                    batch_size_arg,
                    search_queries_arg,
                    extraction_options,
                    resume=resume,
                    stop_event=stop_event,
                )
            finally:
                profile["timing_totals_ms"]["execute_ms"] = (time.perf_counter() - started) * 1000.0

        with ExitStack() as stack:
            stack.enter_context(patch.object(PDFDocument.objects, "all", new=limited_all))
            stack.enter_context(patch("pdf_processor.batch_extraction_service.time.sleep", new=profiled_sleep))
            stack.enter_context(patch.object(BatchExtractionService, "update_task_progress", new=timed_update))
            stack.enter_context(patch.object(BatchExtractionService, "log_progress", new=quiet_log_progress))
            stack.enter_context(patch.object(BatchExtractionService, "extract_from_document_batch", new=timed_extract_batch))
            stack.enter_context(patch.object(BatchExtractionService, "execute_batch_extraction", new=timed_execute))
            stack.enter_context(patch.object(RAGMeteoriteExtractor, "_search_meteorite_segments_optimized", new=timed_search))
            stack.enter_context(patch.object(RAGMeteoriteExtractor, "extract_from_segment", new=timed_extract_segment))
            stack.enter_context(patch.object(RAGMeteoriteExtractor, "extract_from_existing_documents", new=timed_extract_existing))

            completed = service.execute_batch_extraction(
                task_id=task_id,
                batch_size=batch_size,
                search_queries=search_queries,
                extraction_options={},
                resume=False,
                stop_event=None,
            )

        task_elapsed_ms = (time.perf_counter() - task_start) * 1000.0
        task.refresh_from_db()
        final_meteorite_count = Meteorite.objects.count()  # type: ignore
        final_pending_count = PendingMeteorite.objects.count()  # type: ignore

        profile["task"] = {
            "completed": bool(completed),
            "status": task.status,
            "total_ms": task_elapsed_ms,
            "total_batches": len(profile["batches"]),
            "total_queries": len(profile["queries"]),
            "total_documents_target": len(subset_ids),
            "total_documents_processed": task.processed_documents,
            "total_records_written": final_meteorite_count - initial_meteorite_count,
            "meteorite_count_before": initial_meteorite_count,
            "meteorite_count_after": final_meteorite_count,
            "pending_count_before": initial_pending_count,
            "pending_count_after": final_pending_count,
            "results_latest_progress": (task.results or {}).get("latest_progress", {}),
        }

        profile["query_summary"] = {
            "avg_query_ms": self._avg([item["query_ms"] for item in profile["queries"]]),
            "avg_search_ms": self._avg([item["search_ms"] for item in profile["queries"]]),
            "avg_extract_ms": self._avg([item["extract_ms"] for item in profile["queries"]]),
            "avg_processed_unique_docs": self._avg(
                [item["processed_unique_docs_count"] for item in profile["queries"]]
            ),
            "avg_retrieved_docs": self._avg([item["retrieved_docs_count"] for item in profile["queries"]]),
            "avg_duplicate_docs": self._avg([item["duplicate_docs_count"] for item in profile["queries"]]),
            "avg_unique_new_docs": self._avg([item["unique_new_docs_count"] for item in profile["queries"]]),
        }
        profile["doc_summary"] = {
            "avg_doc_extract_ms": self._avg([item["doc_extract_ms"] for item in profile["doc_samples"]]),
            "sample_count": len(profile["doc_samples"]),
        }
        profile["batch_summary"] = {
            "avg_batch_ms": self._avg([item["batch_ms"] for item in profile["batches"]]),
            "avg_batch_retrieved_unique_docs": self._avg(
                [item["batch_retrieved_unique_docs"] for item in profile["batches"]]
            ),
            "avg_batch_extracted_records": self._avg(
                [item["batch_extracted_records"] for item in profile["batches"]]
            ),
        }

        if output_path:
            with open(output_path, "w", encoding="utf-8") as handle:
                json.dump(profile, handle, ensure_ascii=False, indent=2, default=str)

        self.stdout.write(json.dumps(profile, ensure_ascii=False, indent=2, default=str))

    @staticmethod
    def _avg(values: List[Any]) -> float:
        nums = [float(value) for value in values if value is not None]
        if not nums:
            return 0.0
        return sum(nums) / len(nums)
