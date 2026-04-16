"""
混合搜索服务
结合向量搜索和BM25关键词搜索，提高检索质量
"""
import os
import logging
import time
import weaviate
from typing import Iterable, List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from pdf_processor.rag_service import SearchResult
from pdf_processor.embedding_service import embedding_service
from pdf_processor.weaviate_connection import weaviate_connection
from pdf_processor.bench_logging import init_stage_ms

logger = logging.getLogger(__name__)

@dataclass
class HybridSearchResult:
    """混合搜索结果"""
    content: str
    score: float
    vector_score: float
    bm25_score: float
    metadata: Dict[str, Any]
    document_id: str
    page: int
    title: str
    chunk_index: int = -1

class HybridSearchService:
    """混合搜索服务"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.weaviate_connection = weaviate_connection
        self.collection_name = "PDFDocument"
        self.last_stage_ms = init_stage_ms()
        self.last_search_budget: Dict[str, Any] = {}

    def _get_collection_name(self, collection_name: Optional[str] = None) -> str:
        if collection_name and str(collection_name).strip():
            return str(collection_name).strip()
        return os.getenv("WEAVIATE_COLLECTION_NAME", "").strip() or self.collection_name

    def _normalize_allowed_document_ids(
        self,
        allowed_document_ids: Optional[Iterable[Any]],
    ) -> Optional[Set[str]]:
        if allowed_document_ids is None:
            return None
        normalized = {
            str(document_id)
            for document_id in allowed_document_ids
            if document_id not in (None, "")
        }
        return normalized or set()

    def _build_document_filter(
        self,
        allowed_document_ids: Optional[Iterable[Any]],
    ):
        normalized = self._normalize_allowed_document_ids(allowed_document_ids)
        if normalized is None:
            return None
        if not normalized:
            return None
        return weaviate.classes.query.Filter.any_of(
            [
                weaviate.classes.query.Filter.by_property("document_id").equal(document_id)
                for document_id in sorted(normalized)
            ]
        )
    
    def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3,
        allowed_document_ids: Optional[Iterable[Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[HybridSearchResult]:
        """
        混合搜索：结合向量搜索和BM25关键词搜索
        
        Args:
            query: 搜索查询
            limit: 返回结果数量
            vector_weight: 向量搜索权重
            bm25_weight: BM25搜索权重
            
        Returns:
            混合搜索结果列表
        """
        try:
            self.last_stage_ms = init_stage_ms()
            logger.info(f"[hybrid] START query='{query[:60]}' limit={limit}")
            start_time = time.perf_counter()
            allowed_document_id_set = self._normalize_allowed_document_ids(allowed_document_ids)
            if allowed_document_id_set == set():
                self.last_search_budget = {
                    "requested_limit": limit,
                    "effective_limit": 0,
                    "remaining_docs": 0,
                    "vector_limit": 0,
                    "bm25_limit": 0,
                }
                logger.info("[hybrid] empty allowed_document_ids; skip hybrid search")
                return []
            
            # Weaviate 的最大结果数限制通常是 10000
            # 对于每个子搜索，我们使用 min(limit * 2, 10000) 来避免超过限制
            WEAVIATE_MAX_LIMIT = 10000
            remaining_docs = len(allowed_document_id_set) if allowed_document_id_set is not None else None
            effective_limit = max(1, int(limit))
            if remaining_docs is not None:
                effective_limit = min(effective_limit, max(1, remaining_docs * 3))
            vector_limit = min(limit * 2, WEAVIATE_MAX_LIMIT)
            bm25_limit = min(limit * 2, WEAVIATE_MAX_LIMIT)
            if remaining_docs is not None:
                scoped_budget_cap = max(1, remaining_docs * 3)
                vector_limit = min(vector_limit, scoped_budget_cap)
                bm25_limit = min(bm25_limit, scoped_budget_cap)
            self.last_search_budget = {
                "requested_limit": limit,
                "effective_limit": effective_limit,
                "remaining_docs": remaining_docs,
                "vector_limit": vector_limit,
                "bm25_limit": bm25_limit,
            }
            
            # 1. 向量搜索
            vec_start = time.perf_counter()
            vector_results = self._vector_search(
                query,
                vector_limit,
                allowed_document_ids=allowed_document_id_set,
                collection_name=collection_name,
            )
            vec_elapsed = time.perf_counter() - vec_start
            self.last_stage_ms["dense_search"] = vec_elapsed * 1000.0
            logger.info(
                "[hybrid] STEP1 vector 完成 count=%s elapsed=%.2fs",
                len(vector_results),
                vec_elapsed,
            )
            
            # 2. BM25关键词搜索
            bm_start = time.perf_counter()
            bm25_results = self._bm25_search(
                query,
                bm25_limit,
                allowed_document_ids=allowed_document_id_set,
                collection_name=collection_name,
            )
            bm_elapsed = time.perf_counter() - bm_start
            self.last_stage_ms["sparse_search"] = bm_elapsed * 1000.0
            logger.info(
                "[hybrid] STEP2 bm25 完成 count=%s elapsed=%.2fs",
                len(bm25_results),
                bm_elapsed,
            )
            
            # 3. 合并和重排序结果
            merge_start = time.perf_counter()
            hybrid_results = self._merge_and_rerank(
                vector_results, bm25_results, 
                vector_weight, bm25_weight, effective_limit
            )
            merge_elapsed = time.perf_counter() - merge_start
            self.last_stage_ms["fuse"] = merge_elapsed * 1000.0
            total_elapsed = time.perf_counter() - start_time
            
            logger.info(
                "[hybrid] STEP3 merge 完成 count=%s elapsed=%.2fs total=%.2fs",
                len(hybrid_results),
                merge_elapsed,
                total_elapsed,
            )
            return hybrid_results
            
        except Exception as e:
            logger.error(f"混合搜索失败: {e}")
            # 降级到纯向量搜索
            self.last_stage_ms = init_stage_ms()
            return self._fallback_vector_search(
                query,
                limit,
                allowed_document_ids=allowed_document_ids,
                collection_name=collection_name,
            )
    
    def _vector_search(
        self,
        query: str,
        limit: int,
        max_distance: float = 0.8,
        allowed_document_ids: Optional[Iterable[Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        向量搜索
        
        Args:
            query: 搜索查询
            limit: 返回结果数量
            max_distance: 最大距离阈值（cosine距离），超过此值的片段将被过滤
                         0.0 = 完全相同，0.5 = 相似度50%，1.0 = 完全不相似
        """
        try:
            query_vector = self.embedding_service.encode([query])[0]
            client = self.weaviate_connection.get_client()
            collection = client.collections.get(self._get_collection_name(collection_name))
            allowed_document_id_set = self._normalize_allowed_document_ids(allowed_document_ids)
            if allowed_document_id_set == set():
                logger.info("[hybrid] vector search skip: empty allowed_document_ids")
                return []
            where_filter = self._build_document_filter(allowed_document_id_set)
            if where_filter is not None:
                candidate_limit = min(limit, max(1, len(allowed_document_id_set) * 3))
                min_certainty = 1.0 - max_distance
                try:
                    response = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=candidate_limit,
                        certainty=min_certainty,
                        filters=where_filter,
                        return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
                    )
                except TypeError:
                    try:
                        response = collection.query.near_vector(
                            near_vector=query_vector,
                            limit=candidate_limit,
                            distance=max_distance,
                            filters=where_filter,
                            return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
                        )
                    except TypeError:
                        logger.warning("[hybrid] vector query does not support certainty/distance with filters; retrying with filters-only")
                        response = collection.query.near_vector(
                            near_vector=query_vector,
                            limit=candidate_limit,
                            filters=where_filter,
                            return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
                        )

                results = []
                filtered_count = 0
                for obj in response.objects:
                    distance = obj.metadata.distance if obj.metadata else 1.0
                    if distance > max_distance:
                        filtered_count += 1
                        continue

                    document_id = str(obj.properties.get("document_id", "") or "")
                    if document_id not in allowed_document_id_set:
                        continue

                    results.append(SearchResult(
                        content=obj.properties.get("content", ""),
                        score=1.0 - distance,
                        metadata={
                            "document_id": document_id,
                            "page_number": obj.properties.get("page_number", 0),
                            "distance": distance,
                        },
                        document_id=document_id,
                        page=obj.properties.get("page_number", 0),
                        title=obj.properties.get("title", "") or "Unknown document",
                        chunk_index=obj.properties.get("chunk_index", -1),
                    ))
                    if len(results) >= limit:
                        break

                logger.info(
                    "[hybrid] vector search scoped raw=%s kept=%s allowed_docs=%s filtered=%s",
                    len(response.objects),
                    len(results),
                    len(allowed_document_id_set),
                    filtered_count,
                )
                return results
            
            # 在 Weaviate 查询层面设置距离阈值，这样 Weaviate 本身就不会返回不相关的片段
            # distance 参数表示最大允许的 cosine 距离
            # 对于 cosine 距离：0.0 = 完全相同，0.5 = 相似度50%，1.0 = 完全不相似
            # 设置 max_distance 意味着只返回相似度 >= (1 - max_distance) 的片段
            
            # 增加limit以确保有足够的结果，但 Weaviate 会根据 distance 自动过滤
            candidate_limit = min(limit * 3, 10000)
            
            # Weaviate 的 near_vector 使用 certainty 参数（0-1），表示最小相似度
            # certainty = 1.0 - distance，所以如果我们想要 distance <= 0.5，需要 certainty >= 0.5
            min_certainty = 1.0 - max_distance
            
            try:
                response = collection.query.near_vector(
                    near_vector=query_vector,
                    limit=candidate_limit,
                    certainty=min_certainty,  # 在 Weaviate 层面设置相似度阈值
                    return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
                )
            except TypeError:
                # 如果 certainty 参数不支持，回退到使用 distance 参数
                try:
                    response = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=candidate_limit,
                        distance=max_distance,
                        return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
                    )
                except TypeError:
                    # 如果都不支持，回退到原来的方式（只设置 limit）
                    logger.warning("[hybrid] Weaviate 不支持 distance/certainty 参数，使用 limit 限制")
                    response = collection.query.near_vector(
                        near_vector=query_vector,
                        limit=candidate_limit,
                        return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
                    )
            
            results = []
            filtered_count = 0
            distance_samples = []  # 用于记录距离样本
            
            for obj in response.objects:
                distance = obj.metadata.distance if obj.metadata else 1.0
                distance_samples.append(distance)
                
                # 过滤超过距离阈值的片段（Weaviate API 可能不支持 distance/certainty 参数，
                # 所以需要在代码层面进行过滤）
                if distance > max_distance:
                    filtered_count += 1
                    continue
                
                content = obj.properties.get('content', '')
                title = obj.properties.get('title', '') or '未知文档'
                document_id = obj.properties.get('document_id', '')
                page = obj.properties.get('page_number', 0)
                score = 1.0 - distance  # cosine距离转换为相似度分数
                
                results.append(SearchResult(
                    content=content,
                    score=score,
                    metadata={
                        'document_id': document_id,
                        'page_number': page,
                        'distance': distance
                    },
                    document_id=document_id,
                    page=page,
                    title=title,
                    chunk_index=obj.properties.get('chunk_index', -1)
                ))
                
                # 达到目标数量后停止
                if len(results) >= limit:
                    break
            
            # 记录距离统计信息
            if distance_samples:
                min_dist = min(distance_samples)
                max_dist = max(distance_samples)
                avg_dist = sum(distance_samples) / len(distance_samples)
                logger.info(
                    "[hybrid] 向量搜索距离统计: 最小=%.3f, 最大=%.3f, 平均=%.3f, 阈值=%.2f",
                    min_dist, max_dist, avg_dist, max_distance
                )
            
            logger.info(
                "[hybrid] 向量搜索 候选=%s 过滤后=%s (距离阈值=%.2f, 过滤掉=%s, 过滤率=%.1f%%)",
                len(response.objects),
                len(results),
                max_distance,
                filtered_count,
                (filtered_count / len(response.objects)) * 100 if response.objects else 0
            )
            
            # 如果所有结果都被过滤，记录警告并放宽阈值
            if len(results) == 0 and len(response.objects) > 0:
                logger.warning(
                    "[hybrid] 所有向量搜索结果都被过滤！考虑放宽距离阈值。"
                    "当前阈值=%.2f, 最小距离=%.3f",
                    max_distance,
                    min(distance_samples) if distance_samples else 0
                )
            
            return results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    def _bm25_search(
        self,
        query: str,
        limit: int,
        allowed_document_ids: Optional[Iterable[Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[SearchResult]:
        """BM25关键词搜索"""
        try:
            client = self.weaviate_connection.get_client()
            collection = client.collections.get(self._get_collection_name(collection_name))
            allowed_document_id_set = self._normalize_allowed_document_ids(allowed_document_ids)
            if allowed_document_id_set == set():
                logger.info("[hybrid] bm25 search skip: empty allowed_document_ids")
                return []
            where_filter = self._build_document_filter(allowed_document_id_set)
            if where_filter is not None:
                try:
                    response = collection.query.bm25(
                        query=query,
                        query_properties=["content", "title"],
                        limit=limit,
                        filters=where_filter,
                        return_metadata=weaviate.classes.query.MetadataQuery(score=True)
                    )
                except TypeError:
                    response = collection.query.bm25(
                        query=query,
                        limit=limit,
                        filters=where_filter,
                        return_metadata=weaviate.classes.query.MetadataQuery(score=True)
                    )

                results = []
                for obj in response.objects:
                    document_id = str(obj.properties.get("document_id", "") or "")
                    if document_id not in allowed_document_id_set:
                        continue
                    content = obj.properties.get("content", "")
                    score = obj.metadata.score if obj.metadata else 0.0
                    query_lower = query.lower()
                    content_lower = content.lower()
                    has_keywords = any(keyword in content_lower for keyword in query_lower.split() if len(keyword) > 2)
                    results.append(SearchResult(
                        content=content,
                        score=score,
                        metadata={
                            "document_id": document_id,
                            "page_number": obj.properties.get("page_number", 0),
                            "bm25_score": score,
                            "has_keywords": has_keywords,
                        },
                        document_id=document_id,
                        page=obj.properties.get("page_number", 0),
                        title=obj.properties.get("title", "") or "Unknown document",
                        chunk_index=obj.properties.get("chunk_index", -1),
                    ))

                logger.info(
                    "[hybrid] bm25 search scoped raw=%s kept=%s allowed_docs=%s",
                    len(response.objects),
                    len(results),
                    len(allowed_document_id_set),
                )
                return results
            
            # 使用BM25搜索，明确指定要搜索的字段
            # query_properties 指定要在哪些字段中搜索（content是主要内容字段）
            try:
                response = collection.query.bm25(
                    query=query,
                    query_properties=["content", "title"],  # 明确指定搜索字段
                    limit=limit,
                    return_metadata=weaviate.classes.query.MetadataQuery(score=True)
                )
            except TypeError:
                # 如果query_properties参数不支持，使用默认方式
                logger.warning("[hybrid] Weaviate不支持query_properties参数，使用默认BM25搜索")
                response = collection.query.bm25(
                    query=query,
                    limit=limit,
                    return_metadata=weaviate.classes.query.MetadataQuery(score=True)
                )
            
            results = []
            score_samples = []  # 用于记录分数样本
            
            for obj in response.objects:
                content = obj.properties.get('content', '')
                title = obj.properties.get('title', '') or '未知文档'
                document_id = obj.properties.get('document_id', '')
                page = obj.properties.get('page_number', 0)
                score = obj.metadata.score if obj.metadata else 0.0
                score_samples.append(score)
                
                # 验证内容是否包含查询关键词（用于调试）
                query_lower = query.lower()
                content_lower = content.lower()
                has_keywords = any(keyword in content_lower for keyword in query_lower.split() if len(keyword) > 2)
                
                results.append(SearchResult(
                    content=content,
                    score=score,
                    metadata={
                        'document_id': document_id,
                        'page_number': page,
                        'bm25_score': score,
                        'has_keywords': has_keywords  # 用于调试
                    },
                    document_id=document_id,
                    page=page,
                    title=title,
                    chunk_index=obj.properties.get('chunk_index', -1)
                ))
            
            # 记录BM25分数统计
            if score_samples:
                min_score = min(score_samples)
                max_score = max(score_samples)
                avg_score = sum(score_samples) / len(score_samples)
                logger.info(
                    "[hybrid] BM25搜索分数统计: 最小=%.3f, 最大=%.3f, 平均=%.3f, 结果数=%s",
                    min_score, max_score, avg_score, len(results)
                )
            
            # 检查结果相关性
            keyword_matches = sum(1 for r in results if r.metadata.get('has_keywords', False))
            logger.info(
                "[hybrid] BM25搜索结果: 总数=%s, 包含关键词=%s (%.1f%%)",
                len(results), keyword_matches, (keyword_matches / len(results) * 100) if results else 0
            )
            
            return results
            
        except Exception as e:
            logger.error(f"BM25搜索失败: {e}")
            return []
    
    def _merge_and_rerank(self, vector_results: List[SearchResult], 
                         bm25_results: List[SearchResult],
                         vector_weight: float, bm25_weight: float, 
                         limit: int) -> List[HybridSearchResult]:
        """合并和重排序结果"""
        
        # 统计去重前的唯一chunk数量（基于document_id + chunk_index）
        vector_unique_keys = set(f"{r.document_id}_{r.chunk_index}" for r in vector_results)
        bm25_unique_keys = set(f"{r.document_id}_{r.chunk_index}" for r in bm25_results)
        all_unique_keys = vector_unique_keys | bm25_unique_keys
        
        # 检查chunk_index是否有问题
        vector_chunk_indices = [r.chunk_index for r in vector_results]
        bm25_chunk_indices = [r.chunk_index for r in bm25_results]
        vector_invalid_indices = sum(1 for idx in vector_chunk_indices if idx < 0)
        bm25_invalid_indices = sum(1 for idx in bm25_chunk_indices if idx < 0)
        
        logger.info(
            "[hybrid] merge 入参 vector=%s(唯一key=%s) bm25=%s(唯一key=%s) limit=%s",
            len(vector_results),
            len(vector_unique_keys),
            len(bm25_results),
            len(bm25_unique_keys),
            limit,
        )
        logger.info(
            "[hybrid] merge 去重分析: 向量+BM25合并后唯一key总数=%s",
            len(all_unique_keys),
        )
        logger.info(
            "[hybrid] chunk_index检查: 向量搜索无效索引(<0)=%s/%s BM25搜索无效索引(<0)=%s/%s",
            vector_invalid_indices,
            len(vector_results),
            bm25_invalid_indices,
            len(bm25_results),
        )

        # 创建结果映射
        result_map = {}
        
        # 处理向量搜索结果
        for result in vector_results:
            key = f"{result.document_id}_{result.chunk_index}"
            result_map[key] = {
                'content': result.content,
                'vector_score': result.score,
                'bm25_score': 0.0,
                'metadata': result.metadata,
                'document_id': result.document_id,
                'page': result.page,
                'title': result.title,
                'chunk_index': result.chunk_index
            }
        
        # 处理BM25搜索结果
        for result in bm25_results:
            key = f"{result.document_id}_{result.chunk_index}"
            if key in result_map:
                # 合并分数
                result_map[key]['bm25_score'] = result.score
            else:
                # 新结果
                result_map[key] = {
                    'content': result.content,
                    'vector_score': 0.0,
                    'bm25_score': result.score,
                    'metadata': result.metadata,
                    'document_id': result.document_id,
                    'page': result.page,
                    'title': result.title,
                    'chunk_index': result.chunk_index
                }
        
        logger.info(
            "[hybrid] merge 最终result_map大小=%s (这是去重后的唯一chunk数量)",
            len(result_map),
        )
        
        # 计算混合分数并排序
        hybrid_results = []
        
        # 先收集所有分数，用于归一化
        vector_scores = [data['vector_score'] for data in result_map.values() if data['vector_score'] > 0]
        bm25_scores = [data['bm25_score'] for data in result_map.values() if data['bm25_score'] > 0]
        
        # 计算分数范围用于归一化
        max_vector_score = max(vector_scores) if vector_scores else 1.0
        min_vector_score = min(vector_scores) if vector_scores else 0.0
        max_bm25_score = max(bm25_scores) if bm25_scores else 1.0
        min_bm25_score = min(bm25_scores) if bm25_scores else 0.0
        
        # 避免除零
        vector_range = max_vector_score - min_vector_score if max_vector_score > min_vector_score else 1.0
        bm25_range = max_bm25_score - min_bm25_score if max_bm25_score > min_bm25_score else 1.0
        
        logger.info(
            "[hybrid] 分数范围: vector=[%.3f, %.3f] (范围=%.3f), bm25=[%.3f, %.3f] (范围=%.3f)",
            min_vector_score, max_vector_score, vector_range,
            min_bm25_score, max_bm25_score, bm25_range
        )
        
        for key, data in result_map.items():
            # 归一化分数（使用min-max归一化）
            if data['vector_score'] > 0:
                norm_vector_score = (data['vector_score'] - min_vector_score) / vector_range
            else:
                norm_vector_score = 0.0
            
            if data['bm25_score'] > 0:
                # BM25分数归一化：如果>1，说明是原始BM25分数，需要归一化
                if data['bm25_score'] > 1.0:
                    norm_bm25_score = (data['bm25_score'] - min_bm25_score) / bm25_range
                else:
                    norm_bm25_score = data['bm25_score']
            else:
                norm_bm25_score = 0.0
            
            # 计算混合分数
            # 如果只有一种分数，使用该分数；否则使用加权平均
            if data['vector_score'] > 0 and data['bm25_score'] > 0:
                hybrid_score = (vector_weight * norm_vector_score + 
                               bm25_weight * norm_bm25_score)
            elif data['vector_score'] > 0:
                hybrid_score = norm_vector_score
            elif data['bm25_score'] > 0:
                hybrid_score = norm_bm25_score
            else:
                hybrid_score = 0.0
            
            hybrid_results.append(HybridSearchResult(
                content=data['content'],
                score=hybrid_score,
                vector_score=data['vector_score'],
                bm25_score=data['bm25_score'],
                metadata=data['metadata'],
                document_id=data['document_id'],
                page=data['page'],
                title=data['title'],
                chunk_index=data['chunk_index']
            ))
        # MMR + 文档配额去冗余增强
        def mmr_diverse_select(results, k=8, doc_quota=2, min_doc=3):
            import numpy as np
            if not results:
                return []
            # 1. 文档分组，优先取top1
            doc_groups = {}
            for r in results:
                doc_groups.setdefault(r.document_id, []).append(r)
            # 2. 尽量先取每文档top1,满足min_doc覆盖
            pool = []
            doc_ids = sorted(doc_groups, key=lambda d: -max(x.score for x in doc_groups[d]))
            for d in doc_ids:
                pool.append(doc_groups[d][0])
            if len(pool) >= min_doc:
                selected = pool[:min_doc]
            else:
                selected = pool.copy()
            # 3. 继续按MMR，余弦去冗余，最多每文档doc_quota
            def get_emb(text):
                # 尽量用向量分数高的chunk的embedding
                try:
                    from pdf_processor.embedding_service import embedding_service
                    return embedding_service.encode([text])[0]
                except:
                    # fallback: 相似度0
                    return None
            selected_ids = set([(r.document_id, r.chunk_index) for r in selected])
            while len(selected) < k and len(selected) < len(results):
                candidates = [r for r in results if (r.document_id, r.chunk_index) not in selected_ids and \
                              selected.count(r.document_id) < doc_quota]
                if not candidates:
                    break
                # MMR策略：最大化与已选的最小距离（最不相似者优先）
                max_mmr, next_sel = -1e10, None
                emb_selected = [get_emb(r.content) for r in selected]
                for r in candidates:
                    emb = get_emb(r.content)
                    if emb is None:
                        continue
                    sims = [np.dot(emb, e)/(np.linalg.norm(emb)*np.linalg.norm(e)+1e-8) if e is not None else 0 for e in emb_selected]
                    mmr_score = r.score - max(sims)  # 混合分数-最大相似
                    if mmr_score > max_mmr:
                        max_mmr, next_sel = mmr_score, r
                if next_sel:
                    selected.append(next_sel)
                    selected_ids.add((next_sel.document_id, next_sel.chunk_index))
                else:
                    break
            # 限制最后每文档最多doc_quota
            out = []
            per_doc = {}
            for r in selected:
                c = per_doc.get(r.document_id, 0)
                if c < doc_quota:
                    out.append(r)
                    per_doc[r.document_id] = c + 1
            return out[:k]
        
        # 截取指定数量
        hybrid_results.sort(key=lambda x: x.score, reverse=True)
        final_results = hybrid_results[:limit]

        logger.debug(f"混合搜索合并完成，结果数量: {len(final_results)}")
        if hybrid_results:
            top_scores = [round(item.score, 4) for item in final_results[:5]]
            logger.info("[hybrid] merge 输出前5分数=%s", top_scores)
        
        return final_results
    
    def _normalize_score(self, score: float) -> float:
        """归一化分数到0-1范围"""
        if score <= 0:
            return 0.0
        # BM25分数通常范围很大（2-8），需要归一化
        # 向量分数已经是0-1范围（从距离转换）
        # 这里假设如果score > 1，可能是BM25分数，需要归一化
        if score > 1.0:
            # BM25分数归一化：假设最大分数约为10，归一化到0-1
            return min(1.0, score / 10.0)
        return min(1.0, score)
    
    def _fallback_vector_search(
        self,
        query: str,
        limit: int,
        allowed_document_ids: Optional[Iterable[Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[HybridSearchResult]:
        """降级到纯向量搜索"""
        try:
            vector_results = self._vector_search(
                query,
                limit,
                allowed_document_ids=allowed_document_ids,
                collection_name=collection_name,
            )
            hybrid_results = []
            
            for result in vector_results:
                hybrid_results.append(HybridSearchResult(
                    content=result.content,
                    score=result.score,
                    vector_score=result.score,
                    bm25_score=0.0,
                    metadata=result.metadata,
                    document_id=result.document_id,
                    page=result.page,
                    title=result.title,
                    chunk_index=result.chunk_index
                ))
            
            return hybrid_results
            
        except Exception as e:
            logger.error(f"降级向量搜索失败: {e}")
            return []

# 全局实例
hybrid_search_service = HybridSearchService()
