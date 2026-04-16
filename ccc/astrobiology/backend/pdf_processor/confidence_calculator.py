"""
置信度计算服务
提供动态、多维度的置信度计算，提高RAG系统的准确性
"""
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from collections import Counter
import re
from pdf_processor.rag_service import SearchResult

logger = logging.getLogger(__name__)

@dataclass
class ConfidenceMetrics:
    """置信度指标"""
    overall_confidence: float
    relevance_confidence: float
    completeness_confidence: float
    consistency_confidence: float
    quality_confidence: float
    details: Dict[str, Any]

class ConfidenceCalculator:
    """置信度计算器"""
    
    def __init__(self):
        self.historical_accuracy = 0.8  # 历史准确率，用于校准
        # 将最小阈值下调，避免所有结果被钳制到0.30，影响诊断与排序
        self.min_confidence_threshold = 0.05  # 最小置信度阈值
        self.max_confidence_threshold = 0.95  # 最大置信度阈值
    
    def calculate_dynamic_confidence(self, search_results: List[SearchResult], 
                                   query: str, 
                                   use_rerank: bool = True) -> ConfidenceMetrics:
        """
        动态计算置信度
        
        Args:
            search_results: 搜索结果列表
            query: 查询字符串
            use_rerank: 是否使用了重排序
            
        Returns:
            置信度指标
        """
        if not search_results:
            return self._create_empty_confidence()
        
        try:
            logger.info(f"开始计算置信度，结果数: {len(search_results)}")
            
            # 1. 相关性置信度
            relevance_conf = self._calculate_relevance_confidence(search_results, query)
            
            # 2. 完整性置信度
            completeness_conf = self._calculate_completeness_confidence(search_results, query)
            
            # 3. 一致性置信度
            consistency_conf = self._calculate_consistency_confidence(search_results)
            
            # 4. 质量置信度
            quality_conf = self._calculate_quality_confidence(search_results, use_rerank)
            
            # 5. 综合置信度（加权平均）
            overall_conf = self._calculate_overall_confidence(
                relevance_conf, completeness_conf, consistency_conf, quality_conf
            )
            
            # 6. 置信度校准
            calibrated_conf = self._calibrate_confidence(overall_conf)
            
            # 7. 构建详细信息
            details = self._build_confidence_details(
                search_results, query, relevance_conf, completeness_conf, 
                consistency_conf, quality_conf, calibrated_conf
            )
            
            metrics = ConfidenceMetrics(
                overall_confidence=calibrated_conf,
                relevance_confidence=relevance_conf,
                completeness_confidence=completeness_conf,
                consistency_confidence=consistency_conf,
                quality_confidence=quality_conf,
                details=details
            )
            
            logger.info(f"置信度计算完成: 总体={calibrated_conf:.3f}, 相关性={relevance_conf:.3f}")
            return metrics
            
        except Exception as e:
            logger.error(f"置信度计算失败: {e}")
            return self._create_empty_confidence()
    
    def _calculate_relevance_confidence(self, search_results: List[SearchResult], 
                                      query: str) -> float:
        """计算相关性置信度"""
        if not search_results:
            return 0.0
        
        # 1. 基础分数分析
        scores = [result.score for result in search_results]
        max_score = max(scores)
        avg_score = sum(scores) / len(scores)
        
        # 2. 分数分布分析
        score_variance = np.var(scores) if len(scores) > 1 else 0
        score_std = np.std(scores) if len(scores) > 1 else 0
        
        # 3. 重排序分数分析（如果可用）
        rerank_scores = []
        for result in search_results:
            if hasattr(result, 'rerank_score'):
                rerank_scores.append(result.rerank_score)
            elif hasattr(result, 'final_score'):
                rerank_scores.append(result.final_score)
        
        if rerank_scores:
            rerank_avg = sum(rerank_scores) / len(rerank_scores)
            rerank_max = max(rerank_scores)
        else:
            rerank_avg = avg_score
            rerank_max = max_score
        
        # 4. 查询匹配度分析
        query_terms = set(query.lower().split())
        match_scores = []
        for result in search_results:
            content_terms = set(result.content.lower().split())
            # 避免零除：当查询词为空或被清理后为空集时，匹配度按0处理
            if query_terms:
                match_ratio = len(query_terms.intersection(content_terms)) / len(query_terms)
            else:
                match_ratio = 0.0
            match_scores.append(match_ratio)
        
        avg_match = sum(match_scores) / len(match_scores) if match_scores else 0
        
        # 5. 综合相关性分数
        relevance_score = (
            0.3 * max_score +           # 最高分数权重
            0.2 * avg_score +           # 平均分数权重
            0.2 * rerank_max +          # 重排序最高分数
            0.2 * rerank_avg +          # 重排序平均分数
            0.1 * avg_match             # 查询匹配度
        )
        
        # 6. 分数稳定性调整（分数分布越稳定，置信度越高）
        stability_factor = max(0.5, 1.0 - score_std)
        relevance_score *= stability_factor
        
        return min(1.0, max(0.0, relevance_score))
    
    def _calculate_completeness_confidence(self, search_results: List[SearchResult], 
                                         query: str) -> float:
        """计算完整性置信度"""
        if not search_results:
            return 0.0
        
        # 1. 结果数量因子
        count_factor = min(1.0, len(search_results) / 5.0)
        
        # 2. 内容长度因子
        content_lengths = [len(result.content) for result in search_results]
        avg_length = sum(content_lengths) / len(content_lengths)
        length_factor = min(1.0, avg_length / 1000)  # 假设1000字符为理想长度
        
        # 3. 上下文覆盖度
        all_content = " ".join([result.content for result in search_results])
        query_terms = set(query.lower().split())
        content_terms = set(all_content.lower().split())
        # 避免零除：当查询词为空时，覆盖度按0处理
        coverage = (len(query_terms.intersection(content_terms)) / len(query_terms)) if query_terms else 0.0
        
        # 4. 文档多样性（不同文档的数量）
        unique_docs = len(set(result.document_id for result in search_results))
        diversity_factor = min(1.0, unique_docs / 3.0)  # 假设3个不同文档为理想
        
        # 5. 综合完整性分数
        completeness_score = (
            0.3 * count_factor +
            0.2 * length_factor +
            0.3 * coverage +
            0.2 * diversity_factor
        )
        
        return min(1.0, max(0.0, completeness_score))
    
    def _calculate_consistency_confidence(self, search_results: List[SearchResult]) -> float:
        """计算一致性置信度"""
        if len(search_results) < 2:
            return 0.5  # 单个结果无法评估一致性
        
        # 1. 分数一致性
        scores = [result.score for result in search_results]
        score_cv = np.std(scores) / np.mean(scores) if np.mean(scores) > 0 else 1.0
        score_consistency = max(0.0, 1.0 - score_cv)
        
        # 2. 内容相似性（基于关键词重叠）
        content_similarities = []
        for i in range(len(search_results)):
            for j in range(i + 1, len(search_results)):
                content1 = set(search_results[i].content.lower().split())
                content2 = set(search_results[j].content.lower().split())
                if content1 and content2:
                    similarity = len(content1.intersection(content2)) / len(content1.union(content2))
                    content_similarities.append(similarity)
        
        content_consistency = sum(content_similarities) / len(content_similarities) if content_similarities else 0.5
        
        # 3. 文档来源一致性
        doc_sources = [result.document_id for result in search_results]
        source_diversity = len(set(doc_sources)) / len(doc_sources)
        source_consistency = 1.0 - source_diversity  # 来源越集中，一致性越高
        
        # 4. 综合一致性分数
        consistency_score = (
            0.4 * score_consistency +
            0.4 * content_consistency +
            0.2 * source_consistency
        )
        
        return min(1.0, max(0.0, consistency_score))
    
    def _calculate_quality_confidence(self, search_results: List[SearchResult], 
                                    use_rerank: bool) -> float:
        """计算质量置信度"""
        if not search_results:
            return 0.0
        
        # 1. 重排序质量（如果使用了重排序）
        if use_rerank:
            rerank_quality = 0.8  # 重排序通常提高质量
        else:
            rerank_quality = 0.6
        
        # 2. 分数质量（分数分布和范围）
        scores = [result.score for result in search_results]
        score_range = max(scores) - min(scores) if len(scores) > 1 else 0
        score_quality = min(1.0, score_range * 2)  # 分数范围越大，质量越高
        
        # 3. 内容质量指标
        quality_indicators = []
        for result in search_results:
            content = result.content
            
            # 长度合理性
            length_score = min(1.0, len(content) / 500)  # 500字符为基准
            
            # 信息密度（非空字符比例）
            non_empty_chars = len([c for c in content if c.strip()])
            density_score = non_empty_chars / len(content) if content else 0
            
            # 结构化内容（包含数字、标点等）
            has_numbers = bool(re.search(r'\d+', content))
            has_punctuation = bool(re.search(r'[.!?;:]', content))
            structure_score = 0.5 + 0.3 * has_numbers + 0.2 * has_punctuation
            
            content_quality = (length_score + density_score + structure_score) / 3
            quality_indicators.append(content_quality)
        
        avg_content_quality = sum(quality_indicators) / len(quality_indicators)
        
        # 4. 综合质量分数
        quality_score = (
            0.3 * rerank_quality +
            0.3 * score_quality +
            0.4 * avg_content_quality
        )
        
        return min(1.0, max(0.0, quality_score))
    
    def _calculate_overall_confidence(self, relevance: float, completeness: float, 
                                    consistency: float, quality: float) -> float:
        """计算综合置信度"""
        # 使用加权平均，相关性权重最高
        overall = (
            0.4 * relevance +      # 相关性最重要
            0.25 * completeness +  # 完整性次重要
            0.2 * consistency +    # 一致性
            0.15 * quality         # 质量
        )
        
        return min(1.0, max(0.0, overall))
    
    def _calibrate_confidence(self, raw_confidence: float) -> float:
        """校准置信度"""
        # 使用历史准确率进行校准
        calibrated = raw_confidence * self.historical_accuracy
        
        # 应用阈值限制
        calibrated = max(self.min_confidence_threshold, 
                        min(self.max_confidence_threshold, calibrated))
        
        return calibrated
    
    def _build_confidence_details(self, search_results: List[SearchResult], 
                                query: str, relevance: float, completeness: float,
                                consistency: float, quality: float, 
                                overall: float) -> Dict[str, Any]:
        """构建置信度详细信息"""
        scores = [result.score for result in search_results]
        
        return {
            "query": query,
            "result_count": len(search_results),
            "score_statistics": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
                "mean": sum(scores) / len(scores) if scores else 0,
                "std": np.std(scores) if len(scores) > 1 else 0
            },
            "confidence_breakdown": {
                "relevance": relevance,
                "completeness": completeness,
                "consistency": consistency,
                "quality": quality,
                "overall": overall
            },
            "document_sources": len(set(result.document_id for result in search_results)),
            "has_rerank": any(hasattr(result, 'rerank_score') for result in search_results),
            "avg_content_length": sum(len(result.content) for result in search_results) / len(search_results) if search_results else 0
        }
    
    def _create_empty_confidence(self) -> ConfidenceMetrics:
        """创建空的置信度指标"""
        return ConfidenceMetrics(
            overall_confidence=0.0,
            relevance_confidence=0.0,
            completeness_confidence=0.0,
            consistency_confidence=0.0,
            quality_confidence=0.0,
            details={}
        )
    
    def update_historical_accuracy(self, accuracy: float):
        """更新历史准确率"""
        self.historical_accuracy = max(0.0, min(1.0, accuracy))
        logger.info(f"更新历史准确率: {self.historical_accuracy}")
    
    def get_confidence_thresholds(self) -> Tuple[float, float]:
        """获取置信度阈值"""
        return self.min_confidence_threshold, self.max_confidence_threshold
    
    def set_confidence_thresholds(self, min_threshold: float, max_threshold: float):
        """设置置信度阈值"""
        self.min_confidence_threshold = max(0.0, min(1.0, min_threshold))
        self.max_confidence_threshold = max(self.min_confidence_threshold, 
                                          min(1.0, max_threshold))
        logger.info(f"设置置信度阈值: {self.min_confidence_threshold} - {self.max_confidence_threshold}")

# 全局实例
confidence_calculator = ConfidenceCalculator()
