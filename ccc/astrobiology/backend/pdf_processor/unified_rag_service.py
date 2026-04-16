"""
Unified RAG service for search, QA, and extraction.
"""
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
import weaviate

from .bench_logging import init_stage_ms, normalize_config
from .confidence_calculator import confidence_calculator
from .document_aggregator import document_aggregator
from .extraction_schema import (
    EXTRACTION_OUTPUT_SCHEMA_JSON,
    ORGANIC_COMPOUNDS_PROMPT_GUIDANCE,
    normalize_extraction_payload,
)
from .hybrid_search_service import hybrid_search_service
from .rag_service import RAGAnswer, SearchResult
from .reranker_service import reranker_service

logger = logging.getLogger(__name__)


@dataclass
class MeteoriteData:
    name: str
    classification: str
    discovery_location: str
    origin: str
    organic_compounds: List[str]
    contamination_exclusion_method: str
    references: List[Dict[str, str]]


class RAGException(Exception):
    def __init__(self, message: str, code: str = "RAG_ERROR", details: Dict[str, Any] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class UnifiedRAGService:
    VALID_RETRIEVAL_MODES = {"bm25", "dense", "hybrid", "hybrid_rerank"}
    DEFAULT_RETRIEVAL_MODE = "hybrid_rerank"
    DEFAULT_HYBRID_ALPHA = 0.7

    def __init__(self, collection_name: Optional[str] = None):
        self.embedding_service = None
        self.weaviate_connection = None
        self._is_initialized = False
        self.collection_name = str(
            collection_name or os.getenv("WEAVIATE_COLLECTION_NAME", "PDFDocument")
        ).strip() or "PDFDocument"
        self.last_stage_ms = init_stage_ms()
        self.last_config = normalize_config(None)

    def _normalize_retrieval_mode(self, mode: Optional[str]) -> str:
        normalized = (mode or "").strip().lower()
        if normalized in self.VALID_RETRIEVAL_MODES:
            return normalized
        if normalized:
            logger.warning("Invalid retrieval mode '%s', fallback to %s", normalized, self.DEFAULT_RETRIEVAL_MODE)
        return self.DEFAULT_RETRIEVAL_MODE

    def _read_int_env(self, name: str, default: int, min_value: int = 1) -> int:
        raw = os.getenv(name, "").strip()
        if not raw:
            return default
        try:
            value = int(raw)
            if value < min_value:
                return default
            return value
        except ValueError:
            return default

    def _read_float_env(self, name: str, default: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
        raw = os.getenv(name, "").strip()
        if not raw:
            return default
        try:
            value = float(raw)
            if value < min_value or value > max_value:
                return default
            return value
        except ValueError:
            return default

    def _read_optional_int_env(self, name: str) -> Optional[int]:
        raw = os.getenv(name, "").strip()
        if not raw:
            return None
        try:
            value = int(raw)
            if value <= 0:
                return None
            return value
        except ValueError:
            return None

    def _resolve_qa_runtime_options(self) -> Dict[str, Any]:
        top_k = self._read_int_env("RAG_TOP_K", default=10, min_value=1)
        mode = self._normalize_retrieval_mode(os.getenv("RAG_RETRIEVAL_MODE", self.DEFAULT_RETRIEVAL_MODE))
        rerank_k_default = top_k * 2
        rerank_k = self._read_int_env("RAG_RERANK_K", default=rerank_k_default, min_value=1)
        hybrid_alpha = self._read_float_env(
            "RAG_HYBRID_ALPHA",
            default=self.DEFAULT_HYBRID_ALPHA,
            min_value=0.0,
            max_value=1.0,
        )
        context_token_limit = self._read_optional_int_env("RAG_CONTEXT_TOKEN_LIMIT")
        return {
            "retrieval_mode": mode,
            "top_k": top_k,
            "rerank_k": rerank_k,
            "hybrid_alpha": hybrid_alpha,
            "context_token_limit": context_token_limit,
        }

    def initialize(self) -> bool:
        try:
            if not self.embedding_service:
                from .embedding_service import embedding_service

                self.embedding_service = embedding_service

            if not self.weaviate_connection:
                from .weaviate_connection import weaviate_connection

                self.weaviate_connection = weaviate_connection

            if not self.embedding_service or not self.embedding_service._model:
                logger.error("Embedding service unavailable")
                return False

            if not self.weaviate_connection.test_connection():
                logger.error("Weaviate connection failed")
                return False

            self._is_initialized = True
            logger.info("Unified RAG service initialized")
            return True
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            return False

    def search(
        self,
        query: str,
        limit: int = 20,
        use_hybrid: bool = True,
        use_rerank: bool = True,
        use_aggregation: bool = False,
        retrieval_mode: Optional[str] = None,
        rerank_k: Optional[int] = None,
        hybrid_alpha: Optional[float] = None,
    ) -> List[SearchResult]:
        if not self._is_initialized:
            raise RAGException("Service not initialized", "SERVICE_NOT_INITIALIZED")

        try:
            logger.info(f"Search start: '{query[:50]}...', limit={limit}")
            self.last_stage_ms = init_stage_ms()
            if retrieval_mode is None:
                if use_hybrid and use_rerank:
                    mode = "hybrid_rerank"
                elif use_hybrid:
                    mode = "hybrid"
                else:
                    mode = "dense"
            else:
                mode = self._normalize_retrieval_mode(retrieval_mode)

            alpha = self.DEFAULT_HYBRID_ALPHA if hybrid_alpha is None else float(hybrid_alpha)
            if alpha < 0.0 or alpha > 1.0:
                alpha = self.DEFAULT_HYBRID_ALPHA
            vector_weight = alpha
            bm25_weight = 1.0 - alpha
            candidate_limit = max(limit * 2, limit, 1)
            effective_rerank_k = rerank_k if rerank_k and rerank_k > 0 else candidate_limit
            actual_mode = mode

            search_results: List[Any]
            if mode == "bm25":
                sparse_start = time.perf_counter()
                search_results = hybrid_search_service._bm25_search(  # type: ignore[attr-defined]
                    query,
                    candidate_limit,
                    collection_name=self.collection_name,
                )
                self.last_stage_ms["sparse_search"] = (time.perf_counter() - sparse_start) * 1000.0
                self.last_stage_ms["dense_search"] = 0.0
                self.last_stage_ms["fuse"] = 0.0
                self.last_stage_ms["rerank"] = 0.0
                effective_rerank_k = 0
            elif mode == "dense":
                dense_start = time.perf_counter()
                search_results = self._fallback_vector_search(query, candidate_limit)
                self.last_stage_ms["dense_search"] = (time.perf_counter() - dense_start) * 1000.0
                self.last_stage_ms["sparse_search"] = 0.0
                self.last_stage_ms["fuse"] = 0.0
                self.last_stage_ms["rerank"] = 0.0
                effective_rerank_k = 0
            else:
                hybrid_results = hybrid_search_service.hybrid_search(
                    query,
                    candidate_limit,
                    vector_weight=vector_weight,
                    bm25_weight=bm25_weight,
                    collection_name=self.collection_name,
                )
                search_results = hybrid_results
                hybrid_stage = getattr(hybrid_search_service, "last_stage_ms", {}) or {}
                self.last_stage_ms["dense_search"] = float(hybrid_stage.get("dense_search", 0.0))
                self.last_stage_ms["sparse_search"] = float(hybrid_stage.get("sparse_search", 0.0))
                self.last_stage_ms["fuse"] = float(hybrid_stage.get("fuse", 0.0))
                self.last_stage_ms["rerank"] = 0.0

                if mode == "hybrid_rerank":
                    if reranker_service.is_available() and search_results:
                        rerank_start = time.perf_counter()
                        reranked_results = reranker_service.rerank_results(
                            query, search_results, effective_rerank_k
                        )
                        self.last_stage_ms["rerank"] = (time.perf_counter() - rerank_start) * 1000.0
                        search_results = reranked_results
                    else:
                        # No rerank executed in this run; reflect actual path.
                        actual_mode = "hybrid"
                        effective_rerank_k = 0
                else:
                    effective_rerank_k = 0

            self.last_config = normalize_config(
                {
                    "retrieval_mode": actual_mode,
                    "top_k": limit,
                    "rerank_k": effective_rerank_k,
                    "hybrid_alpha": alpha if actual_mode in {"hybrid", "hybrid_rerank"} else None,
                    "context_token_limit": self.last_config.get("context_token_limit"),
                }
            )

            if use_aggregation:
                aggregated_results = document_aggregator.aggregate_search_results(search_results, limit)
                final_results = []
                for agg_result in aggregated_results:
                    final_results.append(
                        SearchResult(
                            content=agg_result.content,
                            score=agg_result.relevance_score,
                            metadata=agg_result.metadata,
                            document_id=agg_result.document_id,
                            page=agg_result.page_range[0],
                            title=agg_result.title,
                            chunk_index=-1,
                        )
                    )
                return final_results

            return self._convert_to_search_results(search_results[:limit])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            self.last_stage_ms = init_stage_ms()
            raise RAGException(f"Search failed: {str(e)}", "SEARCH_FAILED")

    def _fallback_vector_search(self, query: str, limit: int) -> List[SearchResult]:
        try:
            query_vector = self.embedding_service.encode([query])[0]
            client = self.weaviate_connection.get_client()
            collection = client.collections.get(self.collection_name)

            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=limit,
                return_metadata=weaviate.classes.query.MetadataQuery(distance=True),
            )

            results = []
            for obj in response.objects:
                content = obj.properties.get("content", "")
                title = obj.properties.get("title", "") or "Unknown document"
                document_id = obj.properties.get("document_id", "")
                page = obj.properties.get("page_number", 0)
                score = 1.0 - (obj.metadata.distance if obj.metadata else 0.0)

                results.append(
                    SearchResult(
                        content=content,
                        score=score,
                        metadata={
                            "document_id": document_id,
                            "page_number": page,
                            "distance": obj.metadata.distance if obj.metadata else None,
                        },
                        document_id=document_id,
                        page=page,
                        title=title,
                        chunk_index=obj.properties.get("chunk_index", -1),
                    )
                )

            return results
        except Exception as e:
            logger.error(f"Fallback vector search failed: {e}")
            return []

    def _convert_to_search_results(self, results: List[Any]) -> List[SearchResult]:
        search_results = []
        for result in results:
            if hasattr(result, "content"):
                score = getattr(result, "final_score", None)
                if score is None:
                    score = getattr(result, "rerank_score", None)
                if score is None:
                    score = getattr(result, "score", 0.0)
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    score = 0.0

                metadata = getattr(result, "metadata", {}) or {}
                metadata_copy = dict(metadata)
                if "final_score" not in metadata_copy and hasattr(result, "final_score"):
                    metadata_copy["final_score"] = float(getattr(result, "final_score"))
                if "rerank_score" not in metadata_copy and hasattr(result, "rerank_score"):
                    metadata_copy["rerank_score"] = float(getattr(result, "rerank_score"))

                search_results.append(
                    SearchResult(
                        content=result.content,
                        score=score,
                        metadata=metadata_copy,
                        document_id=getattr(result, "document_id", ""),
                        page=getattr(result, "page", 0),
                        title=getattr(result, "title", ""),
                        chunk_index=getattr(result, "chunk_index", -1),
                    )
                )
        return search_results

    def search_meteorite_content(self, query: str, limit: int = 100) -> List[SearchResult]:
        enhanced_query = f"{query} meteorite chondrite"
        results = self.search(enhanced_query, limit * 2)

        filtered_results = []
        for result in results:
            if self._is_meteorite_related(result.content):
                filtered_results.append(result)
                if len(filtered_results) >= limit:
                    break
        return filtered_results

    def _is_meteorite_related(self, content: str) -> bool:
        content_lower = content.lower()
        primary_keywords = [
            "meteorite",
            "chondrite",
            "achondrite",
            "carbonaceous chondrite",
            "extraterrestrial material",
        ]
        has_primary = any(keyword in content_lower for keyword in primary_keywords)

        exclude_patterns = [
            "bibliography",
            "reference list",
            "citation",
            "table of contents",
            "index page",
            "acknowledgment",
        ]
        has_exclude = any(pattern in content_lower for pattern in exclude_patterns)
        if len(content.strip()) < 50:
            return False
        return has_primary and not has_exclude

    def extract_meteorite_data(self, content: str) -> Optional[MeteoriteData]:
        try:
            prompt = f"""
            Extract meteorite data from the following text. Return ONLY valid JSON.

            The JSON must match this schema exactly:
            {EXTRACTION_OUTPUT_SCHEMA_JSON}

            Rules:
            - name: actual meteorite name only
            - classification: type/classification
            - discovery_location: location where the meteorite was discovered
            - origin: meteorite origin
            - contamination_exclusion_method: contamination exclusion method
            - references: list of reference objects or []
            - {ORGANIC_COMPOUNDS_PROMPT_GUIDANCE}

            Text:
            {content}

            If a field is absent, use an empty string or [].
            If there is no meteorite-related information in the text, return null.
            """

            response = requests.post(
                "http://localhost:11434/v1/chat/completions",
                json={
                    "model": "llama3.1:8b-instruct-q4_K_M",
                    "messages": [
                        {"role": "system", "content": "You are a professional astrobiology assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.3,
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                answer = result["choices"][0]["message"]["content"]
                try:
                    data = json.loads(answer)
                    if data and data != "null":
                        normalized_data = normalize_extraction_payload(data)
                        if any(
                            normalized_data.get(key)
                            for key in (
                                "name",
                                "classification",
                                "discovery_location",
                                "origin",
                                "organic_compounds",
                                "contamination_exclusion_method",
                            )
                        ):
                            return MeteoriteData(**normalized_data)
                except json.JSONDecodeError:
                    logger.warning("LLM returned invalid JSON")
            return None
        except Exception as e:
            logger.error(f"Data extraction failed: {e}")
            return None

    def ask_question(self, question: str) -> RAGAnswer:
        stage_ms = init_stage_ms()
        total_start = time.perf_counter()
        try:
            runtime_options = self._resolve_qa_runtime_options()
            search_results = self.search(
                question,
                limit=runtime_options["top_k"],
                retrieval_mode=runtime_options["retrieval_mode"],
                rerank_k=runtime_options["rerank_k"],
                hybrid_alpha=runtime_options["hybrid_alpha"],
            )
            self.last_config["context_token_limit"] = runtime_options["context_token_limit"]
            for key in ("sparse_search", "dense_search", "fuse", "rerank"):
                stage_ms[key] = float(self.last_stage_ms.get(key, 0.0))

            if not search_results:
                return RAGAnswer(
                    answer="Sorry, no relevant information found in the database. Please try rephrasing your question or check if the relevant documents are available.",
                    sources=[],
                    confidence=0.0,
                    total_contexts=0,
                )

            context_start = time.perf_counter()
            stop_words = {
                "the",
                "a",
                "an",
                "and",
                "or",
                "but",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "with",
                "by",
                "from",
                "is",
                "are",
                "was",
                "were",
            }
            question_keywords = {
                kw for kw in question.lower().split() if len(kw) >= 3 and kw not in stop_words
            }
            if not question_keywords:
                question_keywords = {kw for kw in question.lower().split() if len(kw) >= 2}

            relevant_results = []
            for result in search_results:
                content_lower = result.content.lower()
                if not question_keywords or any(keyword in content_lower for keyword in question_keywords):
                    relevant_results.append(result)
                else:
                    logger.debug(
                        "Search result filtered by keyword match: title='%s', chunk=%s",
                        result.title[:80] if result.title else "Unknown title",
                        result.chunk_index,
                    )

            if not relevant_results:
                logger.warning("All results filtered out; fallback to original search results")
                relevant_results = search_results

            actually_reranked = (
                self.last_config.get("retrieval_mode") == "hybrid_rerank"
                and float(self.last_stage_ms.get("rerank", 0.0)) > 0
            )
            confidence_metrics = confidence_calculator.calculate_dynamic_confidence(
                relevant_results, question, use_rerank=actually_reranked
            )

            if confidence_metrics.overall_confidence < 0.3:
                logger.warning(
                    "Low confidence %.3f, continue generating answer with %s contexts",
                    confidence_metrics.overall_confidence,
                    len(relevant_results),
                )

            max_context_segments = min(8, max(1, runtime_options["top_k"]))
            top_results = relevant_results[:max_context_segments]
            contexts = [result.content for result in top_results]

            context_token_limit = runtime_options["context_token_limit"]
            if context_token_limit:
                current_tokens = 0
                limited_contexts: List[str] = []
                limited_results: List[SearchResult] = []
                for result in top_results:
                    text = result.content or ""
                    token_count = len(text.split())
                    if current_tokens + token_count <= context_token_limit:
                        limited_contexts.append(text)
                        limited_results.append(result)
                        current_tokens += token_count
                        continue

                    remaining = context_token_limit - current_tokens
                    if remaining > 0:
                        truncated = " ".join(text.split()[:remaining]).strip()
                        if truncated:
                            limited_contexts.append(truncated)
                            limited_results.append(result)
                    break

                if limited_contexts:
                    contexts = limited_contexts
                    top_results = limited_results

            stage_ms["context_build"] = (time.perf_counter() - context_start) * 1000.0

            llm_start = time.perf_counter()
            answer = self._generate_answer(question, contexts)
            stage_ms["llm_generate"] = (time.perf_counter() - llm_start) * 1000.0

            post_start = time.perf_counter()
            sources = self._build_sources_with_usage(top_results, answer)
            stage_ms["postprocess"] = (time.perf_counter() - post_start) * 1000.0

            return RAGAnswer(
                answer=answer,
                sources=sources,
                confidence=confidence_metrics.overall_confidence,
                total_contexts=len(top_results),
            )
        except Exception as e:
            logger.error(f"QA failed: {e}")
            return RAGAnswer(
                answer=f"An error occurred while processing the question: {str(e)}",
                sources=[],
                confidence=0.0,
                total_contexts=0,
            )
        finally:
            stage_ms["total"] = (time.perf_counter() - total_start) * 1000.0
            self.last_stage_ms = stage_ms

    def _generate_answer(self, question: str, contexts: List[str]) -> str:
        fallback_msg = (
            "The provided documents do not contain information about this topic. "
            "Please try rephrasing your question or adding relevant documents."
        )
        try:
            context_text = "\n\n".join(
                [f"Document snippet {i + 1}:\n{ctx}" for i, ctx in enumerate(contexts)]
            )

            prompt = f"""You are a professional astrobiology research assistant. Answer ONLY with information from the document snippets.

Document content:
{context_text}

Question: {question}

Output format (use English, no code fences):
Answer:
- <one sentence conclusion or say the info is not available>

Key points:
- <fact 1 with short supporting detail> [S1]
- <fact 2> [S2]
- <fact 3> [S1, S3]

Sources:
[S1] <title>, page <page>, score=<score>
[S2] <title>, page <page>, score=<score>

Rules:
- If the snippets do NOT contain the answer, reply exactly: "The provided documents do not contain information about this topic. Please try rephrasing your question or adding relevant documents."
- Do NOT invent information; only use what appears in the snippets.
- Always cite snippet numbers as [S#] that correspond to "Document snippet <#>" above."""

            response = requests.post(
                "http://localhost:11434/v1/chat/completions",
                json={
                    "model": "llama3.1:8b-instruct-q4_K_M",
                    "messages": [
                        {"role": "system", "content": "You are a professional astrobiology assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.1,
                    "top_p": 1,
                },
                timeout=60,
            )

            if response.status_code == 200:
                result = response.json()
                answer_text = result["choices"][0]["message"]["content"]
                return self._validate_and_clean_answer(answer_text, len(contexts), fallback_msg)
            return "Sorry, the LLM service is temporarily unavailable."
        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return f"An error occurred while generating the answer: {str(e)}"

    def _validate_and_clean_answer(self, answer: str, max_index: int, fallback_msg: str) -> str:
        try:
            text = answer or ""
            lower_text = text.lower()
            if "snippet missing" in lower_text or "missing snippet" in lower_text:
                return fallback_msg

            citations = [int(c) for c in re.findall(r"\[s(\d+)\]", text, flags=re.IGNORECASE)]
            if not citations:
                return fallback_msg
            if max_index <= 0 or max(citations) > max_index or min(citations) < 1:
                return fallback_msg

            key_points_section = ""
            m = re.search(r"Key points:(.*)Sources:", text, flags=re.IGNORECASE | re.DOTALL)
            if m:
                key_points_section = m.group(1)
            if key_points_section:
                lines = [ln.strip() for ln in key_points_section.splitlines() if ln.strip().startswith("-")]
                if any("[s" not in ln.lower() for ln in lines):
                    return fallback_msg
            return text
        except Exception:
            return fallback_msg

    def _build_sources_with_usage(self, results: List[SearchResult], answer_text: str) -> List[Dict[str, Any]]:
        try:
            citations = {int(c) for c in re.findall(r"\[s(\d+)\]", answer_text or "", flags=re.IGNORECASE)}
            sources = []
            for idx, result in enumerate(results, start=1):
                sources.append(
                    {
                        "content": result.content,
                        "title": result.title,
                        "page": int(result.page) if result.page is not None else 0,
                        "score": float(result.score) if result.score is not None else 0.0,
                        "document_id": result.document_id,
                        "used": idx in citations,
                    }
                )
            return sources
        except Exception as e:
            logger.error(f"Build sources failed: {e}")
            return []
