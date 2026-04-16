"""
Unified RAG API views.
"""
import json
import logging
import time

import requests
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .bench_logging import append_bench_log, init_stage_ms, new_run_id, normalize_config
from .unified_rag_service import RAGException, UnifiedRAGService

logger = logging.getLogger(__name__)

unified_rag_service = UnifiedRAGService()


def handle_rag_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RAGException as e:
            logger.error("RAG error: %s", e.message)
            return JsonResponse(
                {
                    "success": False,
                    "error": e.message,
                    "code": e.code,
                    "details": e.details,
                },
                status=400,
            )
        except Exception as e:
            logger.error("System error: %s", str(e))
            return JsonResponse(
                {
                    "success": False,
                    "error": "System internal error",
                    "code": "SYSTEM_ERROR",
                },
                status=500,
            )

    return wrapper


@method_decorator(csrf_exempt, name="dispatch")
class UnifiedSearchView(View):
    @handle_rag_exception
    def post(self, request):
        try:
            data = json.loads(request.body)
            query = data.get("query", "").strip()
            if not query:
                return JsonResponse(
                    {"success": False, "error": "Query is required", "code": "INVALID_QUERY"},
                    status=400,
                )

            strategy = data.get("strategy", "comprehensive")
            limit = min(int(data.get("limit", 100)), 1000)
            use_hybrid = data.get("use_hybrid", True)
            use_rerank = data.get("use_rerank", True)
            use_aggregation = data.get("use_aggregation", False)

            if not unified_rag_service._is_initialized:
                if not unified_rag_service.initialize():
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "RAG service initialization failed",
                            "code": "SERVICE_INIT_FAILED",
                        },
                        status=500,
                    )

            if strategy == "meteorite":
                results = unified_rag_service.search_meteorite_content(query, limit)
            else:
                results = unified_rag_service.search(
                    query,
                    limit,
                    use_hybrid=use_hybrid,
                    use_rerank=use_rerank,
                    use_aggregation=use_aggregation,
                )

            segments = []
            for result in results:
                metadata = result.metadata.copy() if result.metadata else {}
                for key, value in metadata.items():
                    if hasattr(value, "dtype"):
                        if "float" in str(value.dtype):
                            metadata[key] = float(value)
                        elif "int" in str(value.dtype):
                            metadata[key] = int(value)

                segments.append(
                    {
                        "id": f"{result.document_id}_{result.chunk_index}",
                        "content": result.content,
                        "title": result.title,
                        "document_id": result.document_id,
                        "page_number": int(result.page) if result.page is not None else 0,
                        "chunk_index": int(result.chunk_index) if result.chunk_index is not None else -1,
                        "relevance_score": float(result.score) if result.score is not None else 0.0,
                        "metadata": metadata,
                    }
                )

            return JsonResponse(
                {
                    "success": True,
                    "data": {
                        "segments": segments,
                        "total_count": len(segments),
                        "query": query,
                        "strategy": strategy,
                    },
                    "message": "Search completed",
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON", "code": "INVALID_JSON"},
                status=400,
            )


@method_decorator(csrf_exempt, name="dispatch")
class UnifiedQuestionView(View):
    @handle_rag_exception
    def post(self, request):
        run_id = new_run_id()
        request_start = time.perf_counter()
        question = ""
        success = False
        error_type = None
        status_code = 200
        payload = {}

        try:
            data = json.loads(request.body)
            question = data.get("question", "").strip()
            if not question:
                status_code = 400
                error_type = "INVALID_QUESTION"
                payload = {
                    "success": False,
                    "error": "Question is required",
                    "code": "INVALID_QUESTION",
                }
            else:
                if not unified_rag_service._is_initialized:
                    if not unified_rag_service.initialize():
                        status_code = 500
                        error_type = "SERVICE_INIT_FAILED"
                        payload = {
                            "success": False,
                            "error": "RAG service initialization failed",
                            "code": "SERVICE_INIT_FAILED",
                        }
                    else:
                        answer = unified_rag_service.ask_question(question)
                        success = True
                        payload = {
                            "success": True,
                            "data": {
                                "answer": answer.answer,
                                "sources": answer.sources,
                                "confidence": answer.confidence,
                                "total_contexts": answer.total_contexts,
                            },
                            "message": "QA completed",
                        }
                else:
                    answer = unified_rag_service.ask_question(question)
                    success = True
                    payload = {
                        "success": True,
                        "data": {
                            "answer": answer.answer,
                            "sources": answer.sources,
                            "confidence": answer.confidence,
                            "total_contexts": answer.total_contexts,
                        },
                        "message": "QA completed",
                    }
        except json.JSONDecodeError as e:
            status_code = 400
            error_type = type(e).__name__
            payload = {"success": False, "error": "Invalid JSON", "code": "INVALID_JSON"}
        except RAGException as e:
            status_code = 400
            error_type = type(e).__name__
            payload = {
                "success": False,
                "error": e.message,
                "code": e.code,
                "details": e.details,
            }
        except Exception as e:
            status_code = 500
            error_type = type(e).__name__
            payload = {
                "success": False,
                "error": "System internal error",
                "code": "SYSTEM_ERROR",
            }
            logger.exception("Unified question failed: %s", e)

        stage_ms = dict(getattr(unified_rag_service, "last_stage_ms", {}) or {})
        if not stage_ms:
            stage_ms = init_stage_ms()
        stage_ms["total"] = (time.perf_counter() - request_start) * 1000.0

        append_bench_log(
            run_id=run_id,
            endpoint="qa_ask",
            success=success,
            error_type=error_type,
            config=normalize_config(getattr(unified_rag_service, "last_config", None)),
            stage_ms=stage_ms,
            question=question,
        )

        return JsonResponse(payload, status=status_code)


@method_decorator(csrf_exempt, name="dispatch")
class UnifiedExtractionView(View):
    @handle_rag_exception
    def post(self, request):
        run_id = new_run_id()
        request_start = time.perf_counter()
        stage_ms = init_stage_ms()
        success = False
        error_type = None
        status_code = 200
        payload = {}

        try:
            data = json.loads(request.body)
            content = data.get("content", "").strip()
            if not content:
                status_code = 400
                error_type = "INVALID_CONTENT"
                payload = {
                    "success": False,
                    "error": "Content is required",
                    "code": "INVALID_CONTENT",
                }
            else:
                if not unified_rag_service._is_initialized:
                    if not unified_rag_service.initialize():
                        status_code = 500
                        error_type = "SERVICE_INIT_FAILED"
                        payload = {
                            "success": False,
                            "error": "RAG service initialization failed",
                            "code": "SERVICE_INIT_FAILED",
                        }
                        stage_ms["total"] = (time.perf_counter() - request_start) * 1000.0
                    else:
                        llm_start = time.perf_counter()
                        meteorite_data = unified_rag_service.extract_meteorite_data(content)
                        stage_ms["llm_generate"] = (time.perf_counter() - llm_start) * 1000.0
                        if meteorite_data:
                            success = True
                            payload = {
                                "success": True,
                                "data": {
                                    "name": meteorite_data.name,
                                    "classification": meteorite_data.classification,
                                    "discovery_location": meteorite_data.discovery_location,
                                    "origin": meteorite_data.origin,
                                    "organic_compounds": meteorite_data.organic_compounds,
                                    "contamination_exclusion_method": meteorite_data.contamination_exclusion_method,
                                    "references": meteorite_data.references,
                                },
                                "message": "Extraction completed",
                            }
                        else:
                            status_code = 404
                            error_type = "NO_METEORITE_DATA"
                            payload = {
                                "success": False,
                                "error": "No meteorite data found",
                                "code": "NO_METEORITE_DATA",
                            }
                else:
                    llm_start = time.perf_counter()
                    meteorite_data = unified_rag_service.extract_meteorite_data(content)
                    stage_ms["llm_generate"] = (time.perf_counter() - llm_start) * 1000.0
                    if meteorite_data:
                        success = True
                        payload = {
                            "success": True,
                            "data": {
                                "name": meteorite_data.name,
                                "classification": meteorite_data.classification,
                                "discovery_location": meteorite_data.discovery_location,
                                "origin": meteorite_data.origin,
                                "organic_compounds": meteorite_data.organic_compounds,
                                "contamination_exclusion_method": meteorite_data.contamination_exclusion_method,
                                "references": meteorite_data.references,
                            },
                            "message": "Extraction completed",
                        }
                    else:
                        status_code = 404
                        error_type = "NO_METEORITE_DATA"
                        payload = {
                            "success": False,
                            "error": "No meteorite data found",
                            "code": "NO_METEORITE_DATA",
                        }
        except json.JSONDecodeError as e:
            status_code = 400
            error_type = type(e).__name__
            payload = {"success": False, "error": "Invalid JSON", "code": "INVALID_JSON"}
        except RAGException as e:
            status_code = 400
            error_type = type(e).__name__
            payload = {
                "success": False,
                "error": e.message,
                "code": e.code,
                "details": e.details,
            }
        except Exception as e:
            status_code = 500
            error_type = type(e).__name__
            payload = {
                "success": False,
                "error": "System internal error",
                "code": "SYSTEM_ERROR",
            }
            logger.exception("Unified extraction failed: %s", e)

        stage_ms["total"] = (time.perf_counter() - request_start) * 1000.0
        # Keep extraction benchmark schema stable even when stages are not triggered.
        stage_ms.setdefault("ocr", 0.0)
        stage_ms.setdefault("chunk", 0.0)
        stage_ms.setdefault("embed", 0.0)
        stage_ms.setdefault("vector_write", 0.0)
        stage_ms.setdefault("db_write", 0.0)
        append_bench_log(
            run_id=run_id,
            endpoint="extract_task",
            success=success,
            error_type=error_type,
            config=normalize_config(
                {
                    "retrieval_mode": "extract_only",
                    "top_k": None,
                    "rerank_k": None,
                    "hybrid_alpha": None,
                    "context_token_limit": None,
                }
            ),
            stage_ms=stage_ms,
        )
        return JsonResponse(payload, status=status_code)


@require_http_methods(["GET"])
def service_status(request):
    try:
        if not unified_rag_service._is_initialized:
            unified_rag_service.initialize()

        weaviate_connected = False
        embedding_available = False

        if unified_rag_service.weaviate_connection:
            weaviate_connected = unified_rag_service.weaviate_connection.test_connection()

        if unified_rag_service.embedding_service and hasattr(
            unified_rag_service.embedding_service, "_model"
        ):
            embedding_available = unified_rag_service.embedding_service._model is not None

        llm_connected = False
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            llm_connected = response.status_code == 200
        except Exception:
            llm_connected = False

        return JsonResponse(
            {
                "success": True,
                "data": {
                    "weaviate_connected": weaviate_connected,
                    "embedding_available": embedding_available,
                    "llm_connected": llm_connected,
                    "service_initialized": unified_rag_service._is_initialized,
                },
                "message": "Service healthy"
                if all([weaviate_connected, embedding_available, llm_connected])
                else "Service partially unavailable",
            }
        )
    except Exception as e:
        logger.error("Status check failed: %s", e)
        return JsonResponse(
            {"success": False, "error": "Status check failed", "code": "STATUS_CHECK_FAILED"},
            status=500,
        )
