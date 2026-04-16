"""RAG Meteorite Extractor shim bridging to full RAG pipeline with hybrid search and reranking."""

import hashlib
import json
import logging
from typing import Any, Dict, Iterable, List, Optional, Set

import requests

from .full_rag_service import full_rag_service

logger = logging.getLogger(__name__)


class RAGMeteoriteExtractor:
    SHADOW_HIGH_OVERLAP_MIN_OVERLAP_COUNT = 4
    SHADOW_HIGH_OVERLAP_MIN_RATIO_VS_CURRENT = 0.8
    SHADOW_HIGH_OVERLAP_MIN_RATIO_VS_REFERENCE = 0.8
    SHADOW_HIGH_OVERLAP_MAX_NOVEL_CHUNKS = 1
    SHADOW_HIGH_OVERLAP_MAX_NOVEL_RATIO = 0.25

    def __init__(self) -> None:
        self.rag_service = None

    def _normalize_allowed_document_ids(
        self,
        allowed_document_ids: Optional[Iterable[Any]],
    ) -> Optional[Set[str]]:
        if allowed_document_ids is None:
            return None
        normalized = {str(doc_id) for doc_id in allowed_document_ids if doc_id not in (None, "")}
        return normalized or set()

    def _enhance_meteorite_query(self, query: str) -> str:
        """
        Keep the original query to avoid forcing unrelated queries toward the same results.
        """
        return query

    def initialize_services(self) -> bool:
        try:
            if not full_rag_service._is_initialized:
                full_rag_service.initialize()
            self.rag_service = full_rag_service
            return True
        except Exception as e:
            logger.error("RAGMeteoriteExtractor init failed: %s", e)
            return False

    def _search_meteorite_segments_optimized(
        self,
        query: str,
        max_segments: int = 1000,
        allowed_document_ids: Optional[Iterable[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search segments related to meteorites; returns list of dicts."""
        if not self.rag_service and not self.initialize_services():
            return []

        enhanced_query = self._enhance_meteorite_query(query)
        logger.info(
            "[single-task] full search (with rerank) original='%s' enhanced='%s' limit=%s",
            query[:60],
            enhanced_query[:100],
            max_segments,
        )

        if self.rag_service is None:
            logger.error("RAG service is not initialized")
            return []

        allowed_document_id_set = self._normalize_allowed_document_ids(allowed_document_ids)
        effective_max_segments = max(1, int(max_segments))
        if allowed_document_id_set is not None:
            if not allowed_document_id_set:
                return []
            effective_max_segments = min(effective_max_segments, len(allowed_document_id_set))

        results = self.rag_service.search(
            query=enhanced_query,
            limit=effective_max_segments,
            use_hybrid=True,
            use_rerank=True,
            allowed_document_ids=allowed_document_ids,
        )
        logger.info("[single-task] raw candidates fetched=%s", len(results))
        if allowed_document_id_set is not None:
            results = [
                result
                for result in results
                if str(getattr(result, "document_id", "") or "") in allowed_document_id_set
            ]
            logger.info(
                "[single-task] batch-scope filtered candidates=%s allowed_docs=%s",
                len(results),
                len(allowed_document_id_set),
            )

        segments: List[Dict[str, Any]] = []
        for result in results:
            segments.append(
                {
                    "content": result.content,
                    "score": float(getattr(result, "score", 0.0) or 0.0),
                    "document_id": getattr(result, "document_id", ""),
                    "title": getattr(result, "title", ""),
                    "chunk_index": getattr(result, "chunk_index", 0),
                    "source": "weaviate",
                }
            )

        logger.info("[single-task] converted segments=%s", len(segments))
        return segments

    def _combine_document_contents(
        self,
        contents: List[str],
        *,
        max_segments: int = 3,
        max_chars: int = 12000,
    ) -> str:
        combined_parts: List[str] = []
        current_length = 0

        for content in contents[:max_segments]:
            text = str(content or "").strip()
            if not text:
                continue

            next_length = current_length + len(text)
            if combined_parts:
                next_length += len("\n\n---\n\n")

            if next_length > max_chars:
                remaining = max_chars - current_length
                if combined_parts:
                    remaining -= len("\n\n---\n\n")
                if remaining > 100:
                    combined_parts.append(text[:remaining] + "...")
                break

            combined_parts.append(text)
            current_length = next_length

        return "\n\n---\n\n".join(combined_parts)

    def _aggregate_segments_by_document(
        self,
        segments: List[Dict[str, Any]],
        max_documents: int,
    ) -> List[Dict[str, Any]]:
        aggregated_by_document: Dict[str, Dict[str, Any]] = {}
        ordered_document_keys: List[str] = []

        for index, segment in enumerate(segments):
            document_id = str(segment.get("document_id", "") or "")
            document_key = document_id or f"__segment_{index}"
            chunk_index = int(segment.get("chunk_index", 0) or 0)
            score = float(segment.get("score", 0.0) or 0.0)
            content = str(segment.get("content", "") or "").strip()

            entry = aggregated_by_document.get(document_key)
            if entry is None:
                entry = {
                    "document_id": document_id,
                    "title": segment.get("title", ""),
                    "score": score,
                    "chunk_index": chunk_index,
                    "source": segment.get("source", "weaviate"),
                    "chunk_indices": [],
                    "matched_segment_count": 0,
                    "_contents": [],
                    "_seen_contents": set(),
                }
                aggregated_by_document[document_key] = entry
                ordered_document_keys.append(document_key)

            entry["matched_segment_count"] += 1
            if chunk_index not in entry["chunk_indices"]:
                entry["chunk_indices"].append(chunk_index)
            if score > entry["score"]:
                entry["score"] = score
                entry["chunk_index"] = chunk_index
            if content and content not in entry["_seen_contents"]:
                entry["_seen_contents"].add(content)
                entry["_contents"].append(content)

        document_candidates: List[Dict[str, Any]] = []
        for document_key in ordered_document_keys[:max_documents]:
            entry = aggregated_by_document[document_key]
            combined_content = self._combine_document_contents(entry["_contents"])
            document_candidates.append(
                {
                    "document_id": entry["document_id"],
                    "title": entry["title"],
                    "score": entry["score"],
                    "chunk_index": entry["chunk_index"],
                    "chunk_indices": sorted(entry["chunk_indices"]),
                    "matched_segment_count": entry["matched_segment_count"],
                    "content": combined_content,
                    "full_content": combined_content,
                    "source": entry["source"],
                }
            )

        return document_candidates

    def _build_document_attempt_signature(self, document_candidate: Dict[str, Any]) -> str:
        chunk_indices = self._normalize_candidate_chunk_indices(document_candidate)
        matched_segment_count = int(
            document_candidate.get("matched_segment_count", len(chunk_indices) or 0) or 0
        )

        if chunk_indices:
            chunk_signature = ",".join(str(chunk_index) for chunk_index in chunk_indices)
        else:
            content = str(
                document_candidate.get("content")
                or document_candidate.get("full_content")
                or ""
            )
            chunk_signature = hashlib.sha1(content[:1000].encode("utf-8")).hexdigest()[:16] if content else "empty"

        return f"chunks={chunk_signature}|matched={matched_segment_count}"

    def _normalize_candidate_chunk_indices(self, document_candidate: Dict[str, Any]) -> List[int]:
        chunk_indices: List[int] = []
        for raw_chunk_index in document_candidate.get("chunk_indices", []) or []:
            try:
                chunk_indices.append(int(raw_chunk_index))
            except (TypeError, ValueError):
                continue

        return sorted(set(chunk_indices))

    def _get_attempt_state(
        self,
        extraction_attempt_cache: Optional[Dict[str, Dict[str, Any]]],
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        if extraction_attempt_cache is None or not document_id:
            return None

        attempt_state = extraction_attempt_cache.setdefault(
            document_id,
            {
                "attempted_signatures": set(),
                "attempted_contexts": [],
                "failed_attempts": 0,
            },
        )

        attempted_signatures = attempt_state.get("attempted_signatures")
        if not isinstance(attempted_signatures, set):
            attempted_signatures = {
                str(signature)
                for signature in (attempted_signatures or [])
                if signature not in (None, "")
            }
            attempt_state["attempted_signatures"] = attempted_signatures

        attempted_contexts = attempt_state.get("attempted_contexts")
        if not isinstance(attempted_contexts, list):
            attempted_contexts = []
            attempt_state["attempted_contexts"] = attempted_contexts

        try:
            attempt_state["failed_attempts"] = int(attempt_state.get("failed_attempts", 0) or 0)
        except (TypeError, ValueError):
            attempt_state["failed_attempts"] = 0

        return attempt_state

    def _evaluate_attempt_context_gate(
        self,
        attempt_state: Dict[str, Any],
        attempt_signature: str,
        chunk_indices: List[int],
    ) -> Optional[Dict[str, str]]:
        attempted_signatures = attempt_state["attempted_signatures"]
        if attempt_signature in attempted_signatures:
            return {
                "skip_reason": "duplicate_signature",
                "reference_signature": attempt_signature,
            }

        if not chunk_indices:
            return None

        candidate_chunk_set = set(chunk_indices)
        for context in attempt_state.get("attempted_contexts", []):
            prior_signature = str(context.get("signature", "") or "")
            prior_chunk_set = context.get("chunk_index_set")
            if not isinstance(prior_chunk_set, set):
                prior_chunk_set = {
                    int(chunk_index)
                    for chunk_index in context.get("chunk_indices", [])
                    if isinstance(chunk_index, int)
                }
                context["chunk_index_set"] = prior_chunk_set

            if candidate_chunk_set and candidate_chunk_set < prior_chunk_set:
                return {
                    "skip_reason": "dominance_subset",
                    "reference_signature": prior_signature,
                }

        return None

    def _record_attempt_context(
        self,
        attempt_state: Dict[str, Any],
        attempt_signature: str,
        chunk_indices: List[int],
        matched_segment_count: int,
    ) -> None:
        attempted_contexts = attempt_state.get("attempted_contexts")
        if not isinstance(attempted_contexts, list):
            attempted_contexts = []
            attempt_state["attempted_contexts"] = attempted_contexts

        attempted_contexts.append(
            {
                "signature": attempt_signature,
                "chunk_indices": list(chunk_indices),
                "chunk_index_set": set(chunk_indices),
                "matched_segment_count": matched_segment_count,
            }
        )

    def _evaluate_shadow_high_overlap_observation(
        self,
        attempt_state: Dict[str, Any],
        attempt_signature: str,
        chunk_indices: List[int],
    ) -> Optional[Dict[str, Any]]:
        if not chunk_indices:
            return None

        candidate_chunk_set = set(chunk_indices)
        if not candidate_chunk_set:
            return None

        best_match: Optional[Dict[str, Any]] = None
        for context in attempt_state.get("attempted_contexts", []):
            prior_signature = str(context.get("signature", "") or "")
            if not prior_signature or prior_signature == attempt_signature:
                continue

            prior_chunk_set = context.get("chunk_index_set")
            if not isinstance(prior_chunk_set, set):
                prior_chunk_set = {
                    int(chunk_index)
                    for chunk_index in context.get("chunk_indices", [])
                    if isinstance(chunk_index, int)
                }
                context["chunk_index_set"] = prior_chunk_set

            if not prior_chunk_set:
                continue

            overlap_count = len(candidate_chunk_set & prior_chunk_set)
            if overlap_count <= 0:
                continue

            if candidate_chunk_set < prior_chunk_set:
                continue

            overlap_ratio_vs_current = overlap_count / len(candidate_chunk_set)
            overlap_ratio_vs_reference = overlap_count / len(prior_chunk_set)
            novel_chunk_count = len(candidate_chunk_set - prior_chunk_set)
            novel_chunk_ratio = novel_chunk_count / len(candidate_chunk_set)

            if (
                overlap_count >= self.SHADOW_HIGH_OVERLAP_MIN_OVERLAP_COUNT
                and overlap_ratio_vs_current >= self.SHADOW_HIGH_OVERLAP_MIN_RATIO_VS_CURRENT
                and overlap_ratio_vs_reference >= self.SHADOW_HIGH_OVERLAP_MIN_RATIO_VS_REFERENCE
                and novel_chunk_count <= self.SHADOW_HIGH_OVERLAP_MAX_NOVEL_CHUNKS
                and novel_chunk_ratio <= self.SHADOW_HIGH_OVERLAP_MAX_NOVEL_RATIO
            ):
                candidate_match = {
                    "would_skip_reason": "high_overlap_low_novelty",
                    "reference_signature": prior_signature,
                    "overlap_count": overlap_count,
                    "overlap_ratio_vs_current": round(overlap_ratio_vs_current, 4),
                    "overlap_ratio_vs_reference": round(overlap_ratio_vs_reference, 4),
                    "novel_chunk_count": novel_chunk_count,
                    "novel_chunk_ratio": round(novel_chunk_ratio, 4),
                }
                if best_match is None or (
                    candidate_match["overlap_count"],
                    candidate_match["overlap_ratio_vs_current"],
                ) > (
                    best_match["overlap_count"],
                    best_match["overlap_ratio_vs_current"],
                ):
                    best_match = candidate_match

        return best_match

    def extract_from_segment(self, segment: Dict[str, Any], extraction_options: Dict[str, Any]) -> Dict[str, Any]:
        """Extract meteorite data from a segment; returns standardized dict."""
        content = segment.get("full_content") or segment.get("content", "")
        if not content or len(content.strip()) < 50:
            return {"success": False, "error": "content too short"}

        try:
            from .full_rag_service import full_rag_service as frs

            if not frs._is_initialized:
                frs.initialize()

            data = frs.extract_meteorite_data(content)
            if data:
                return {"success": True, "data": data.__dict__, "confidence": 0.7}
            return {"success": False, "error": "no valid data extracted", "error_type": "no_data"}
        except json.JSONDecodeError as e:
            logger.error("extract_from_segment JSON parse failed: %s", e)
            return {"success": False, "error": f"JSON parse failed: {e}", "error_type": "json_parse"}
        except requests.exceptions.Timeout as e:
            logger.error("extract_from_segment timeout: %s", e)
            return {"success": False, "error": f"request timeout: {e}", "error_type": "timeout"}
        except Exception as e:
            logger.error("extract_from_segment failed: %s", e, exc_info=True)
            return {"success": False, "error": str(e), "error_type": "exception"}

    def extract_from_document(self, document_id: str, extraction_options: Dict[str, Any]) -> Dict[str, Any]:
        """Extract meteorite data from a document by ID; returns standardized dict."""
        try:
            if not self.rag_service and not self.initialize_services():
                return {"success": False, "error": "service initialization failed"}

            from .hybrid_search_service import hybrid_search_service

            search_results = hybrid_search_service.hybrid_search(document_id, 1)
            if not search_results:
                return {"success": False, "error": f"document not found: {document_id}"}

            doc_content = search_results[0].content

            from .full_rag_service import full_rag_service as frs

            if not frs._is_initialized:
                frs.initialize()

            data = frs.extract_meteorite_data(doc_content)
            if data:
                return {"success": True, "data": data.__dict__, "confidence": 0.7}
            return {"success": False, "error": "no valid data extracted"}
        except Exception as e:
            logger.error("extract_from_document failed for document %s: %s", document_id, e, exc_info=True)
            return {"success": False, "error": str(e)}

    def extract_from_existing_documents(
        self,
        search_query: str,
        max_documents: int = 100,
        preview_only: bool = False,
        allowed_document_ids: Optional[Iterable[Any]] = None,
        extraction_attempt_cache: Optional[Dict[str, Dict[str, Any]]] = None,
        max_failed_attempts_per_document: int = 3,
    ) -> Dict[str, Any]:
        """Extract meteorite data from retrieved documents."""
        try:
            if not self.rag_service and not self.initialize_services():
                return {
                    "status": "failed",
                    "error_message": "service initialization failed",
                    "results": [],
                }

            segments = self._search_meteorite_segments_optimized(
                search_query,
                max_documents,
                allowed_document_ids=allowed_document_ids,
            )
            if not segments:
                return {
                    "status": "completed",
                    "error_message": "no relevant documents found",
                    "results": [],
                }

            document_candidates = self._aggregate_segments_by_document(segments, max_documents)
            logger.info(
                "[single-task] document-level aggregation unique_docs=%s raw_segments=%s",
                len(document_candidates),
                len(segments),
            )
            if not document_candidates:
                return {
                    "status": "completed",
                    "error_message": "no document candidates available",
                    "results": [],
                }

            results: List[Dict[str, Any]] = []
            success_count = 0
            skipped_attempts = 0
            shadow_would_skip_attempts = 0
            shadow_would_skip_successes = 0
            for document_candidate in document_candidates:
                if preview_only and success_count >= 5:
                    break

                document_id = str(document_candidate.get("document_id", "") or "")
                candidate_chunk_indices = self._normalize_candidate_chunk_indices(document_candidate)
                matched_segment_count = int(
                    document_candidate.get("matched_segment_count", len(candidate_chunk_indices) or 1) or 1
                )
                attempt_signature = self._build_document_attempt_signature(document_candidate)
                attempt_state = self._get_attempt_state(extraction_attempt_cache, document_id)
                shadow_observation: Optional[Dict[str, Any]] = None
                if attempt_state is not None:
                    context_gate = self._evaluate_attempt_context_gate(
                        attempt_state,
                        attempt_signature,
                        candidate_chunk_indices,
                    )
                    if context_gate is not None:
                        skipped_attempts += 1
                        logger.info(
                            "[single-task] skip extraction attempt doc=%s reason=%s signature=%s reference=%s",
                            document_id,
                            context_gate["skip_reason"],
                            attempt_signature,
                            context_gate["reference_signature"],
                        )
                        results.append(
                            {
                                "document_id": document_id,
                                "title": document_candidate.get("title", ""),
                                "chunk_index": document_candidate.get("chunk_index", 0),
                                "chunk_indices": document_candidate.get("chunk_indices", []),
                                "matched_segment_count": matched_segment_count,
                                "attempt_signature": attempt_signature,
                                "skip_reference_signature": context_gate["reference_signature"],
                                "would_skip_reason": "",
                                "would_skip_reference_signature": "",
                                "shadow_overlap_metrics": {},
                                "attempted": False,
                                "skipped": True,
                                "skip_reason": context_gate["skip_reason"],
                                "success": False,
                                "data": {},
                                "error": "",
                            }
                        )
                        continue

                    failed_attempts = int(attempt_state.get("failed_attempts", 0) or 0)
                    if failed_attempts >= max_failed_attempts_per_document:
                        skipped_attempts += 1
                        logger.info(
                            "[single-task] skip extraction attempt after failed budget doc=%s failed_attempts=%s limit=%s",
                            document_id,
                            failed_attempts,
                            max_failed_attempts_per_document,
                        )
                        results.append(
                            {
                                "document_id": document_id,
                                "title": document_candidate.get("title", ""),
                                "chunk_index": document_candidate.get("chunk_index", 0),
                                "chunk_indices": document_candidate.get("chunk_indices", []),
                                "matched_segment_count": matched_segment_count,
                                "attempt_signature": attempt_signature,
                                "skip_reference_signature": "",
                                "would_skip_reason": "",
                                "would_skip_reference_signature": "",
                                "shadow_overlap_metrics": {},
                                "attempted": False,
                                "skipped": True,
                                "skip_reason": "failed_attempt_budget",
                                "success": False,
                                "data": {},
                                "error": "",
                            }
                        )
                        continue

                    shadow_observation = self._evaluate_shadow_high_overlap_observation(
                        attempt_state,
                        attempt_signature,
                        candidate_chunk_indices,
                    )
                    if shadow_observation is not None:
                        logger.info(
                            "[single-task] shadow would-skip doc=%s reason=%s signature=%s reference=%s overlap=%s novel=%s",
                            document_id,
                            shadow_observation["would_skip_reason"],
                            attempt_signature,
                            shadow_observation["reference_signature"],
                            shadow_observation["overlap_count"],
                            shadow_observation["novel_chunk_count"],
                        )

                    attempt_state["attempted_signatures"].add(attempt_signature)
                    self._record_attempt_context(
                        attempt_state,
                        attempt_signature,
                        candidate_chunk_indices,
                        matched_segment_count,
                    )

                extraction_result = self.extract_from_segment(document_candidate, {})
                if not extraction_result["success"] and attempt_state is not None:
                    attempt_state["failed_attempts"] = int(attempt_state.get("failed_attempts", 0) or 0) + 1
                if shadow_observation is not None:
                    shadow_would_skip_attempts += 1
                    if extraction_result["success"]:
                        shadow_would_skip_successes += 1
                results.append(
                    {
                        "document_id": document_id,
                        "title": document_candidate.get("title", ""),
                        "chunk_index": document_candidate.get("chunk_index", 0),
                        "chunk_indices": document_candidate.get("chunk_indices", []),
                        "matched_segment_count": matched_segment_count,
                        "attempt_signature": attempt_signature,
                        "skip_reference_signature": "",
                        "would_skip_reason": (
                            shadow_observation["would_skip_reason"] if shadow_observation is not None else ""
                        ),
                        "would_skip_reference_signature": (
                            shadow_observation["reference_signature"] if shadow_observation is not None else ""
                        ),
                        "shadow_overlap_metrics": (
                            {
                                "overlap_count": shadow_observation["overlap_count"],
                                "overlap_ratio_vs_current": shadow_observation["overlap_ratio_vs_current"],
                                "overlap_ratio_vs_reference": shadow_observation["overlap_ratio_vs_reference"],
                                "novel_chunk_count": shadow_observation["novel_chunk_count"],
                                "novel_chunk_ratio": shadow_observation["novel_chunk_ratio"],
                            }
                            if shadow_observation is not None
                            else {}
                        ),
                        "attempted": True,
                        "skipped": False,
                        "skip_reason": "",
                        "success": extraction_result["success"],
                        "data": extraction_result.get("data", {}),
                        "error": extraction_result.get("error", "") if not extraction_result["success"] else "",
                    }
                )
                if extraction_result["success"]:
                    success_count += 1

            return {
                "status": "completed" if not preview_only else "preview",
                "results": results,
                "total_processed": len(document_candidates),
                "raw_segments_count": len(segments),
                "unique_documents_found": len(document_candidates),
                "successful_extractions": success_count,
                "skipped_attempts": skipped_attempts,
                "would_skip_attempts": shadow_would_skip_attempts,
                "would_skip_successes": shadow_would_skip_successes,
                "error_message": "" if success_count > 0 else "no valid data extracted",
            }
        except Exception as e:
            logger.error("extract_from_existing_documents failed: %s", e, exc_info=True)
            return {
                "status": "failed",
                "error_message": str(e),
                "results": [],
            }


rag_meteorite_extractor = RAGMeteoriteExtractor()
