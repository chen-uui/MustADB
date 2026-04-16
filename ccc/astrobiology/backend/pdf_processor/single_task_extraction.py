"""Single task extraction manager for new frontend flow."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from django.utils import timezone
from django.db import transaction

from .rag_meteorite_extractor import RAGMeteoriteExtractor

logger = logging.getLogger(__name__)

# 延迟导入数据库模型，避免循环依赖
_database_session_model = None
def _get_database_session_model():
    """延迟加载数据库会话模型"""
    global _database_session_model
    if _database_session_model is None:
        try:
            from meteorite_search.models import SingleTaskExtractionSession
            _database_session_model = SingleTaskExtractionSession
        except ImportError:
            logger.warning("无法导入SingleTaskExtractionSession模型")
            _database_session_model = False
    return _database_session_model

# 延迟导入审核系统，避免循环依赖
_review_system = None
def _get_review_system():
    """延迟加载审核系统"""
    global _review_system
    if _review_system is None:
        try:
            from meteorite_search.review_system_v2 import new_review_system
            _review_system = new_review_system
        except ImportError:
            logger.warning("无法导入审核系统，将跳过自动保存到待审核表")
            _review_system = False  # 标记为不可用，避免重复尝试
    return _review_system


@dataclass
class SegmentMeta:
    id: str
    document_id: str
    chunk_index: int
    title: str
    score: float
    page: Optional[int]
    content: str
    highlight: Optional[str] = None
    authors: List[str] = field(default_factory=list)


@dataclass
class QueueItem:
    segment: SegmentMeta
    status: str = "queued"  # queued | running | success | failed | cancelled
    attempts: int = 0
    error: Optional[str] = None
    result: Optional[Dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class AggregatedResult:
    entity_id: str
    entity_label: str
    fields: Dict
    segments: List[Dict]
    updated_at: str
    pending_id: Optional[int] = None  # 保存到待审核表后的ID，用于去重


@dataclass
class SingleTaskSession:
    id: str
    keywords: List[str]
    threshold: float
    sort_by: str
    created_at: str = field(default_factory=lambda: timezone.now().isoformat())
    status: str = "searching"  # searching | ready | running | completed | cancelled
    segments: Dict[str, SegmentMeta] = field(default_factory=dict)
    segment_order: List[str] = field(default_factory=list)
    queue: Dict[str, QueueItem] = field(default_factory=dict)
    aggregated: Dict[str, AggregatedResult] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: timezone.now().isoformat())
    worker: Optional[threading.Thread] = None
    stop_event: threading.Event = field(default_factory=threading.Event)


class SingleTaskExtractionManager:
    """Thread-safe manager orchestrating single-task extraction lifecycle."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: Dict[str, SingleTaskSession] = {}  # 支持多个session
        self._extractor = RAGMeteoriteExtractor()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    def start_search(self, keywords: List[str], threshold: float, sort_by: str) -> SingleTaskSession:
        keywords = [kw.strip() for kw in keywords if kw and kw.strip()]
        joined_query = " ".join(keywords)
        if not joined_query:
            raise ValueError("关键词不能为空")

        with self._lock:
            # 允许创建新session，不再限制只有一个
            session_id = uuid.uuid4().hex
            session = SingleTaskSession(
                id=session_id,
                keywords=keywords,
                threshold=threshold,
                sort_by=sort_by,
                status="searching",
            )
            self._sessions[session_id] = session

        segments = self._search_segments(joined_query, threshold, sort_by)

        with self._lock:
            # 检查session是否仍然存在（可能在搜索过程中被清理）
            if session_id not in self._sessions:
                raise RuntimeError("任务已被清理，请重新发起检索")
            session = self._sessions[session_id]

            for seg in segments:
                session.segments[seg.id] = seg
            session.segment_order = [seg.id for seg in segments]
            session.status = "ready"
            session.last_updated = timezone.now().isoformat()
            
            # 保存到数据库
            self._save_session_to_db(session)

            return session

    def get_session(self, session_id: str) -> Optional[SingleTaskSession]:
        with self._lock:
            # 先查内存
            if session_id in self._sessions:
                return self._sessions[session_id]
            
            # 内存中没有，尝试从数据库加载
            try:
                db_session = self._load_session_from_db(session_id)
                if db_session:
                    self._sessions[session_id] = db_session
                    return db_session
            except Exception as e:
                logger.warning(f"从数据库加载session失败: {e}")
            
            return None

    def cancel_session(self, session_id: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            # 如果内存中没有，尝试从数据库加载
            if not session:
                try:
                    session = self._load_session_from_db(session_id)
                    if session:
                        self._sessions[session_id] = session
                    else:
                        raise RuntimeError("任务不存在或已结束")
                except Exception as e:
                    logger.warning(f"从数据库加载session失败: {e}")
                    raise RuntimeError("任务不存在或已结束")

            session.stop_event.set()
            for item in session.queue.values():
                if item.status in {"queued", "running"}:
                    item.status = "cancelled"
                    item.error = "任务已取消"
            session.status = "cancelled"
            session.last_updated = timezone.now().isoformat()
            
            # 保存到数据库
            self._save_session_to_db(session)

    # ------------------------------------------------------------------
    # Queue operations
    # ------------------------------------------------------------------
    def enqueue_segments(self, session_id: str, segment_ids: List[str]) -> SingleTaskSession:
        if not segment_ids:
            raise ValueError("缺少片段ID")

        with self._lock:
            session = self._sessions.get(session_id)
            # 如果内存中没有，尝试从数据库加载
            if not session:
                try:
                    session = self._load_session_from_db(session_id)
                    if session:
                        self._sessions[session_id] = session
                    else:
                        raise RuntimeError("任务不存在，请重新检索")
                except Exception as e:
                    logger.warning(f"从数据库加载session失败: {e}")
                    raise RuntimeError("任务不存在，请重新检索")

            for seg_id in segment_ids:
                if seg_id not in session.segments:
                    raise ValueError(f"片段 {seg_id} 不存在或已过期")
                if seg_id not in session.queue:
                    session.queue[seg_id] = QueueItem(segment=session.segments[seg_id])
                else:
                    item = session.queue[seg_id]
                    item.status = "queued"
                    item.error = None
            logger.info("[single-task] 入队片段 %s 个 (session=%s)", len(segment_ids), session.id)
            session.status = "running"
            session.last_updated = timezone.now().isoformat()
            
            # 保存到数据库
            self._save_session_to_db(session)

            if not session.worker or not session.worker.is_alive():
                session.stop_event.clear()
                session.worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"single-task-{session.id}",
                    args=(session,),
                    daemon=True,
                )
                session.worker.start()

            return session

    def retry_segment(self, session_id: str, segment_id: str) -> SingleTaskSession:
        return self.enqueue_segments(session_id, [segment_id])

    # ------------------------------------------------------------------
    # Status formatting
    # ------------------------------------------------------------------
    def serialize_session(self, session: SingleTaskSession) -> Dict:
        # 计算已处理的片段ID（已成功完成的）
        processed_segment_ids = {
            item.segment.id for item in session.queue.values() 
            if item.status == "success"
        }
        
        # 计算未处理的片段ID
        unprocessed_segment_ids = [
            seg_id for seg_id in session.segment_order 
            if seg_id not in processed_segment_ids
        ]
        
        return {
            "sessionId": session.id,
            "status": session.status,
            "keywords": session.keywords,
            "threshold": session.threshold,
            "startedAt": session.created_at,
            "lastUpdated": session.last_updated,
            "totalSegments": len(session.segment_order),
            "allSegmentIds": session.segment_order,  # 包含所有片段ID，用于全选功能
            "unprocessedSegmentIds": unprocessed_segment_ids,  # 未处理的片段ID，用于选择剩余片段
            "processedSegmentIds": list(processed_segment_ids),  # 已处理的片段ID
            "queue": [
                {
                    "id": item.segment.id,
                    "status": item.status,
                    "attempts": item.attempts,
                    "error": item.error,
                    "result": item.result,
                    "startedAt": item.started_at,
                    "completedAt": item.completed_at,
                    "score": item.segment.score,
                    "title": item.segment.title,
                    "documentId": item.segment.document_id,
                    "chunkIndex": item.segment.chunk_index,
                    "content": item.segment.content,
                }
                for item in session.queue.values()
            ],
            "aggregatedResults": [
                {
                    "entityId": agg.entity_id,
                    "label": agg.entity_label,
                    "fields": agg.fields,
                    "segments": agg.segments,
                    "updatedAt": agg.updated_at,
                }
                for agg in session.aggregated.values()
            ],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _search_segments(self, query: str, threshold: float, sort_by: str) -> List[SegmentMeta]:
        if not self._extractor.initialize_services():
            raise RuntimeError("初始化提取服务失败")

        # 设置较大的上限以获取所有相关片段（实际检索时 hybrid_search 会先获取更多候选，rerank 后再截断）
        # 这里设置10000作为上限，实际返回数量取决于 reranker 的输出
        raw_segments = self._extractor._search_meteorite_segments_optimized(query, max_segments=10000)  # type: ignore[attr-defined]

        scores = [float(seg.get("score", 0.0) or 0.0) for seg in raw_segments]
        if scores:
            top_scores = sorted(scores, reverse=True)[:5]
            min_score = min(scores)
            max_score = max(scores)
            avg_score = sum(scores) / len(scores)
            logger.info(
                "[single-task] 原始片段统计 count=%s max=%.4f min=%.4f avg=%.4f top5=%s",
                len(scores),
                max_score,
                min_score,
                avg_score,
                [round(s, 4) for s in top_scores],
            )
        else:
            logger.warning("[single-task] 原始片段为空，无法进行排序")

        segments = []
        for raw in raw_segments:
            score = float(raw.get("score", 0.0) or 0.0)
            segment_id = self._build_segment_id(raw)
            segments.append(
                SegmentMeta(
                    id=segment_id,
                    document_id=str(raw.get("document_id", "")),
                    chunk_index=int(raw.get("chunk_index") or 0),
                    title=str(raw.get("title") or "未知文档"),
                    score=score,
                    page=raw.get("page") or raw.get("page_number"),
                    content=str(raw.get("content", "")),
                    highlight=query,
                )
            )

        # 保守的阈值过滤：只过滤掉明显不相关的片段
        # 注意：搜索分数反映的是相关性，不是数据存在性。
        # 低分片段也可能包含陨石数据，所以只过滤掉分数极低的片段，保留更多候选。
        if scores and len(segments) > 0:
            sorted_scores = sorted(scores, reverse=True)
            
            # 策略：只过滤掉明显不相关的片段
            # 注意：搜索分数反映相关性，不是数据存在性。低分片段也可能包含陨石数据。
            # 我们采用非常保守的策略：只过滤掉分数明显低于平均分的片段
            
            # 如果分数分布很集中（最低分接近平均分），说明大部分片段都有一定相关性，不过滤
            score_range = max_score - min(scores) if scores else 1.0
            score_std = (sum((s - avg_score) ** 2 for s in scores) / len(scores)) ** 0.5 if scores and len(scores) > 1 else 0
            
            # 如果分数分布很分散（标准差大），可以过滤掉明显低于平均分的片段
            # 如果分数分布很集中，说明大部分片段都有一定相关性，保留所有
            if score_std > avg_score * 0.5:  # 标准差较大，说明有很低的分数
                # 过滤掉分数 < 平均分 - 1.5倍标准差 的片段（明显低于平均水平的）
                final_threshold = avg_score - 1.5 * score_std
                # 但不低于绝对最小值（0.06）和最低分的90%
                final_threshold = max(final_threshold, 0.06, min(scores) * 0.9 if scores else 0.06)
                threshold_source = "std_based"
            else:
                # 分数分布集中，保留所有片段
                final_threshold = min(scores) - 0.01 if scores else 0.0  # 只过滤掉理论上的异常值
                threshold_source = "keep_all"
            
            # 安全上限：不超过最高分的50%
            final_threshold = min(final_threshold, max_score * 0.5)
            
            filtered_segments = [s for s in segments if s.score >= final_threshold]
            filtered_count = len(segments) - len(filtered_segments)
            
            logger.info(
                "[single-task] 智能阈值过滤 原始=%s 过滤后=%s (阈值=%.4f, %s, 过滤掉=%s, 保留率=%.1f%%)",
                len(segments),
                len(filtered_segments),
                final_threshold,
                threshold_source,
                filtered_count,
                (len(filtered_segments) / len(segments)) * 100 if segments else 0
            )
            logger.info(
                "[single-task] 分数分布: 最高=%.4f 平均=%.4f 最低=%.4f 标准差=%.4f",
                max_score,
                avg_score,
                min(scores) if scores else 0,
                score_std
            )
            segments = filtered_segments
        else:
            logger.warning("[single-task] 无分数数据，跳过阈值过滤")

        if sort_by == "score_asc":
            segments.sort(key=lambda s: s.score)
        elif sort_by == "page_asc":
            segments.sort(key=lambda s: (s.page or 0, -s.score))
        else:
            segments.sort(key=lambda s: s.score, reverse=True)

        return segments

    def get_segments_page(self, session: SingleTaskSession, page: int, page_size: int) -> List[SegmentMeta]:
        if page < 1:
            page = 1
        if page_size <= 0:
            page_size = 50

        with self._lock:
            start = (page - 1) * page_size
            end = start + page_size
            ordered_ids = session.segment_order[start:end]
            return [session.segments[sid] for sid in ordered_ids if sid in session.segments]

    def _worker_loop(self, session: SingleTaskSession) -> None:
        while not session.stop_event.is_set():
            next_item = self._next_queue_item(session)
            if not next_item:
                break

            next_item.status = "running"
            next_item.started_at = timezone.now().isoformat()
            next_item.attempts += 1
            logger.info(
                "[single-task] 开始抽取 segment=%s attempt=%s session=%s",
                next_item.segment.id,
                next_item.attempts,
                session.id,
            )

            try:
                # 在执行LLM提取前再次检查取消信号
                if session.stop_event.is_set():
                    logger.info("[single-task] 任务已取消，停止提取 session=%s", session.id)
                    next_item.status = "cancelled"
                    next_item.error = "任务已取消"
                    break
                
                result = self._extractor.extract_from_segment(
                    {
                        "content": next_item.segment.content,
                        "document_id": next_item.segment.document_id,
                        "chunk_index": next_item.segment.chunk_index,
                        "title": next_item.segment.title,
                    },
                    {},
                )
                
                # 提取后立即检查取消信号
                if session.stop_event.is_set():
                    logger.info("[single-task] 任务已取消，停止处理结果 session=%s", session.id)
                    next_item.status = "cancelled"
                    next_item.error = "任务已取消"
                    break

                if result.get("success"):
                    next_item.status = "success"
                    next_item.result = self._format_success_result(session, next_item, result)
                    logger.info("[single-task] 抽取成功 segment=%s", next_item.segment.id)
                else:
                    # 对于某些错误（如JSON解析失败、超时），可以考虑重试
                    error_msg = result.get("error", "提取失败")
                    error_type = result.get("error_type", "")
                    
                    # 对于可重试的错误类型（JSON解析失败、超时），且尝试次数小于2时重试
                    if next_item.attempts < 2 and error_type in ("json_parse", "timeout"):
                        logger.info(
                            "[single-task] %s，将重试 segment=%s attempt=%s",
                            error_msg[:50],
                            next_item.segment.id,
                            next_item.attempts,
                        )
                        # 重置状态以重新入队
                        next_item.status = "queued"
                        next_item.started_at = None
                        continue
                    
                    next_item.status = "failed"
                    next_item.error = error_msg
                    logger.warning(
                        "[single-task] 抽取失败 segment=%s error=%s attempt=%s",
                        next_item.segment.id,
                        next_item.error,
                        next_item.attempts,
                    )
            except Exception as e:
                logger.error(
                    "[single-task] 抽取异常 segment=%s error=%s",
                    next_item.segment.id,
                    str(e),
                    exc_info=True,
                )
                next_item.status = "failed"
                next_item.error = f"提取异常: {str(e)}"

            next_item.completed_at = timezone.now().isoformat()

            with self._lock:
                session.last_updated = timezone.now().isoformat()
                
                # 每处理5个片段保存一次到数据库
                processed_count = sum(1 for item in session.queue.values() 
                                     if item.status in {"success", "failed", "cancelled"})
                if processed_count % 5 == 0:
                    self._save_session_to_db(session)

        with self._lock:
            if session.stop_event.is_set():
                session.status = "cancelled"
                logger.info("[single-task] 任务已取消 session=%s", session.id)
            else:
                pending = any(item.status in {"queued", "running"} for item in session.queue.values())
                session.status = "completed" if not pending else "running"
                logger.info(
                    "[single-task] 任务状态更新 session=%s status=%s",
                    session.id,
                    session.status,
                )
            session.last_updated = timezone.now().isoformat()
            
            # 任务结束或状态变更时保存到数据库
            self._save_session_to_db(session)

    def _next_queue_item(self, session: SingleTaskSession) -> Optional[QueueItem]:
        with self._lock:
            for item in session.queue.values():
                if item.status == "queued":
                    return item
        return None

    def _format_success_result(self, session: SingleTaskSession, item: QueueItem, result: Dict) -> Dict:
        payload = result.get("data") or {}
        entity_label = self._resolve_entity_label(payload, item)
        entity_id = self._resolve_entity_id(payload, item)

        segment_entry = {
            "id": item.segment.id,
            "score": item.segment.score,
            "documentId": item.segment.document_id,
            "chunkIndex": item.segment.chunk_index,
            "content": item.segment.content,
        }

        with self._lock:
            agg = session.aggregated.get(entity_id)
            is_new_entity = False
            if not agg:
                is_new_entity = True
                agg = AggregatedResult(
                    entity_id=entity_id,
                    entity_label=entity_label,
                    fields=payload,
                    segments=[segment_entry],
                    updated_at=timezone.now().isoformat(),
                )
                session.aggregated[entity_id] = agg
            else:
                agg.fields = payload
                agg.segments.append(segment_entry)
                agg.updated_at = timezone.now().isoformat()
            
            # 自动保存到待审核表（仅在首次创建新实体时，避免重复提交）
            if is_new_entity:
                self._save_to_pending_review(agg, session)

        return {
            "entityId": entity_id,
            "entityLabel": entity_label,
            "fields": payload,
            "updatedAt": timezone.now().isoformat(),
        }

    @staticmethod
    def _resolve_entity_label(payload: Dict, item: QueueItem) -> str:
        for key in ("meteorite_name", "name", "designation", "title"):
            value = payload.get(key)
            if value:
                return str(value)
        return item.segment.title or item.segment.id

    @staticmethod
    def _resolve_entity_id(payload: Dict, item: QueueItem) -> str:
        for key in ("meteorite_id", "meteorite_name", "name", "designation"):
            value = payload.get(key)
            if value:
                return str(value)
        return item.segment.id

    @staticmethod
    def _build_segment_id(raw: Dict) -> str:
        document_id = str(raw.get("document_id", ""))
        chunk_index = raw.get("chunk_index")
        if document_id and chunk_index is not None:
            return f"{document_id}:{chunk_index}"
        return uuid.uuid4().hex

    @staticmethod
    def _build_evidence_snippet(content: Optional[str], max_chars: int = 280) -> str:
        text = " ".join(str(content or "").split())
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 3].rstrip() + "..."

    def _build_review_evidence_context(
        self, agg: AggregatedResult, session: SingleTaskSession
    ) -> Dict[str, object]:
        evidence_segment_ids: List[str] = []
        evidence_snippets: List[str] = []
        evidence_title = ""
        source_document_id = ""

        for seg in agg.segments[:3]:
            segment_id = str(seg.get("id") or "").strip()
            if segment_id:
                evidence_segment_ids.append(segment_id)

            if not source_document_id:
                source_document_id = str(seg.get("documentId") or "").strip()

            if segment_id and not evidence_title:
                segment_meta = session.segments.get(segment_id)
                if segment_meta and segment_meta.title:
                    evidence_title = str(segment_meta.title).strip()

            snippet = self._build_evidence_snippet(seg.get("content"))
            if snippet:
                evidence_snippets.append(snippet)

        return {
            "source_document_id": source_document_id,
            "evidence_title": evidence_title,
            "evidence_segment_ids": evidence_segment_ids[:5],
            "evidence_snippets": evidence_snippets[:2],
        }

    def _save_to_pending_review(self, agg: AggregatedResult, session: SingleTaskSession) -> None:
        """将聚合结果保存到待审核表"""
        try:
            review_system = _get_review_system()
            if not review_system:
                return  # 审核系统不可用，跳过
            
            # 转换字段格式为审核系统需要的格式
            fields = agg.fields or {}
            
            # 计算置信度分数（基于片段数量和平均得分）
            segment_scores = [seg.get("score", 0.0) for seg in agg.segments if isinstance(seg.get("score"), (int, float))]
            avg_score = sum(segment_scores) / len(segment_scores) if segment_scores else 0.0
            # 片段数量越多，置信度越高（最高0.9，避免过度自信）
            confidence_bonus = min(0.2, len(agg.segments) * 0.02)
            confidence_score = min(0.9, avg_score + confidence_bonus)
            evidence_context = self._build_review_evidence_context(agg, session)
            
            # 准备提交数据
            submission_data = {
                "name": fields.get("name") or fields.get("meteorite_name") or agg.entity_label or "Unknown",
                "classification": fields.get("classification") or fields.get("type") or "Unknown",
                "discovery_location": fields.get("discovery_location") or fields.get("location") or "Unknown",
                "origin": fields.get("origin") or fields.get("source") or "Unknown",
                "organic_compounds": fields.get("organic_compounds") or [],
                "contamination_exclusion_method": fields.get("contamination_exclusion_method") or fields.get("contamination_exclusion") or "Not specified",
                "references": fields.get("references") or [],
                "confidence_score": confidence_score,
                "extraction_source": "pdf",  # 使用'pdf'作为来源，因为是从PDF文档中提取的
                "extraction_metadata": {
                    "session_id": session.id,
                    "keywords": session.keywords,
                    "entity_id": agg.entity_id,
                    "segment_count": len(agg.segments),
                    "segment_ids": [seg.get("id") for seg in agg.segments[:10]],  # 只保存前10个片段ID
                    "extraction_time": agg.updated_at,
                    "extraction_mode": "single_task",  # 标记为单任务提取模式
                    **evidence_context,
                }
            }
            
            # 提交到待审核表
            result = review_system.submit_for_review(submission_data, submitter=None)
            
            if result.get("success"):
                agg.pending_id = result.get("pending_id")
                logger.info(
                    "[single-task] 聚合结果已保存到待审核表 entity_id=%s pending_id=%s name=%s",
                    agg.entity_id,
                    agg.pending_id,
                    submission_data["name"]
                )
            else:
                logger.warning(
                    "[single-task] 保存到待审核表失败 entity_id=%s error=%s",
                    agg.entity_id,
                    result.get("error", "未知错误")
                )
                
        except Exception as e:
            # 保存失败不应影响提取流程，只记录日志
            logger.exception(
                "[single-task] 保存聚合结果到待审核表时发生异常 entity_id=%s: %s",
                agg.entity_id,
                e
            )
    
    def _load_session_from_db(self, session_id: str) -> Optional[SingleTaskSession]:
        """从数据库加载session"""
        SessionModel = _get_database_session_model()
        if not SessionModel:
            return None
        
        try:
            db_session = SessionModel.objects.get(session_id=session_id)
            
            # 反序列化segment数据
            segments = {}
            segments_data = db_session.segments_data or {}
            for seg_id, seg_data in segments_data.items():
                segments[seg_id] = SegmentMeta(**seg_data)
            
            # 反序列化queue数据
            queue = {}
            queue_data = db_session.queue_data or {}
            for seg_id, queue_item_data in queue_data.items():
                # 重建SegmentMeta
                seg_meta = segments.get(queue_item_data['segment']['id'])
                if seg_meta:
                    queue[seg_id] = QueueItem(
                        segment=seg_meta,
                        status=queue_item_data.get('status', 'queued'),
                        attempts=queue_item_data.get('attempts', 0),
                        error=queue_item_data.get('error'),
                        result=queue_item_data.get('result'),
                        started_at=queue_item_data.get('started_at'),
                        completed_at=queue_item_data.get('completed_at'),
                    )
            
            # 反序列化aggregated结果
            aggregated = {}
            for agg_data in (db_session.aggregated_results or {}).values():
                aggregated[agg_data['entity_id']] = AggregatedResult(**agg_data)
            
            # 重建SingleTaskSession
            session = SingleTaskSession(
                id=db_session.session_id,
                keywords=db_session.keywords,
                threshold=db_session.threshold,
                sort_by=db_session.sort_by,
                created_at=db_session.created_at.isoformat(),
                status=db_session.status,
                segments=segments,
                segment_order=db_session.segment_order,
                queue=queue,
                aggregated=aggregated,
                last_updated=db_session.last_updated.isoformat(),
            )
            
            logger.info(f"从数据库恢复session: {session_id}, status={session.status}")
            return session
            
        except SessionModel.DoesNotExist:
            logger.debug(f"数据库中没有找到session: {session_id}")
            return None
        except Exception as e:
            logger.error(f"从数据库加载session失败: {e}", exc_info=True)
            return None
    
    def _save_session_to_db(self, session: SingleTaskSession) -> bool:
        """保存session到数据库"""
        SessionModel = _get_database_session_model()
        if not SessionModel:
            return False
        
        try:
            # 序列化segments
            segments_data = {}
            for seg_id, seg in session.segments.items():
                segments_data[seg_id] = {
                    'id': seg.id,
                    'document_id': seg.document_id,
                    'chunk_index': seg.chunk_index,
                    'title': seg.title,
                    'score': seg.score,
                    'page': seg.page,
                    'content': seg.content,
                    'highlight': seg.highlight,
                    'authors': seg.authors,
                }
            
            # 序列化queue
            queue_data = {}
            for seg_id, item in session.queue.items():
                queue_data[seg_id] = {
                    'segment': {
                        'id': item.segment.id,
                    },
                    'status': item.status,
                    'attempts': item.attempts,
                    'error': item.error,
                    'result': item.result,
                    'started_at': item.started_at,
                    'completed_at': item.completed_at,
                }
            
            # 序列化aggregated
            aggregated_data = {}
            for agg in session.aggregated.values():
                aggregated_data[agg.entity_id] = {
                    'entity_id': agg.entity_id,
                    'entity_label': agg.entity_label,
                    'fields': agg.fields,
                    'segments': agg.segments,
                    'updated_at': agg.updated_at,
                    'pending_id': agg.pending_id,
                }
            
            # 更新或创建数据库记录
            SessionModel.objects.update_or_create(
                session_id=session.id,
                defaults={
                    'keywords': session.keywords,
                    'threshold': session.threshold,
                    'sort_by': session.sort_by,
                    'status': session.status,
                    'segments_data': segments_data,
                    'segment_order': session.segment_order,
                    'queue_data': queue_data,
                    'aggregated_results': aggregated_data,
                }
            )
            
            logger.debug(f"保存session到数据库: {session.id}")
            return True
            
        except Exception as e:
            logger.error(f"保存session到数据库失败: {e}", exc_info=True)
            return False


single_task_manager = SingleTaskExtractionManager()
