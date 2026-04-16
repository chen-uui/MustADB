"""
文档级聚合服务
将片段级搜索结果聚合为文档级结果，提供更完整的上下文
"""
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
from pdf_processor.hybrid_search_service import HybridSearchResult

logger = logging.getLogger(__name__)

@dataclass
class DocumentContext:
    """文档上下文"""
    document_id: str
    title: str
    total_chunks: int
    relevant_chunks: int
    combined_content: str
    chunk_scores: List[float]
    page_range: Tuple[int, int]
    relevance_score: float

@dataclass
class AggregatedSearchResult:
    """聚合搜索结果"""
    document_id: str
    title: str
    content: str
    relevance_score: float
    chunk_count: int
    page_range: Tuple[int, int]
    metadata: Dict[str, Any]

class DocumentAggregator:
    """文档级聚合器"""
    
    def __init__(self, max_context_length: int = 50000):
        self.max_context_length = max_context_length
    
    def aggregate_search_results(self, search_results: List[HybridSearchResult], 
                               max_documents: int = 10) -> List[AggregatedSearchResult]:
        """
        聚合搜索结果为文档级结果
        
        Args:
            search_results: 混合搜索结果列表
            max_documents: 最大文档数量
            
        Returns:
            聚合后的文档级结果列表
        """
        try:
            logger.info(f"开始文档级聚合，输入 {len(search_results)} 个片段")
            
            # 1. 按文档ID分组
            document_groups = self._group_by_document(search_results)
            logger.info(f"分组得到 {len(document_groups)} 个文档")
            
            # 2. 为每个文档聚合内容
            aggregated_docs = []
            for doc_id, chunks in document_groups.items():
                aggregated_doc = self._aggregate_document_chunks(doc_id, chunks)
                if aggregated_doc:
                    aggregated_docs.append(aggregated_doc)
            
            # 3. 按相关性分数排序
            aggregated_docs.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # 4. 限制返回数量
            result = aggregated_docs[:max_documents]
            logger.info(f"文档级聚合完成，返回 {len(result)} 个文档")
            
            return result
            
        except Exception as e:
            logger.error(f"文档级聚合失败: {e}")
            return []
    
    def _group_by_document(self, search_results: List[HybridSearchResult]) -> Dict[str, List[HybridSearchResult]]:
        """按文档ID分组搜索结果"""
        document_groups = defaultdict(list)
        
        for result in search_results:
            document_groups[result.document_id].append(result)
        
        # 为每个文档的片段按页码排序
        for doc_id in document_groups:
            document_groups[doc_id].sort(key=lambda x: x.page)
        
        return dict(document_groups)
    
    def _aggregate_document_chunks(self, doc_id: str, chunks: List[HybridSearchResult]) -> AggregatedSearchResult:
        """聚合单个文档的片段"""
        if not chunks:
            return None
        
        # 获取文档基本信息
        title = chunks[0].title
        # 兼容不同类型的搜索结果对象
        chunk_scores = []
        for chunk in chunks:
            if hasattr(chunk, 'score'):
                chunk_scores.append(chunk.score)
            elif hasattr(chunk, 'final_score'):
                chunk_scores.append(chunk.final_score)
            elif hasattr(chunk, 'original_score'):
                chunk_scores.append(chunk.original_score)
            else:
                chunk_scores.append(0.0)
        
        # 计算页面范围
        pages = [chunk.page for chunk in chunks]
        page_range = (min(pages), max(pages))
        
        # 聚合内容
        combined_content = self._combine_chunks_content(chunks)
        
        # 计算文档级相关性分数
        relevance_score = self._calculate_document_relevance_score(chunks)
        
        # 构建元数据，确保所有数值都是Python原生类型
        metadata = {
            'document_id': doc_id,
            'total_chunks': len(chunks),
            'page_range': page_range,
            'chunk_scores': [float(score) for score in chunk_scores],
            'avg_chunk_score': float(sum(chunk_scores) / len(chunk_scores)),
            'max_chunk_score': float(max(chunk_scores)),
            'min_chunk_score': float(min(chunk_scores))
        }
        
        return AggregatedSearchResult(
            document_id=doc_id,
            title=title,
            content=combined_content,
            relevance_score=relevance_score,
            chunk_count=len(chunks),
            page_range=page_range,
            metadata=metadata
        )
    
    def _combine_chunks_content(self, chunks: List[HybridSearchResult]) -> str:
        """合并片段内容"""
        if not chunks:
            return ""
        
        # 按页码排序
        sorted_chunks = sorted(chunks, key=lambda x: x.page)
        
        combined_parts = []
        current_length = 0
        
        for chunk in sorted_chunks:
            content = chunk.content.strip()
            if not content:
                continue
            
            # 检查长度限制
            if current_length + len(content) > self.max_context_length:
                # 如果添加这个片段会超过限制，截断并添加
                remaining_length = self.max_context_length - current_length
                if remaining_length > 100:  # 至少保留100字符
                    content = content[:remaining_length] + "..."
                    combined_parts.append(content)
                break
            
            combined_parts.append(content)
            current_length += len(content)
        
        # 合并内容，添加分隔符
        combined_content = "\n\n---\n\n".join(combined_parts)
        
        return combined_content
    
    def _calculate_document_relevance_score(self, chunks: List[HybridSearchResult]) -> float:
        """计算文档级相关性分数"""
        if not chunks:
            return 0.0
        
        # 使用多种策略计算分数，兼容不同类型的搜索结果对象
        scores = []
        for chunk in chunks:
            if hasattr(chunk, 'score'):
                scores.append(chunk.score)
            elif hasattr(chunk, 'final_score'):
                scores.append(chunk.final_score)
            elif hasattr(chunk, 'original_score'):
                scores.append(chunk.original_score)
            else:
                scores.append(0.0)
        
        # 1. 平均分数
        avg_score = sum(scores) / len(scores)
        
        # 2. 最高分数
        max_score = max(scores)
        
        # 3. 片段数量加权（更多相关片段 = 更高分数）
        count_weight = min(1.0, len(chunks) / 5.0)  # 最多5个片段的权重
        
        # 4. 综合分数
        relevance_score = (0.4 * avg_score + 0.4 * max_score + 0.2 * count_weight)
        
        return min(1.0, relevance_score)
    
    def expand_context(self, search_results: List[HybridSearchResult], 
                      expand_factor: float = 1.5) -> List[HybridSearchResult]:
        """
        扩展上下文：为每个相关文档添加更多片段
        
        Args:
            search_results: 原始搜索结果
            expand_factor: 扩展因子
            
        Returns:
            扩展后的搜索结果
        """
        try:
            # 按文档分组
            document_groups = self._group_by_document(search_results)
            expanded_results = []
            
            for doc_id, chunks in document_groups.items():
                # 获取该文档的所有片段
                all_chunks = self._get_document_all_chunks(doc_id)
                
                if not all_chunks:
                    expanded_results.extend(chunks)
                    continue
                
                # 计算需要添加的片段数量
                target_count = int(len(chunks) * expand_factor)
                additional_count = max(0, target_count - len(chunks))
                
                if additional_count > 0:
                    # 添加相关但未包含的片段
                    additional_chunks = self._select_additional_chunks(
                        chunks, all_chunks, additional_count
                    )
                    expanded_results.extend(chunks + additional_chunks)
                else:
                    expanded_results.extend(chunks)
            
            return expanded_results
            
        except Exception as e:
            logger.error(f"上下文扩展失败: {e}")
            return search_results
    
    def _get_document_all_chunks(self, document_id: str) -> List[HybridSearchResult]:
        """获取文档的所有片段（简化实现）"""
        # 这里应该从Weaviate获取文档的所有片段
        # 为了简化，返回空列表
        return []
    
    def _select_additional_chunks(self, existing_chunks: List[HybridSearchResult], 
                                all_chunks: List[HybridSearchResult], 
                                count: int) -> List[HybridSearchResult]:
        """选择额外的相关片段"""
        # 简化实现：随机选择
        existing_ids = {f"{chunk.document_id}_{chunk.chunk_index}" for chunk in existing_chunks}
        available_chunks = [chunk for chunk in all_chunks 
                           if f"{chunk.document_id}_{chunk.chunk_index}" not in existing_ids]
        
        return available_chunks[:count]

# 全局实例
document_aggregator = DocumentAggregator()
