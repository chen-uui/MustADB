"""
鏁版嵁鎻愬彇鐩稿叧鐨凙PI瑙嗗浘
鎻愪緵浠庢枃妗ｅ簱鎻愬彇闄ㄧ煶鏁版嵁鐨勫姛鑳?"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import JsonResponse

import json
import time
import uuid

from django.utils import timezone
from django.db import transaction
from typing import Dict, List, Any, Optional

# 娣诲姞绫诲瀷妫€鏌ョ浉鍏崇殑瀵煎叆
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meteorite_search.models import DataExtractionTask

from .rag_meteorite_extractor import RAGMeteoriteExtractor
from .rag_service import RAGService
from .single_task_extraction import single_task_manager
from meteorite_search.models import DataExtractionTask
from .thread_manager import thread_manager
from .task_status_manager import task_status_manager
from .utils import parse_request_body, validate_pagination_params, validate_threshold, create_error_response
from .bench_logging import append_bench_log, init_stage_ms, new_run_id, normalize_config

logger = logging.getLogger(__name__)


def _resolve_task_id_from_request(request, task_id: Optional[str] = None) -> str:
    if task_id:
        return task_id

    request_data = getattr(request, "data", None) or {}
    if isinstance(request_data, dict):
        task_id = request_data.get("task_id") or request_data.get("taskId")
        if task_id:
            return str(task_id)

    query_params = getattr(request, "query_params", None) or {}
    task_id = query_params.get("task_id") or query_params.get("taskId")
    if task_id:
        return str(task_id)

    raise ValueError("missing task_id")


def _build_task_failure_progress(error: Exception) -> Dict[str, Any]:
    return {
        "status": "failed",
        "error_message": str(error),
        "error_type": type(error).__name__,
        "failed_at": timezone.now().isoformat(),
        "status_text": "failed",
    }


def _persist_failed_task(task_id: str, error: Exception) -> None:
    failure_progress = _build_task_failure_progress(error)
    task_status_manager.update_task_status(
        task_id=task_id,
        status="failed",
        progress_data=failure_progress,
    )

    try:
        task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
        latest_progress = dict(task.results.get("latest_progress", {}) or {}) if isinstance(task.results, dict) else {}
        latest_progress.update(failure_progress)
        task.status = "failed"
        task.completed_at = timezone.now()
        task.results = {
            **(task.results or {}),
            "error_message": str(error),
            "error_type": type(error).__name__,
            "latest_progress": latest_progress,
        }
        task.save(update_fields=["status", "completed_at", "results"])
    except DataExtractionTask.DoesNotExist:  # type: ignore
        logger.error("Task %s no longer exists, failed status cannot be saved", task_id)
    except Exception as save_error:
        logger.error("Task %s failed while saving failed status: %s", task_id, save_error)


def _serialize_segment(seg) -> Dict[str, Any]:
    return {
        "id": seg.id,
        "documentId": seg.document_id,
        "chunkIndex": seg.chunk_index,
        "title": seg.title,
        "score": seg.score,
        "page": seg.page,
        "content": seg.content,
        "highlight": seg.highlight,
        "authors": getattr(seg, "authors", []),
    }


def _serialize_segments(session, segment_list) -> List[Dict[str, Any]]:
    return [_serialize_segment(seg) for seg in segment_list]


@api_view(["POST"])
@permission_classes([AllowAny])  # TODO: tighten permissions when ready
def single_task_search(request):
    """
    鍗曚换鍔℃悳绱PI
    浼樺寲锛氫娇鐢ㄧ粺涓€鐨勯敊璇鐞嗗拰鎬ц兘鐩戞帶
    """
    try:
        # 浼樺寲锛氫娇鐢ㄧ粺涓€鐨勫伐鍏峰嚱鏁拌В鏋愬拰楠岃瘉鍙傛暟
        try:
            payload = parse_request_body(request)
        except ValueError as e:
            return create_error_response(str(e), status.HTTP_400_BAD_REQUEST)
        
        keywords = payload.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [keywords]
        
        # 浣跨敤缁熶竴鐨勫弬鏁伴獙璇佸嚱鏁?        threshold = validate_threshold(payload.get("threshold", 0.5))
        sort_by = payload.get("sortBy", "score_desc")
        page, page_size = validate_pagination_params(
            payload.get("page", 1),
            payload.get("pageSize", 50),
            max_page_size=100
        )

        session = single_task_manager.start_search(keywords, threshold, sort_by)

        segment_page = single_task_manager.get_segments_page(session, page, page_size)
        total_segments = len(session.segment_order)

        logger.info("[single-task] 鍝嶅簲鐗囨鏁伴噺=%s", len(segment_page))

        return Response(
            {
                "success": True,
                "data": {
                    "session": single_task_manager.serialize_session(session),
                    "segments": {
                        "items": _serialize_segments(session, segment_page),
                        "page": page,
                        "pageSize": page_size,
                        "total": total_segments,
                        "allSegmentIds": session.segment_order,  # 鍖呭惈鎵€鏈夌墖娈礗D锛岀敤浜庡叏閫夊姛鑳?                        "unprocessedSegmentIds": session.segment_order,  # 鍒濆鏃舵墍鏈夌墖娈甸兘鏈鐞嗭紙鎴栦粠session涓幏鍙栵級
                    },
                },
            }
        )
    except ValueError as exc:
        logger.warning(f"鍗曚换鍔℃绱㈠弬鏁伴敊璇? {str(exc)}")
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as exc:
        logger.warning(f"鍗曚换鍔℃绱㈣繍琛屾椂閿欒: {str(exc)}")
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_409_CONFLICT)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("鍗曚换鍔℃绱㈠け璐? %s", exc)
        return Response(
            {"success": False, "error": "search failed, please try again later"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def single_task_enqueue(request):
    """
    鍗曚换鍔″叆闃烝PI
    浼樺寲锛氬弬鏁伴獙璇佸拰閿欒澶勭悊
    """
    try:
        # 浼樺寲锛氫娇鐢ㄧ粺涓€鐨勫伐鍏峰嚱鏁拌В鏋愬拰楠岃瘉鍙傛暟
        try:
            payload = parse_request_body(request)
        except ValueError as e:
            return create_error_response(str(e), status.HTTP_400_BAD_REQUEST)
        
        session_id = payload.get("sessionId")
        if not session_id:
            return create_error_response("缂哄皯sessionId鍙傛暟", status.HTTP_400_BAD_REQUEST)
        
        segment_ids = payload.get("segmentIds") or []
        if not isinstance(segment_ids, list):
            return create_error_response("segmentIds must be a list", status.HTTP_400_BAD_REQUEST)

        session = single_task_manager.enqueue_segments(session_id, segment_ids)
        return Response(
            {
                "success": True,
                "data": single_task_manager.serialize_session(session),
            }
        )
    except ValueError as exc:
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as exc:
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_409_CONFLICT)
    except Exception as exc:  # pragma: no cover
        logger.exception("鐗囨鍏ラ槦澶辫触: %s", exc)
        return Response({"success": False, "error": "鐗囨鍏ラ槦澶辫触"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def single_task_status(request):
    try:
        session_id = request.query_params.get("sessionId")
        if not session_id:
            raise ValueError("缂哄皯 sessionId")

        session = single_task_manager.get_session(session_id)
        if not session:
            return Response(
                {"success": False, "error": "session not found or expired"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"success": True, "data": single_task_manager.serialize_session(session)})
    except ValueError as exc:
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:  # pragma: no cover
        logger.exception("鏌ヨ浠诲姟鐘舵€佸け璐? %s", exc)
        return Response(
            {"success": False, "error": "status query failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def single_task_cancel(request):
    """
    鍙栨秷鍗曚换鍔PI
    浼樺寲锛氫娇鐢ㄧ粺涓€鐨勫弬鏁拌В鏋?    """
    try:
        try:
            payload = parse_request_body(request)
        except ValueError as e:
            return create_error_response(str(e), status.HTTP_400_BAD_REQUEST)
        
        session_id = payload.get("sessionId")
        if not session_id:
            raise ValueError("缂哄皯 sessionId")

        single_task_manager.cancel_session(session_id)
        session = single_task_manager.get_session(session_id)
        return Response({"success": True, "data": single_task_manager.serialize_session(session) if session else {}})
    except ValueError as exc:
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except RuntimeError as exc:
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_409_CONFLICT)
    except Exception as exc:  # pragma: no cover
        logger.exception("鍙栨秷浠诲姟澶辫触: %s", exc)
        return Response({"success": False, "error": "鍙栨秷澶辫触"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def single_task_segments(request):
    try:
        session_id = request.query_params.get("sessionId")
        if not session_id:
            raise ValueError("缂哄皯 sessionId")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("pageSize", 50))

        session = single_task_manager.get_session(session_id)
        if not session:
            return Response(
                {"success": False, "error": "session not found or expired"},
                status=status.HTTP_404_NOT_FOUND,
            )

        segment_page = single_task_manager.get_segments_page(session, page, page_size)
        total_segments = len(session.segment_order)

        # 璁＄畻鏈鐞嗙殑鐗囨ID锛堝凡鎴愬姛瀹屾垚鐨勶級
        processed_segment_ids = {
            item.segment.id for item in session.queue.values() 
            if item.status == "success"
        }
        unprocessed_segment_ids = [
            seg_id for seg_id in session.segment_order 
            if seg_id not in processed_segment_ids
        ]
        
        return Response(
            {
                "success": True,
                "data": {
                    "segments": {
                        "items": _serialize_segments(session, segment_page),
                        "page": page,
                        "pageSize": page_size,
                        "total": total_segments,
                        "allSegmentIds": session.segment_order,  # 鍖呭惈鎵€鏈夌墖娈礗D锛岀敤浜庡叏閫夊姛鑳?                        "unprocessedSegmentIds": unprocessed_segment_ids,  # 鏈鐞嗙殑鐗囨ID
                    }
                }
            }
        )
    except ValueError as exc:
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:  # pragma: no cover
        logger.exception("鍒嗛〉鑾峰彇鐗囨澶辫触: %s", exc)
        return Response({"success": False, "error": "鑾峰彇鐗囨澶辫触"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def extraction_preview_search(request):
    """Preview extraction-mode search results from the document library."""
    try:
        data = json.loads(request.body)
        query = data.get('searchQuery', '')  # 淇敼涓轰笌鍓嶇涓€鑷寸殑瀛楁鍚?        max_documents = int(data.get('maxDocuments', 10))  # 绉婚櫎纭紪鐮侀檺鍒讹紝鍏佽鐢ㄦ埛閫夋嫨鐨勬暟閲?        relevance_threshold = data.get('relevanceThreshold', 0.7)  # 淇敼涓轰笌鍓嶇涓€鑷寸殑瀛楁鍚?        
        if not query:
            return Response({
                'success': False,
                'error': 'request failed',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 鍒濆鍖朢AG鏈嶅姟
        rag_service = RAGService()
        if not rag_service.is_initialized:
            rag_service.initialize()
        
        # 璁＄畻鏈夋晥鐨則op_k锛? 琛ㄧず鍏ㄩ儴锛岃繖閲岀敤棰勮涓婇檺锛?        effective_top_k = max_documents if (isinstance(max_documents, int) and max_documents > 0) else 50
        # 鎵ц鍚戦噺鎼滅储
        search_results = rag_service.vector_search(
            query=query,
            top_k=effective_top_k
        )
        
        # 搴旂敤鐩稿叧鎬ч槇鍊艰繃婊?        filtered_results = []
        try:
            for r in search_results:
                score = float(getattr(r, 'score', 0.0) or 0.0)
                if score >= float(relevance_threshold):
                    filtered_results.append(r)
        except Exception:
            filtered_results = search_results
        
        # 鏍煎紡鍖栨悳绱㈢粨鏋?        documents = []
        for result in filtered_results:
            documents.append({
                'id': getattr(result, 'id', 'unknown'),
                'title': getattr(result, 'title', '鏈煡鏍囬'),
                'content': getattr(result, 'content', '')[:500] + '...' if len(getattr(result, 'content', '')) > 500 else getattr(result, 'content', ''),
                'score': getattr(result, 'score', 0.0),
                'metadata': getattr(result, 'metadata', {})
            })
        
        return Response({
            'success': True,
            'data': {
                'documents': documents,
                'total_found': len(documents),
                'query': query,
                'max_documents': max_documents,
                'relevance_threshold': relevance_threshold
            }
        })
        
    except Exception as e:
        logger.error(f"棰勮鎼滅储澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'鎼滅储澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def preview_search(request):
    try:
        data = json.loads(request.body)
        query = data.get('searchQuery', '')  # 淇敼涓轰笌鍓嶇涓€鑷寸殑瀛楁鍚?        max_documents = int(data.get('maxDocuments', 10))  # 绉婚櫎纭紪鐮侀檺鍒讹紝鍏佽鐢ㄦ埛閫夋嫨鐨勬暟閲?        relevance_threshold = data.get('relevanceThreshold', 0.7)  # 淇敼涓轰笌鍓嶇涓€鑷寸殑瀛楁鍚?        
        if not query:
            return Response({
                'success': False,
                'error': 'request failed',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 鍒濆鍖朢AG鏈嶅姟
        rag_service = RAGService()
        if not rag_service.is_initialized:
            rag_service.initialize()
        
        # 璁＄畻鏈夋晥鐨則op_k锛? 琛ㄧず鍏ㄩ儴锛岃繖閲岀敤棰勮涓婇檺锛?        effective_top_k = max_documents if (isinstance(max_documents, int) and max_documents > 0) else 50
        # 鎵ц鍚戦噺鎼滅储
        search_results = rag_service.vector_search(
            query=query,
            top_k=effective_top_k
        )
        
        # 搴旂敤鐩稿叧鎬ч槇鍊艰繃婊?        filtered_results = []
        try:
            for r in search_results:
                score = float(getattr(r, 'score', 0.0) or 0.0)
                if score >= float(relevance_threshold):
                    filtered_results.append(r)
        except Exception:
            filtered_results = search_results
        
        # 鏍煎紡鍖栨悳绱㈢粨鏋?        documents = []
        for result in filtered_results:
            documents.append({
                'id': getattr(result, 'id', 'unknown'),
                'title': getattr(result, 'title', '鏈煡鏍囬'),
                'content': getattr(result, 'content', '')[:500] + '...' if len(getattr(result, 'content', '')) > 500 else getattr(result, 'content', ''),
                'score': getattr(result, 'score', 0.0),
                'source': getattr(result, 'source', '鏈煡鏉ユ簮')
            })
        
        return Response({
            'success': True,
            'data': {
                'documents': documents,
                'total_found': len(documents),
                'query': query,
                'relevance_threshold': relevance_threshold
            }
        })
        
    except Exception as e:
        logger.error(f"鎼滅储棰勮澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'鎼滅储棰勮澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_batch_extraction_state(request):
    """Reset batch extraction state and clear saved checkpoints."""
    try:
        from .batch_extraction_service import BatchExtractionService
        
        # 鑾峰彇璇锋眰鏁版嵁
        data = json.loads(request.body) if request.body else {}
        task_id = data.get('task_id')  # 鍙€夛細鎸囧畾浠诲姟ID
        
        # 鍒涘缓鏈嶅姟瀹炰緥骞堕噸缃姸鎬?        service = BatchExtractionService()
        result = service.reset_batch_extraction_state(task_id=task_id)
        
        if result['success']:
            logger.info(f"鎵归噺鎻愬彇鐘舵€侀噸缃垚鍔? {result['message']}")
            return Response({
                'success': True,
                'message': result['message'],
                'data': {
                    'cleared_documents': result['cleared_documents'],
                    'cleared_logs': result['cleared_logs'],
                    'checkpoints_cleared': result.get('checkpoints_cleared', False),
                    'reset_time': result['reset_time']
                }
            })
        else:
            logger.error(f"鎵归噺鎻愬彇鐘舵€侀噸缃け璐? {result['error']}")
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"閲嶇疆鎵归噺鎻愬彇鐘舵€丄PI璋冪敤澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'閲嶇疆澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def start_extraction_from_db(request):
    """Start extraction from the document library."""
    try:
        data = json.loads(request.body)
        
        # 鎻愬彇鍙傛暟
        search_config = data.get('searchConfig', {})
        extraction_options = data.get('extractionOptions', {})
        
        query = search_config.get('searchQuery', '')
        max_documents = int(search_config.get('maxDocuments', 50))
        relevance_threshold = search_config.get('relevanceThreshold', 0.7)
        
        # 濡傛灉娌℃湁鎻愪緵鎼滅储璇嶏紝浣跨敤榛樿鐨勯櫒鐭崇浉鍏虫悳绱㈣瘝
        if not query:
            query = 'meteorite'
            logger.info("鏈彁渚涙悳绱㈣瘝锛屼娇鐢ㄩ粯璁ゆ悳绱㈣瘝: meteorite")
        
        # 妫€鏌ユ槸鍚﹂€夋嫨浜嗘彁鍙栭€夐」锛屽鏋滄病鏈夐€夋嫨鍒欎娇鐢ㄩ粯璁ら€夐」
        has_options = any([
            extraction_options.get('extractBasicInfo', False),
            extraction_options.get('extractLocation', False),
            extraction_options.get('extractClassification', False),
            extraction_options.get('extractOrganicCompounds', False),
            extraction_options.get('extractContamination', False),
            extraction_options.get('extractReferences', False)
        ])
        
        if not has_options:
            # 浣跨敤榛樿鎻愬彇閫夐」
            extraction_options = {
                'extractBasicInfo': True,
                'extractLocation': True,
                'extractClassification': True,
                'extractOrganicCompounds': True,
                'extractContamination': False,
                'extractReferences': False
            }
            logger.info("鏈€夋嫨鎻愬彇閫夐」锛屼娇鐢ㄩ粯璁ら€夐」")
        
        # 鍒涘缓浠诲姟ID
        task_id = str(uuid.uuid4())
        
        # 鍒涘缓鏁版嵁鎻愬彇浠诲姟璁板綍
        # 澶勭悊鍖垮悕鐢ㄦ埛鎯呭喌
        created_by = None
        if request.user and request.user.is_authenticated:
            created_by = request.user
        
        task = DataExtractionTask.objects.create(  # type: ignore
            task_id=task_id,
            task_type='rag_extraction',
            status='running',
            parameters={
                'search_config': search_config,
                'extraction_options': extraction_options,
                'query': query,
                'max_documents': max_documents,
                'relevance_threshold': relevance_threshold
            },
            created_by=created_by,
            started_at=timezone.now()
        )

        initial_total = max_documents if (isinstance(max_documents, int) and max_documents > 0) else 0
        if initial_total:
            task.total_documents = initial_total
            task.save(update_fields=['total_documents'])

        # 绔嬪嵆璁板綍鍒濆浠诲姟鐘舵€侊紝閬垮厤鍓嶇棣栨杞鍑虹幇404
        task_status_manager.update_task_status(
            task_id=task_id,
            status='running',
            progress_data={
                'progress_percentage': 0,
                'total_documents': initial_total,
                'processed_documents': 0,
                'successful_extractions': 0,
                'failed_extractions': 0,
                'status_text': 'preparing'
            }
        )
        
        # 妫€鏌ユ槸鍚︿负棰勮妯″紡
        preview_mode = data.get('preview_mode', False)
        
        # Use the incremental extraction workflow in a background thread.
        try:
            from .management.commands.incremental_merge_extraction import IncrementalMergeExtractor, IncrementalMergeConfig

            def run_task_background(tid: str, q: str, max_docs: int, rel_thr: float, preview: bool, stop_event=None, pause_event=None):
                try:
                    # Build the extractor configuration for this task.
                    config = IncrementalMergeConfig(
                        similarity_threshold=0.7,
                        merge_strategy='intelligent',
                        enable_field_level_merge=True,
                        enable_confidence_weighting=True,
                        save_interval=10
                    )
                    extractor = IncrementalMergeExtractor(config)
                    expected_total = max_docs if (isinstance(max_docs, int) and max_docs > 0) else 0

                    # 杩涘害鍥炶皟锛氬啓鍏askStatusManager
                    def progress_callback(progress: dict):
                        try:
                            status = progress.get('status', 'running')
                            if expected_total and not progress.get('total_documents'):
                                progress['total_documents'] = expected_total
                            progress.setdefault('status_text', _default_status_text(status))
                            task_status_manager.update_task_status(
                                task_id=tid,
                                status=status,
                                progress_data=progress
                            )
                            _persist_progress_snapshot(tid, status, progress)
                        except Exception as _:
                            pass

                    # 鎵ц
                    if preview:
                        docs = min(max_docs, 5) if (isinstance(max_docs, int) and max_docs > 0) else 5
                    else:
                        docs = max_docs
                    report = extractor.extract_and_merge_from_corpus(
                        search_query=q,
                        max_documents=docs,
                        relevance_threshold=rel_thr,
                        preview_only=preview,
                        progress_callback=progress_callback,
                        stop_event=stop_event,
                        pause_event=pause_event
                    )

                    # 鏈€缁堢姸鎬佷笌缁熻
                    if stop_event and stop_event.is_set():
                        final_status = 'cancelled'
                    else:
                        final_status = 'preview_ready' if preview else 'completed'
                    processing_stats = report.get('processing_stats', {})
                    extraction_stats = report.get('extraction_stats', {})

                    final_progress = {
                        'progress_percentage': _compute_progress_percentage(processing_stats, final_status),
                        'total_documents': processing_stats.get('total_documents') or expected_total or task.total_documents,
                        'processed_documents': processing_stats.get('processed_documents', 0),
                        'successful_extractions': (
                            processing_stats.get('new_extractions', 0) + processing_stats.get('merged_extractions', 0)
                        ),
                        'failed_extractions': extraction_stats.get('failed_extractions', 0) if extraction_stats else 0,
                        'status_text': 'preview_ready' if final_status == 'preview_ready' else ('completed' if final_status == 'completed' else 'stopped'),
                        'processing_stats': processing_stats,
                        'extraction_stats': extraction_stats,
                        'merge_stats': report.get('merge_stats', {}),
                        'quality_metrics': report.get('quality_metrics', {})
                    }

                    # Update the database task record with the final status.
                    try:
                        task_obj = DataExtractionTask.objects.get(task_id=tid)  # type: ignore
                        task_obj.status = final_status
                        task_obj.completed_at = timezone.now()
                        task_obj.total_documents = final_progress['total_documents']
                        task_obj.processed_documents = final_progress['processed_documents']
                        task_obj.successful_extractions = final_progress['successful_extractions']
                        task_obj.failed_extractions = final_progress['failed_extractions']
                        task_obj.results = {
                            'incremental_merge_report': report,
                            'processing_stats': processing_stats,
                            'extraction_stats': extraction_stats,
                            'merge_stats': report.get('merge_stats', {}),
                            'quality_metrics': report.get('quality_metrics', {}),
                            'extraction_results': report.get('extraction_results', []),
                            'latest_progress': final_progress
                        }
                        task_obj.save()
                    except Exception as _:
                        pass

                    task_status_manager.update_task_status(
                        task_id=tid,
                        status=final_status,
                        progress_data=final_progress
                    )
                    _persist_progress_snapshot(tid, final_status, final_progress)
                except Exception as e:
                    logger.error(f"鍚庡彴澧為噺鍚堝苟浠诲姟澶辫触: {e}")
                    _persist_failed_task(tid, e)

            # 鍚姩鍚庡彴绾跨▼
            thread_manager.start_thread(
                task_id=task_id,
                target_func=run_task_background,
                tid=task_id,
                q=query,
                max_docs=max_documents,
                rel_thr=relevance_threshold,
                preview=preview_mode
            )

            # 绔嬪嵆杩斿洖浠诲姟ID锛屽墠绔彲杞杩涘害
            return Response({
                'success': True,
                'data': {
                    'task_id': task_id,
                    'status': 'running',
                    'message': '浠诲姟宸插湪鍚庡彴鍚姩'
                }
            })

        except Exception as extraction_error:
            _persist_failed_task(task_id, extraction_error)
            logger.error(f"鏁版嵁鎻愬彇澶辫触: {str(extraction_error)}")
            return Response({
                'success': False,
                'error': f'鏁版嵁鎻愬彇澶辫触: {str(extraction_error)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"鍚姩鎻愬彇浠诲姟澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'鍚姩鎻愬彇浠诲姟澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_and_save_extraction(request):
    """Confirm and save previewed extraction data."""
    try:
        task_id = request.data.get('task_id')
        selected_data_indices = request.data.get('selected_data', [])
        if not task_id:
            return Response({
                'success': False,
                'error': '浠诲姟ID涓嶈兘涓虹┖'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 鑾峰彇浠诲姟璁板綍
        try:
            task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
        except DataExtractionTask.DoesNotExist:  # type: ignore
            return Response({
                'success': False,
                'error': 'request failed',
            }, status=status.HTTP_404_NOT_FOUND)
        
        if task.status != 'preview_ready':
            return Response({
                'success': False,
                'error': 'request failed',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        extraction_results = list(task.results.get('extraction_results') or [])
        if not extraction_results:
            return Response({
                'success': False,
                'error': 'No preview extraction results available for confirmation',
            }, status=status.HTTP_400_BAD_REQUEST)

        normalized_indices = []
        if not selected_data_indices:
            normalized_indices = [i for i, r in enumerate(extraction_results) if r.get('success', False)]
        else:
            if not isinstance(selected_data_indices, list):
                return Response({
                    'success': False,
                    'error': 'selected_data must be a list',
                }, status=status.HTTP_400_BAD_REQUEST)
            try:
                normalized_indices = [int(index) for index in selected_data_indices]
            except (TypeError, ValueError):
                return Response({
                    'success': False,
                    'error': 'selected_data must contain integer indexes',
                }, status=status.HTTP_400_BAD_REQUEST)

        if not normalized_indices:
            return Response({
                'success': False,
                'error': 'No preview entries selected for saving',
            }, status=status.HTTP_400_BAD_REQUEST)

        from .meteorite_storage_service import MeteoriteStorageService
        storage_service = MeteoriteStorageService()
        storage_service.initialize_rag_service()
        
        saved_count = 0
        failed_count = 0
        errors = []
        saved_pending_ids = []
        
        # Save the selected extraction results.
        for index in normalized_indices:
            if index < 0 or index >= len(extraction_results):
                failed_count += 1
                errors.append(f"selected_data index out of range: {index}")
                continue

            result_data = extraction_results[index] or {}
            meteorite_data = result_data.get('meteorite_data') or result_data.get('data') or {}
            if isinstance(meteorite_data, dict) and isinstance(meteorite_data.get('meteorite_data'), dict):
                meteorite_data = meteorite_data.get('meteorite_data') or {}

            if not result_data.get('success', False) or not isinstance(meteorite_data, dict) or not meteorite_data:
                failed_count += 1
                errors.append(f"preview entry {index} is not a successful extraction result")
                continue

            try:
                source_info = dict(result_data.get('source_info') or {})
                source_info.update({
                    'task_id': task_id,
                    'preview_index': index,
                    'confidence': result_data.get('confidence', 0.0),
                    'extraction_source': 'pdf',
                })

                storage_result = storage_service._store_to_database(
                    meteorite_data,
                    submitter=request.user if request.user.is_authenticated else None,
                    extraction_metadata=source_info,
                )
                
                if storage_result.get('success', False):
                    saved_count += 1
                    saved_pending_ids.append(storage_result.get('pending_id'))
                else:
                    failed_count += 1
                    storage_errors = storage_result.get('errors') or []
                    if not storage_errors and storage_result.get('error'):
                        storage_errors = [storage_result.get('error')]
                    errors.extend(storage_errors or [f"failed to save preview entry {index}"])
            except Exception as e:
                failed_count += 1
                errors.append(f"淇濆瓨鏁版嵁鏃跺嚭閿? {str(e)}")

        final_status = 'completed' if saved_count > 0 else 'failed'
        latest_progress = {
            'successful_extractions': saved_count,
            'failed_extractions': failed_count,
            'saved_count': saved_count,
            'saved_pending_ids': saved_pending_ids,
            'errors': errors,
            'status_text': final_status,
        }
        task.status = final_status
        task.completed_at = timezone.now()
        task.results = {
            **(task.results or {}),
            'saved_count': saved_count,
            'failed_count': failed_count,
            'saved_pending_ids': saved_pending_ids,
            'latest_progress': {
                **(task.results.get('latest_progress', {}) if isinstance(task.results, dict) else {}),
                **latest_progress,
            },
        }
        task.save(update_fields=['status', 'completed_at', 'results'])

        task_status_manager.update_task_status(
            task_id=task_id,
            status=final_status,
            progress_data=latest_progress,
        )

        if saved_count == 0:
            return Response({
                'success': False,
                'error': 'No preview extraction results were saved',
                'data': {
                    'task_id': task_id,
                    'saved_count': saved_count,
                    'failed_count': failed_count,
                    'errors': errors,
                },
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': True,
            'data': {
                'task_id': task_id,
                'saved_count': saved_count,
                'failed_count': failed_count,
                'saved_pending_ids': saved_pending_ids,
                'errors': errors,
                'message': f'Saved {saved_count} records' + (f', {failed_count} failed' if failed_count > 0 else '')
            }
        })
        
    except Exception as e:
        logger.error(f"纭淇濆瓨鎻愬彇鏁版嵁澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'纭淇濆瓨澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def start_batch_extraction(request):
    """
    Start asynchronous batch extraction task.
    """
    run_id = new_run_id()
    request_start = time.perf_counter()
    stage_ms = init_stage_ms()
    success = False
    error_type = None
    task_id = None

    try:
        batch_size = request.data.get('batch_size', 10)
        search_queries_provided = 'search_queries' in request.data
        search_queries = request.data.get('search_queries', [])
        extraction_options = request.data.get('extraction_options', {})

        if batch_size <= 0 or batch_size > 100:
            error_type = 'INVALID_BATCH_SIZE'
            return Response(
                {
                    'success': False,
                    'error': 'batch_size must be in range 1-100',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if search_queries_provided and (not search_queries or not isinstance(search_queries, list)):
            error_type = 'INVALID_SEARCH_QUERIES'
            return Response(
                {
                    'success': False,
                    'error': 'search_queries must be a non-empty list',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .batch_extraction_service import BatchExtractionService

        batch_service = BatchExtractionService()
        effective_search_queries = (
            search_queries if search_queries_provided else batch_service.get_default_search_terms()
        )

        db_start = time.perf_counter()
        task_id = str(uuid.uuid4())
        DataExtractionTask.objects.create(  # type: ignore
            task_id=task_id,
            task_type='batch_by_docs',
            status='pending',
            total_documents=0,
            processed_documents=0,
            successful_extractions=0,
            failed_extractions=0,
            parameters={
                'search_config': {
                    'batch_size': batch_size,
                    'search_queries': search_queries,
                },
                'extraction_options': extraction_options,
            },
            created_at=timezone.now(),
        )
        stage_ms['db_write'] = (time.perf_counter() - db_start) * 1000.0

        def run_batch_task(stop_event=None):
            return batch_service.execute_batch_extraction(
                task_id=task_id,
                batch_size=batch_size,
                search_queries=search_queries,
                extraction_options=extraction_options,
                stop_event=stop_event,
            )

        thread_manager.start_thread(
            task_id=task_id,
            target_func=run_batch_task,
        )

        success = True
        return Response(
            {
                'success': True,
                'data': {
                    'task_id': task_id,
                    'message': 'batch extraction task started',
                    'batch_size': batch_size,
                    'search_queries_count': len(effective_search_queries),
                },
            }
        )
    except Exception as e:
        logger.error(f"start_batch_extraction failed: {str(e)}")
        error_type = type(e).__name__
        return Response(
            {
                'success': False,
                'error': f'start_batch_extraction failed: {str(e)}',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    finally:
        stage_ms['total'] = (time.perf_counter() - request_start) * 1000.0
        # Keep extraction benchmark schema stable even when stages are not triggered.
        stage_ms.setdefault('ocr', 0.0)
        stage_ms.setdefault('chunk', 0.0)
        stage_ms.setdefault('embed', 0.0)
        stage_ms.setdefault('vector_write', 0.0)
        stage_ms.setdefault('db_write', 0.0)
        append_bench_log(
            run_id=run_id,
            endpoint='extract_task',
            success=success,
            error_type=error_type,
            config=normalize_config(
                {
                    'retrieval_mode': 'batch_extract',
                    'top_k': None,
                    'rerank_k': None,
                    'hybrid_alpha': None,
                    'context_token_limit': None,
                }
            ),
            stage_ms=stage_ms,
            extra={'task_id': task_id} if task_id else None,
        )

@api_view(['GET'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def get_extraction_progress(request, task_id):
    """Get extraction task progress from persisted task state."""
    logger.info("[progress] request task_id=%s", task_id)
    try:
        task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
    except DataExtractionTask.DoesNotExist:  # type: ignore
        return Response({
            'success': False,
            'error': 'request failed',
        }, status=status.HTTP_404_NOT_FOUND)

    latest_progress = {}
    if isinstance(task.results, dict):
        latest_progress = task.results.get('latest_progress', {}) or {}

    response_payload = {
        'task_id': task_id,
        'status': task.status,
        'progress_percentage': latest_progress.get('progress_percentage', task.get_progress_percentage()),
        'total_documents': latest_progress.get('total_documents', task.total_documents),
        'processed_documents': latest_progress.get('processed_documents', task.processed_documents),
        'successful_extractions': latest_progress.get('successful_extractions', task.successful_extractions),
        'failed_extractions': latest_progress.get('failed_extractions', task.failed_extractions),
        'created_at': task.created_at,
        'started_at': task.started_at,
        'completed_at': task.completed_at,
        'current_batch': latest_progress.get('current_batch', task.results.get('current_batch', 0) if task.results else 0),
        'total_batches': latest_progress.get('total_batches', task.results.get('total_batches', 0) if task.results else 0),
        'status_text': latest_progress.get('status_text', _default_status_text(task.status))
    }

    return Response({'success': True, 'data': response_payload})


def _default_status_text(status: str) -> str:
    mapping = {
        'running': 'running',
        'paused': 'paused',
        'completed': 'completed',
        'failed': 'failed',
        'cancelled': 'cancelled',
        'preview_ready': 'preview_ready',
        'pending': 'pending',
    }
    return mapping.get(status, 'processing')


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def search_meteorite_segments(request):
    """
    鎼滅储闄ㄧ煶鐩稿叧鐗囨 - 鍒嗘寮忔彁鍙栫殑绗竴姝?    杩斿洖鎵€鏈夋壘鍒扮殑闄ㄧ煶鐩稿叧鐗囨渚涚敤鎴烽€夋嫨
    """
    try:
        data = json.loads(request.body)
        
        # 鏀寔澶氱鍙傛暟鏍煎紡
        search_strategy = data.get('searchStrategy', 'comprehensive')
        custom_keywords = data.get('customKeywords', [])
        max_segments = int(data.get('maxSegments', data.get('limit', 1000)))  # 鏀寔limit鍙傛暟
        query_param = data.get('query', '')  # 鏀寔鐩存帴鐨剄uery鍙傛暟
        
        logger.info(f"寮€濮嬫悳绱㈤櫒鐭崇墖娈?- 绛栫暐: {search_strategy}, 鏈€澶х墖娈垫暟: {max_segments}, 鏌ヨ: {query_param}")
        
        # 鍒濆鍖朢AG闄ㄧ煶鎻愬彇鍣?        extractor = RAGMeteoriteExtractor()
        if not extractor.initialize_services():
            return JsonResponse({
                'success': False,
                'error': 'request failed',
                'segments': []
            }, status=500)
        
        # Build the search query according to the selected strategy.
        if query_param:
            query = query_param
        elif search_strategy == 'comprehensive':
            query = "meteorite organic compounds astrobiology chondrite"
        elif search_strategy == 'focused' or search_strategy == 'targeted':
            query = "meteorite amino acids organic matter chondrite"
        elif search_strategy == 'custom' and custom_keywords:
            # 纭繚鑷畾涔夊叧閿瘝鍖呭惈鍩烘湰鐨勯櫒鐭冲叧閿瘝
            base_keywords = ["meteorite"]
            all_keywords = base_keywords + custom_keywords
            query = " ".join(all_keywords)
        else:
            query = "meteorite"
        
        # 鎵ц鐗囨鎼滅储锛堝彧鎼滅储锛屼笉鎻愬彇锛?        segments = extractor._search_meteorite_segments_optimized(query, max_segments)
        
        # 鑾峰彇鏁版嵁搴撲腑鐨勫疄闄呯墖娈垫€绘暟
        total_segments = "鏈煡鏁伴噺"
        try:
            weaviate_client = getattr(extractor.rag_service, 'weaviate_client', None)
            if extractor.rag_service and weaviate_client:
                collection = weaviate_client.collections.get(extractor.rag_service.collection_name)
                response = collection.aggregate.over_all(total_count=True)
                total_segments = response.total_count
        except Exception as e:
            logger.warning(f"鑾峰彇鎬荤墖娈垫暟澶辫触: {e}")
        
        # 鏍煎紡鍖栬繑鍥炴暟鎹?        formatted_segments = []
        for i, segment in enumerate(segments):
            content = segment.get('content', '')
            formatted_segments.append({
                'id': f"segment_{i}",
                'document_id': segment.get('document_id', 'unknown'),
                'title': segment.get('title', '鏈煡鏂囨。'),
                'content': content[:800] + '...' if len(content) > 800 else content,
                'full_content': content,  # 瀹屾暣鍐呭鐢ㄤ簬鍚庣画鎻愬彇
                'relevance_score': segment.get('score', 0.0),
                'chunk_index': segment.get('chunk_index', 0),
                'source': segment.get('source', '鏈煡鏉ユ簮')
            })
        
        logger.info("Segment search completed, found %s relevant segments", len(formatted_segments))
        
        return JsonResponse({
            'success': True,
            'segments': formatted_segments,
            'total_found': len(formatted_segments),
            'total_segments': total_segments,  # 娣诲姞鎬荤墖娈垫暟淇℃伅
            'search_strategy': search_strategy,
            'max_segments': max_segments
        })
        
    except Exception as e:
        logger.error(f"鎼滅储闄ㄧ煶鐗囨澶辫触: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'鎼滅储澶辫触: {str(e)}',
            'segments': []
        }, status=500)


def _persist_progress_snapshot(task_id: str, status: str, progress: dict) -> None:
    try:
        with transaction.atomic():  # type: ignore
            task = DataExtractionTask.objects.select_for_update().get(task_id=task_id)  # type: ignore

            update_fields = set()

            if status and task.status != status:
                task.status = status
                update_fields.add('status')

            if 'total_documents' in progress and progress.get('total_documents') is not None:
                total_documents = int(progress['total_documents'])
                if task.total_documents != total_documents:
                    task.total_documents = total_documents
                    update_fields.add('total_documents')

            if 'processed_documents' in progress and progress.get('processed_documents') is not None:
                processed_documents = int(progress['processed_documents'])
                if task.processed_documents != processed_documents:
                    task.processed_documents = processed_documents
                    update_fields.add('processed_documents')

            if 'successful_extractions' in progress and progress.get('successful_extractions') is not None:
                success_count = int(progress['successful_extractions'])
                if task.successful_extractions != success_count:
                    task.successful_extractions = success_count
                    update_fields.add('successful_extractions')

            if 'failed_extractions' in progress and progress.get('failed_extractions') is not None:
                failed_count = int(progress['failed_extractions'])
                if task.failed_extractions != failed_count:
                    task.failed_extractions = failed_count
                    update_fields.add('failed_extractions')

            results = task.results or {}
            results['latest_progress'] = progress
            task.results = results
            update_fields.add('results')

            if update_fields:
                task.save(update_fields=list(update_fields))
    except DataExtractionTask.DoesNotExist:  # type: ignore
        pass
    except Exception as exc:  # pragma: no cover - best-effort persistence
        logger.debug("Persisting progress update failed: %s", exc)


def _compute_progress_percentage(processing_stats: Dict[str, Any], final_status: str) -> float:
    total_documents = processing_stats.get('total_documents') or 0
    processed_documents = processing_stats.get('processed_documents') or 0

    if total_documents:
        try:
            percentage = (processed_documents / total_documents) * 100
            return max(0.0, min(100.0, percentage))
        except Exception:
            return 0.0

    if final_status == 'completed':
        return 100.0
    return 0.0


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def extract_from_selected_segments(request):
    """
    浠庨€変腑鐨勭墖娈典腑鎻愬彇闄ㄧ煶鏁版嵁 - 鍒嗘寮忔彁鍙栫殑绗簩姝?    鏀寔鐪熸鐨勬壒娆″鐞嗗拰瀹炴椂杩涘害鏇存柊
    """
    try:
        data = json.loads(request.body)
        logger.info(f"鏀跺埌鎻愬彇璇锋眰鏁版嵁: {data}")
        
        # 鏀寔涓ょ瀛楁鍚嶆牸寮忥細鍓嶇鍙戦€佺殑鍜屽師鏉ョ殑
        selected_segments = data.get('selectedSegments', data.get('segment_ids', []))
        extraction_options = data.get('extractionOptions', data.get('extraction_options', {}))
        batch_size = int(data.get('batchSize', data.get('batch_size', 10)))  # 鑾峰彇鎵规澶у皬
        
        logger.info(f"瑙ｆ瀽鍚庣殑鐗囨鏁伴噺: {len(selected_segments)}, 鎵规澶у皬: {batch_size}, 鎻愬彇閫夐」: {extraction_options}")
        
        if not selected_segments:
            logger.warning("娌℃湁閫夋嫨鐗囨杩涜鎻愬彇")
            return JsonResponse({
                'success': False,
                'error': 'request failed',
            }, status=400)
        
        # Check whether any extraction options are selected.
        has_options = any([
            extraction_options.get('extractBasicInfo', extraction_options.get('extract_basic_info', False)),
            extraction_options.get('extractLocation', extraction_options.get('extract_location', False)),
            extraction_options.get('extractClassification', extraction_options.get('extract_classification', False)),
            extraction_options.get('extractOrganicCompounds', extraction_options.get('extract_organic_compounds', False)),
            extraction_options.get('extractContamination', extraction_options.get('extract_contamination', False)),
            extraction_options.get('extractReferences', extraction_options.get('extract_references', False))
        ])
        
        logger.info(f"鏄惁鏈夋彁鍙栭€夐」: {has_options}")
        
        if not has_options:
            logger.warning("娌℃湁閫夋嫨鎻愬彇閫夐」")
            return JsonResponse({
                'success': False,
                'error': '璇疯嚦灏戦€夋嫨涓€涓暟鎹彁鍙栭€夐」'
            }, status=400)
        
        # 璁＄畻鎵规淇℃伅
        total_segments = len(selected_segments)
        total_batches = (total_segments + batch_size - 1) // batch_size
        
        # 鍒涘缓浠诲姟璁板綍
        task_id = str(uuid.uuid4())
        task = DataExtractionTask.objects.create(  # type: ignore
            task_id=task_id,
            task_type='segment_extraction',
            status='running',
            total_documents=total_segments,
            processed_documents=0,
            successful_extractions=0,
            failed_extractions=0,
            parameters={
                'selected_segments': selected_segments,  # 淇濆瓨瀹屾暣鐨勭墖娈垫暟鎹?                'selected_segments_count': total_segments,
                'batch_size': batch_size,
                'extraction_options': extraction_options
            },
            results={
                'current_batch': 0,
                'total_batches': total_batches,
                'processed_segments': 0,
                'total_segments': total_segments,
                'extracted_records': 0
            },
            created_at=timezone.now(),
            started_at=timezone.now()
        )
        
        logger.info(f"鍒涘缓浠诲姟 {task_id}: 鎬荤墖娈?{total_segments}, 鎵规澶у皬={batch_size}, 鎬绘壒娆?{total_batches}")
        
        # Start background processing through the thread manager.
        thread_manager.start_thread(
            task_id=task_id,
            target_func=process_segments_in_batches,
            selected_segments=selected_segments,
            extraction_options=extraction_options,
            batch_size=batch_size
        )
        
        return JsonResponse({
            'success': True,
            'task_id': task_id,
            'message': f'Batch extraction started: {total_batches} batches, {total_segments} segments',
            'batch_info': {
                'total_segments': total_segments,
                'batch_size': batch_size,
                'total_batches': total_batches
            }
        })
        
    except Exception as e:
        logger.error(f"鍚姩鍒嗘寮忔彁鍙栧け璐? {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'鍚姩澶辫触: {str(e)}'
        }, status=500)


def process_segments_in_batches(task_id: str, selected_segments: List[Dict], 
                               extraction_options: Dict, batch_size: int, stop_event=None):
    """
    鍒嗘壒澶勭悊閫変腑鐨勭墖娈佃繘琛屾暟鎹彁鍙?    澧炲己鐨勯敊璇鐞嗗拰鐘舵€佸悓姝?    """
    logger.info(f"浠诲姟 {task_id}: 寮€濮嬪垎鎵瑰鐞嗭紝鎬荤墖娈垫暟={len(selected_segments)}, 鎵规澶у皬={batch_size}")
    
    try:
        # 鑾峰彇浠诲姟瀵硅薄
        task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
        
        # Ensure the task is still runnable before processing segments.
        if task.status not in ['running', 'pending']:
            logger.warning("Task %s is in status %s and cannot continue", task_id, task.status)
            return
            
        # Mark the task as running in the status manager.
        task_status_manager.update_task_status(
            task_id=task_id,
            status='running',
            progress_data={'started_at': timezone.now().isoformat()}
        )
        
        # 鍒濆鍖栨彁鍙栧櫒
        extractor = RAGMeteoriteExtractor()
        
        # 璁＄畻鎵规淇℃伅
        total_segments = len(selected_segments)
        total_batches = (total_segments + batch_size - 1) // batch_size
        
        # 鍒濆鍖栫粺璁?        successful_count = 0
        failed_count = 0
        extraction_results = []
        
        # 鏇存柊浠诲姟鍒濆鐘舵€?        task.total_documents = total_segments
        task.processed_documents = 0
        task.successful_extractions = 0
        task.failed_extractions = 0
        task.results.update({
            'total_batches': total_batches,
            'current_batch': 0,
            'status': f'寮€濮嬪鐞嗭紝鎬绘壒娆?{total_batches}',
            'progress_percentage': 0
        })
        task.save()
        
        logger.info("Task %s: starting batch processing with %s batches", task_id, total_batches)
        
        # Process the selected segments in batches.
        for batch_num in range(total_batches):
            # Exit immediately when an external stop signal is raised.
            if stop_event and stop_event.is_set():
                logger.info("Task %s: stop event received before batch processing", task_id)
                return
            
            # Stop when the persisted task status changes to paused/cancelled.
            try:
                current_task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
                current_task.refresh_from_db()
                if current_task.status in ['cancelled', 'paused']:
                    logger.info("Task %s: status changed to %s, stopping", task_id, current_task.status)
                    return
            except DataExtractionTask.DoesNotExist:  # type: ignore
                logger.error("Task %s: database record was deleted during processing", task_id)
                return
            
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_segments)
            batch_segments = selected_segments[start_idx:end_idx]
            
            logger.info(
                "Task %s: processing batch %s/%s (segments %s-%s)",
                task_id,
                batch_num + 1,
                total_batches,
                start_idx + 1,
                end_idx,
            )
            
            # 鏇存柊鎵规杩涘害
            task.results.update({
                'current_batch': batch_num + 1,
                'status': f'澶勭悊鎵规 {batch_num + 1}/{total_batches}'
            })
            task.save()
            
            # Process the segments within the current batch.
            batch_successful = 0
            batch_failed = 0
            
            for segment_idx, segment in enumerate(batch_segments):
                # Re-check the stop event before each segment.
                if stop_event and stop_event.is_set():
                    logger.info("Task %s: stop event received during segment processing", task_id)
                    return
                
                # Re-check persisted task status before each segment.
                try:
                    current_task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
                    current_task.refresh_from_db()
                    if current_task.status in ['cancelled', 'paused']:
                        logger.info("Task %s: status changed to %s during segment processing", task_id, current_task.status)
                        return
                except DataExtractionTask.DoesNotExist:  # type: ignore
                    logger.error("Task %s: database record missing during segment processing", task_id)
                    return
                
                try:
                    # 娣诲姞瓒呮椂鏈哄埗闃叉鍗曚釜鐗囨澶勭悊鍗℃锛圵indows鍏煎锛?                    import threading
                    import time
                    
                    result = None
                    exception_occurred = None
                    
                    def extract_with_timeout():
                        nonlocal result, exception_occurred
                        try:
                            # 鎻愬彇鍗曚釜鐗囨
                            result = extractor.extract_from_segment(
                                segment, 
                                extraction_options
                            )
                        except Exception as e:
                            exception_occurred = e
                    
                    # 鍒涘缓绾跨▼鎵ц鎻愬彇
                    extract_thread = threading.Thread(target=extract_with_timeout)
                    extract_thread.daemon = True
                    extract_thread.start()
                    
                    # 绛夊緟鏈€澶?0绉?                    extract_thread.join(timeout=30)
                    
                    if extract_thread.is_alive():
                        # 瓒呮椂澶勭悊
                        batch_failed += 1
                        failed_count += 1
                        error_msg = "鐗囨澶勭悊瓒呮椂锛?0绉掞級"
                        extraction_results.append({
                            'segment_id': segment.get('id', f'segment_{start_idx + segment_idx}'),
                            'success': False,
                            'error': error_msg
                        })
                        logger.error(f"浠诲姟 {task_id}: 鐗囨 {start_idx + segment_idx + 1} 澶勭悊瓒呮椂")
                        continue
                    
                    if exception_occurred:
                        raise exception_occurred
                    
                    if result and result.get('success', False):
                        batch_successful += 1
                        successful_count += 1
                        extraction_results.append({
                            'segment_id': segment.get('id', f'segment_{start_idx + segment_idx}'),
                            'success': True,
                            'data': result.get('data', {}),
                            'confidence': result.get('confidence', 0.0)
                        })
                        logger.debug(f"浠诲姟 {task_id}: 鐗囨 {start_idx + segment_idx + 1} 鎻愬彇鎴愬姛")
                    else:
                        batch_failed += 1
                        failed_count += 1
                        error_msg = result.get('error', 'Extraction failed') if result else 'Extraction returned no result'
                        extraction_results.append({
                            'segment_id': segment.get('id', f'segment_{start_idx + segment_idx}'),
                            'success': False,
                            'error': error_msg
                        })
                        logger.warning(f"浠诲姟 {task_id}: 鐗囨 {start_idx + segment_idx + 1} 鎻愬彇澶辫触: {error_msg}")
                        
                except Exception as segment_error:
                    batch_failed += 1
                    failed_count += 1
                    error_msg = f"鐗囨澶勭悊寮傚父: {str(segment_error)}"
                    extraction_results.append({
                        'segment_id': segment.get('id', f'segment_{start_idx + segment_idx}'),
                        'success': False,
                        'error': error_msg
                    })
                    logger.error(f"浠诲姟 {task_id}: 鐗囨 {start_idx + segment_idx + 1} 澶勭悊寮傚父: {str(segment_error)}")
                
                # 娣诲姞灏忓欢杩熼槻姝㈣繃搴﹀崰鐢ㄨ祫婧?                import time  # 纭繚瀵煎叆time妯″潡
                time.sleep(0.1)
            
            # 鏇存柊鎵规瀹屾垚鍚庣殑缁熻
            processed_count = start_idx + len(batch_segments)
            progress_percentage = (processed_count / total_segments) * 100
            
            # 鏇存柊浠诲姟杩涘害
            task.processed_documents = processed_count
            task.successful_extractions = successful_count
            task.failed_extractions = failed_count
            task.results.update({
                'current_batch': batch_num + 1,
                'processed_segments': processed_count,
                'successful_extractions': successful_count,
                'failed_extractions': failed_count,
                'progress_percentage': progress_percentage,
                'status': f'宸插畬鎴愭壒娆?{batch_num + 1}/{total_batches}',
                'extraction_results': extraction_results[-100:]  # 鍙繚鐣欐渶杩?00涓粨鏋滐紝閬垮厤鏁版嵁杩囧ぇ
            })
            task.save()
            
            logger.info(f"浠诲姟 {task_id}: 鎵规 {batch_num + 1} 瀹屾垚 - 鎴愬姛: {batch_successful}, 澶辫触: {batch_failed}")
            
            # 鎵规闂寸煭鏆備紤鎭紝閬垮厤杩囪浇
            import time
            time.sleep(0.5)
        
        # 鏈€缁堟鏌ヤ换鍔＄姸鎬?        task.refresh_from_db()
        if task.status in ['cancelled', 'paused']:
            logger.info(f"浠诲姟 {task_id}: 澶勭悊瀹屾垚鏃跺彂鐜扮姸鎬佷负 {task.status}锛屼笉鏇存柊涓篶ompleted")
            return
        
        # 鏇存柊鏈€缁堜换鍔＄姸鎬?        task.status = 'completed'
        task.completed_at = timezone.now()
        task.successful_extractions = successful_count
        task.failed_extractions = failed_count
        task.results.update({
            'extraction_results': extraction_results,
            'statistics': {
                'total_segments': total_segments,
                'successful_extractions': successful_count,
                'failed_extractions': failed_count,
                'success_rate': (successful_count / total_segments * 100) if total_segments > 0 else 0
            },
            'status': 'completed',
            'progress_percentage': 100,
            'completed_at': timezone.now().isoformat()
        })
        task.save()
        
        logger.info(
            "Task %s completed: %s successful, %s failed",
            task_id,
            successful_count,
            failed_count,
        )
        
    except DataExtractionTask.DoesNotExist:  # type: ignore
        logger.error("Task %s does not exist", task_id)
        # Nothing else can be updated when the task row is gone.
    except Exception as e:
        logger.error(f"浠诲姟 {task_id} 鎵规澶勭悊澶辫触: {str(e)}", exc_info=True)
        try:
            # 灏濊瘯鏇存柊浠诲姟鐘舵€佷负澶辫触
            task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
            task.status = 'failed'
            task.completed_at = timezone.now()
            task.results.update({
                'error': str(e),
                'error_type': type(e).__name__,
                'failed_at': timezone.now().isoformat(),
                'status': 'failed'
            })
            task.save()
        except DataExtractionTask.DoesNotExist:  # type: ignore
            logger.error("Task %s no longer exists, failed status cannot be saved", task_id)
        except Exception as save_error:
            logger.error("Task %s failed while saving failed status: %s", task_id, save_error)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def pause_extraction_task(request, task_id=None):
    """Pause an extraction task."""
    try:
        task_id = _resolve_task_id_from_request(request, task_id)
        task = None
        try:
            task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
        except DataExtractionTask.DoesNotExist:  # type: ignore
            logger.warning(
                "Pause requested for task %s, but no database record was found; trying the thread manager directly",
                task_id,
            )

        if task and task.status != 'running':
            return Response({
                'success': False,
                'error': f'Task status is {task.status} and cannot be paused'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not thread_manager.pause_thread(task_id):
            return Response({
                'success': False,
                'error': 'Task thread not found or already finished'
            }, status=status.HTTP_404_NOT_FOUND)

        if task:
            task.status = 'paused'
            task.save(update_fields=['status'])

        task_status_manager.update_task_status(
            task_id=task_id,
            status='paused',
            progress_data={}
        )

        logger.info("Task %s paused", task_id)

        return Response({
            'success': True,
            'message': 'Task paused successfully'
        })
    except DataExtractionTask.DoesNotExist:  # type: ignore
        if thread_manager.stop_thread(task_id, save_progress=True):
            task_status_manager.update_task_status(
                task_id=task_id,
                status='cancelled',
                progress_data={}
            )
            return Response({
                'success': True,
                'message': 'Task stopped successfully'
            })
        return Response({
            'success': False,
            'error': 'request failed',
        }, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error("Pause task failed: %s", e)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




























































# Legacy sync/admin endpoints retained for manual import only.
# These functions are intentionally not routed from pdf_processor.urls.
@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def legacy_sync_extraction_to_meteorite(request):
    """鍚屾鎻愬彇缁撴灉鍒伴櫒鐭虫暟鎹簱"""
    try:
        data = json.loads(request.body)
        extraction_id = data.get('extraction_id')
        
        if not extraction_id:
            return Response({
                'success': False,
                'error': 'extraction_id涓嶈兘涓虹┖'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 瀵煎叆鏁版嵁鍚屾鏈嶅姟
        from .services.data_sync_service import DataSyncService
        
        # 鍒涘缓鏈嶅姟瀹炰緥骞舵墽琛屽悓姝?        sync_service = DataSyncService()
        meteorite = sync_service.sync_extraction_to_meteorite(extraction_id)
        
        if meteorite:
            return Response({
                'success': True,
                'data': {
                    'meteorite_id': str(meteorite.pk),
                    'meteorite_name': meteorite.name,
                    'classification': meteorite.classification,
                    'message': f'鎴愬姛鍚屾闄ㄧ煶鏁版嵁: {meteorite.name}'
                }
            })
        else:
            return Response({
                'success': False,
                'error': '鍚屾澶辫触锛氭彁鍙栫粨鏋滀笉鍖呭惈鏈夋晥闄ㄧ煶鏁版嵁'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"鍚屾鎻愬彇缁撴灉澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'鍚屾澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def legacy_sync_batch_extractions(request):
    """鎵归噺鍚屾鎻愬彇缁撴灉"""
    try:
        data = json.loads(request.body)
        extraction_ids = data.get('extraction_ids', [])
        
        if not extraction_ids:
            return Response({
                'success': False,
                'error': 'extraction_ids涓嶈兘涓虹┖'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 瀵煎叆鏁版嵁鍚屾鏈嶅姟
        from .services.data_sync_service import DataSyncService
        
        # 鍒涘缓鏈嶅姟瀹炰緥骞舵墽琛屾壒閲忓悓姝?        sync_service = DataSyncService()
        results = sync_service.sync_batch_extractions(extraction_ids)
        
        return Response({
            'success': True,
            'data': results
        })
            
    except Exception as e:
        logger.error(f"鎵归噺鍚屾澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'鎵归噺鍚屾澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def legacy_sync_recent_extractions(request):
    """鍚屾鏈€杩戠殑鎻愬彇缁撴灉"""
    try:
        data = json.loads(request.body)
        hours = int(data.get('hours', 24))  # 榛樿鏈€杩?4灏忔椂
        
        # 瀵煎叆鏁版嵁鍚屾鏈嶅姟
        from .services.data_sync_service import DataSyncService
        
        # 鍒涘缓鏈嶅姟瀹炰緥骞舵墽琛屽悓姝?        sync_service = DataSyncService()
        results = sync_service.sync_recent_extractions(hours)
        
        return Response({
            'success': True,
            'data': results
        })
            
    except Exception as e:
        logger.error(f"鍚屾鏈€杩戞彁鍙栫粨鏋滃け璐? {str(e)}")
        return Response({
            'success': False,
            'error': f'鍚屾澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def legacy_get_sync_statistics(request):
    """鑾峰彇鍚屾缁熻淇℃伅"""
    try:
        # 瀵煎叆鏁版嵁鍚屾鏈嶅姟
        from .services.data_sync_service import DataSyncService
        
        # 鍒涘缓鏈嶅姟瀹炰緥骞惰幏鍙栫粺璁?        sync_service = DataSyncService()
        statistics = sync_service.get_sync_statistics()
        
        return Response({
            'success': True,
            'data': statistics
        })
            
    except Exception as e:
        logger.error(f"鑾峰彇鍚屾缁熻澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'鑾峰彇缁熻澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def legacy_cleanup_duplicate_meteorites(request):
    """Clean up duplicate meteorite records."""
    try:
        # 瀵煎叆鏁版嵁鍚屾鏈嶅姟
        from .services.data_sync_service import DataSyncService
        
        # 鍒涘缓鏈嶅姟瀹炰緥骞舵墽琛屾竻鐞?        sync_service = DataSyncService()
        results = sync_service.cleanup_duplicate_meteorites()
        
        return Response({
            'success': True,
            'data': results
        })
            
    except Exception as e:
        logger.error(f"娓呯悊閲嶅闄ㄧ煶璁板綍澶辫触: {str(e)}")
        return Response({
            'success': False,
            'error': f'娓呯悊澶辫触: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def resume_extraction_task(request, task_id=None):
    """Resume an extraction task."""
    try:
        task_id = _resolve_task_id_from_request(request, task_id)
        task = None
        try:
            task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
        except DataExtractionTask.DoesNotExist:  # type: ignore
            logger.warning(
                "Resume requested for task %s, but no database record was found; trying the thread manager directly",
                task_id,
            )

        if task and task.status != 'paused':
            return Response({
                'success': False,
                'error': f'Task status is {task.status} and cannot be resumed'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not thread_manager.resume_thread(task_id):
            return Response({
                'success': False,
                'error': 'Task thread not found or already finished'
            }, status=status.HTTP_404_NOT_FOUND)

        if task:
            task.status = 'running'
            task.save(update_fields=['status'])

        task_status_manager.update_task_status(
            task_id=task_id,
            status='running',
            progress_data={}
        )

        logger.info("Task %s resumed", task_id)

        return Response({
            'success': True,
            'message': 'Task resumed successfully'
        })

    except DataExtractionTask.DoesNotExist:  # type: ignore
        return Response({
            'success': False,
            'error': 'request failed',
        }, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error("Resume task failed: %s", e)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def stop_extraction_task(request, task_id=None):
    """Stop an extraction task."""
    try:
        task_id = _resolve_task_id_from_request(request, task_id)
        task = None
        try:
            task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
        except DataExtractionTask.DoesNotExist:  # type: ignore
            logger.warning(
                "Stop requested for task %s, but no database record was found; trying the thread manager directly",
                task_id,
            )

        if task and task.status not in ['running', 'paused']:
            return Response({
                'success': False,
                'error': f'Task status is {task.status} and cannot be stopped'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not thread_manager.stop_thread(task_id, save_progress=True):
            return Response({
                'success': False,
                'error': 'Task thread not found or already finished'
            }, status=status.HTTP_404_NOT_FOUND)

        wait_deadline = time.monotonic() + 1.5
        while thread_manager.is_running(task_id) and time.monotonic() < wait_deadline:
            time.sleep(0.1)

        thread_running = thread_manager.is_running(task_id)
        status_text = 'stopping' if thread_running else 'stopped'

        if task:
            task.status = 'cancelled'
            task.completed_at = timezone.now()
            task.save(update_fields=['status', 'completed_at'])

        task_status_manager.update_task_status(
            task_id=task_id,
            status='cancelled',
            progress_data={
                'status_text': status_text,
                'stop_signaled': True,
                'thread_running': thread_running,
            }
        )

        if thread_running:
            logger.info("Task %s stop signaled; thread is still shutting down", task_id)
            return Response({
                'success': True,
                'message': 'Stop signal sent; task is stopping',
                'stop_signaled': True,
                'thread_running': True,
                'status_text': 'stopping',
            })

        logger.info("Task %s stopped", task_id)

        return Response({
            'success': True,
            'message': 'Task stopped successfully',
            'stop_signaled': True,
            'thread_running': False,
            'status_text': 'stopped',
        })

    except DataExtractionTask.DoesNotExist:  # type: ignore
        return Response({
            'success': False,
            'error': 'request failed',
        }, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error("Stop task failed: %s", e)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # 涓存椂鏀逛负AllowAny鐢ㄤ簬娴嬭瘯
def get_task_status(request, task_id=None):
    """Get extraction task status."""
    try:
        task_id = _resolve_task_id_from_request(request, task_id)
        try:
            task = DataExtractionTask.objects.get(task_id=task_id)  # type: ignore
        except DataExtractionTask.DoesNotExist:  # type: ignore
            return Response({
                'success': False,
                'error': 'request failed',
            }, status=status.HTTP_404_NOT_FOUND)

        # Retrieve task status information from the status manager.
        status_info = task_status_manager.get_task_status(task_id)
        
        response_data = {
            'task_id': task.task_id,
            'task_type': task.task_type,
            'status': task.status,
            'created_at': task.created_at,
            'started_at': task.started_at,
            'completed_at': task.completed_at,
            'total_documents': task.total_documents,
            'processed_documents': task.processed_documents,
            'successful_extractions': task.successful_extractions,
            'failed_extractions': task.failed_extractions,
            'progress_percentage': task.get_progress_percentage(),
            'parameters': task.parameters,
            'results': task.results
        }
        
        # Include status-manager details when available.
        if status_info:
            response_data['status_info'] = status_info

        return Response({
            'success': True,
            'data': response_data
        })
        
    except ValueError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error("Get task status failed: %s", e)
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

