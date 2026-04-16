"""
重排序服务
使用CrossEncoder模型对搜索结果进行重新排序，提高检索精度
"""
import logging
import math
import time
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import torch
from sentence_transformers import CrossEncoder
from pdf_processor.hybrid_search_service import HybridSearchResult

logger = logging.getLogger(__name__)

@dataclass
class RerankedResult:
    """重排序结果"""
    content: str
    original_score: float
    rerank_score: float
    final_score: float
    metadata: Dict[str, Any]
    document_id: str
    page: int
    title: str
    chunk_index: int = -1

class RerankerService:
    """重排序服务 - 集成原有系统的配置"""
    
    def __init__(self, model_name: str = None):
        from django.conf import settings as django_settings
        import os
        
        # 使用原有系统的配置
        if model_name is None:
            self.model_name = django_settings.RERANKER_CONFIG['MODEL_NAME']
            self.cache_dir = django_settings.RERANKER_CONFIG['CACHE_DIR']
            self.device = django_settings.RERANKER_CONFIG['DEVICE']
        else:
            self.model_name = model_name
            self.cache_dir = str(os.path.join(os.path.dirname(__file__), '../../models'))
            self.device = 'cpu'
        
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化重排序模型 - 使用原有系统的逻辑"""
        import os
        
        try:
            logger.info(f"初始化重排序模型: {self.model_name}")
            
            # 尝试从本地加载模型
            # 处理模型路径：cross-encoder/ms-marco-MiniLM-L-6-v2 -> cross-encoder/ms-marco-MiniLM-L-6-v2
            if '/' in self.model_name:
                model_path = os.path.join(self.cache_dir, self.model_name)
            else:
                model_path = os.path.join(self.cache_dir, self.model_name.replace('/', '_'))
            
            if os.path.exists(model_path):
                logger.info(f"从本地路径加载重排序模型: {model_path}")
                self.model = CrossEncoder(model_path, device=self.device)
            else:
                logger.info(f"本地模型不存在，尝试从在线下载: {self.model_name}")
                self.model = CrossEncoder(self.model_name, device=self.device)
                
                # 保存模型到本地
                os.makedirs(self.cache_dir, exist_ok=True)
                self.model.save(model_path)
                logger.info(f"重排序模型已保存到本地: {model_path}")
            
            logger.info("重排序模型初始化成功")
            
        except Exception as e:
            logger.error(f"重排序模型初始化失败: {e}")
            self.model = None
    
    def rerank_results(self, query: str, search_results: List[HybridSearchResult], 
                      top_k: int = 10, rerank_weight: float = 0.6) -> List[RerankedResult]:
        """
        重排序搜索结果
        
        Args:
            query: 搜索查询
            search_results: 搜索结果列表
            top_k: 返回结果数量
            rerank_weight: 重排序权重
            
        Returns:
            重排序后的结果列表
        """
        if not self.model or not search_results:
            return self._fallback_rerank(query, search_results, top_k)
        
        try:
            logger.info("[rerank] START query='%s' results=%s top_k=%s", query[:60], len(search_results), top_k)
            start_cpu = time.perf_counter()
            start = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            end = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            if start and end:
                start.record()
            
            # 1. 准备查询-文档对
            query_doc_pairs = []
            for result in search_results:
                query_doc_pairs.append([query, result.content])
            
            # 2. 批量计算重排序分数
            predict_start = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            predict_end = torch.cuda.Event(enable_timing=True) if torch.cuda.is_available() else None
            predict_cpu_start = time.perf_counter()
            if predict_start and predict_end:
                predict_start.record()
            rerank_scores = self.model.predict(query_doc_pairs)
            predict_cpu_elapsed = time.perf_counter() - predict_cpu_start
            if predict_start and predict_end:
                predict_end.record()
                torch.cuda.synchronize()
                logger.info("[rerank] predict elapsed=%.2fms (cpu≈%.2fs)", predict_start.elapsed_time(predict_end), predict_cpu_elapsed)
            else:
                logger.info("[rerank] predict elapsed≈%.2fs", predict_cpu_elapsed)
            
            # 3. 创建重排序结果
            reranked_results = []
            for i, (result, rerank_score) in enumerate(zip(search_results, rerank_scores)):
                # 计算最终分数（原始分数 + 重排序分数）
                final_score = self._calculate_final_score(
                    result.score, rerank_score, rerank_weight
                )
                
                reranked_results.append(RerankedResult(
                    content=result.content,
                    original_score=result.score,
                    rerank_score=float(rerank_score),
                    final_score=final_score,
                    metadata=result.metadata,
                    document_id=result.document_id,
                    page=result.page,
                    title=result.title,
                    chunk_index=result.chunk_index
                ))
            
            # 4. 按最终分数排序
            reranked_results.sort(key=lambda x: x.final_score, reverse=True)
            
            # 5. 返回top_k结果
            result = reranked_results[:top_k]
            total_cpu = time.perf_counter() - start_cpu
            if start and end:
                end.record()
                torch.cuda.synchronize()
                logger.info("[rerank] FINISH total=%.2fms (cpu≈%.2fs) returned=%s", start.elapsed_time(end), total_cpu, len(result))
            else:
                logger.info("[rerank] FINISH total≈%.2fs returned=%s", total_cpu, len(result))
            
            return result
            
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            return self._fallback_rerank(query, search_results, top_k)
    
    def _calculate_final_score(self, original_score: float, rerank_score: float, 
                               rerank_weight: float) -> float:
        """计算最终分数"""
        # 使用sigmoid对交叉编码输出进行归一化
        normalized_rerank = 1.0 / (1.0 + math.exp(-rerank_score))

        # 重新归一化原始分数到0-1范围（原始分数通常在0~1之间，但加一层安全夹持）
        normalized_original = max(0.0, min(1.0, original_score))

        # 加权融合
        final_score = (1 - rerank_weight) * normalized_original + rerank_weight * normalized_rerank
        return final_score
    
    def _fallback_rerank(self, query: str, search_results: List[HybridSearchResult], 
                        top_k: int) -> List[RerankedResult]:
        """降级重排序（使用原始分数）"""
        try:
            reranked_results = []
            
            for result in search_results:
                reranked_results.append(RerankedResult(
                    content=result.content,
                    original_score=result.score,
                    rerank_score=result.score,
                    final_score=result.score,
                    metadata=result.metadata,
                    document_id=result.document_id,
                    page=result.page,
                    title=result.title,
                    chunk_index=result.chunk_index
                ))
            
            # 按原始分数排序
            reranked_results.sort(key=lambda x: x.original_score, reverse=True)
            
            return reranked_results[:top_k]
            
        except Exception as e:
            logger.error(f"降级重排序失败: {e}")
            return []
    
    def batch_rerank(self, queries_and_results: List[Tuple[str, List[HybridSearchResult]]], 
                    top_k: int = 10) -> List[List[RerankedResult]]:
        """
        批量重排序
        
        Args:
            queries_and_results: 查询和结果对的列表
            top_k: 每个查询返回的结果数量
            
        Returns:
            重排序结果列表的列表
        """
        if not self.model:
            return [self._fallback_rerank(query, results, top_k) 
                   for query, results in queries_and_results]
        
        try:
            logger.info(f"开始批量重排序，查询数: {len(queries_and_results)}")
            
            all_reranked_results = []
            
            for query, search_results in queries_and_results:
                reranked_results = self.rerank_results(query, search_results, top_k)
                all_reranked_results.append(reranked_results)
            
            logger.info("批量重排序完成")
            return all_reranked_results
            
        except Exception as e:
            logger.error(f"批量重排序失败: {e}")
            return [self._fallback_rerank(query, results, top_k) 
                   for query, results in queries_and_results]
    
    def is_available(self) -> bool:
        """检查重排序服务是否可用"""
        return self.model is not None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'model_name': self.model_name,
            'is_available': self.is_available(),
            'device': str(self.model.device) if self.model else None
        }

# 全局实例
reranker_service = RerankerService()
