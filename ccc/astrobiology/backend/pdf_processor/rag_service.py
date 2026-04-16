"""
RAG (Retrieval-Augmented Generation) 服务
集成Weaviate向量搜索和本地LLM生成答案
"""
import os

# 禁用 weaviate / tqdm 默认的进度条输出，减少控制台噪声
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("WEAVIATE_PROGRESS_BAR_DISABLE", "true")
os.environ.setdefault("WEAVIATE_NO_PROGRESS_BAR", "1")
os.environ.setdefault("WEAVIATE_PROGRESS_BAR", "false")
os.environ.setdefault("DISABLE_TQDM", "1")

try:
    import tqdm as _tqdm_module

    class _SilentTqdm:
        def __init__(self, iterable=None, *args, **kwargs):
            self._iterable = iterable

        def __iter__(self):
            if self._iterable is None:
                return iter(())
            for item in self._iterable:
                yield item

        def update(self, *args, **kwargs):
            return None

        def close(self, *args, **kwargs):
            return None

        def set_description(self, *args, **kwargs):
            return None

        def set_postfix(self, *args, **kwargs):
            return None

        def refresh(self, *args, **kwargs):
            return None

        def clear(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    if hasattr(_tqdm_module, 'tqdm'):
        _tqdm_module.tqdm = _SilentTqdm

    try:
        import tqdm.auto as _tqdm_auto
        _tqdm_auto.tqdm = _SilentTqdm
    except Exception:
        pass
except Exception:
    pass

import logging
from typing import List, Dict, Any
from dataclasses import dataclass
from sentence_transformers.cross_encoder import CrossEncoder
import weaviate
from django.conf import settings

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """搜索结果数据结构"""
    content: str
    score: float
    metadata: Dict[str, Any]
    document_id: str
    page: int
    title: str
    # 追加索引信息，便于上下文扩展
    chunk_index: int = -1

@dataclass
class RAGAnswer:
    """RAG答案数据结构"""
    answer: str
    # 为了与视图层统一，sources 使用标准字典列表结构
    sources: List[Dict[str, Any]]
    confidence: float
    total_contexts: int
    
    def to_dict(self):
        """转换为可JSON序列化的字典"""
        return {
            'answer': self.answer,
            'sources': self.sources,
            'confidence': self.confidence,
            'total_contexts': self.total_contexts
        }

_qa_service = None

def get_qa_service():
    """获取问答服务实例 - 确保正确初始化"""
    global _qa_service
    if _qa_service is None:
        _qa_service = RAGService()
        # 确保服务已初始化
        if not _qa_service.is_initialized:
            _qa_service.initialize()
    return _qa_service

class RAGService:
    """RAG问答服务"""
    
    def __init__(self):
        # 使用统一的嵌入服务和连接管理
        from .embedding_service import embedding_service
        from .weaviate_connection import weaviate_connection
        
        self.embedding_service = embedding_service
        self.weaviate_connection = weaviate_connection
        self._reranker = None
        self._qa_service = None
        self._is_initialized = False
        
        # 添加collection_name属性
        self.collection_name = "PDFDocument"
        
    @property
    def is_initialized(self) -> bool:
        """检查服务是否已初始化"""
        return self._is_initialized
    
    @property
    def weaviate_client(self):
        """获取Weaviate客户端"""
        if self.weaviate_connection:
            return self.weaviate_connection.get_client()
        return None
        
    def initialize(self) -> bool:
        """初始化RAG服务"""
        try:
            # 检查嵌入服务是否可用
            if not self.embedding_service:
                logger.error("嵌入服务不可用")
                return False
                
            # 检查Weaviate连接是否可用
            if not self.weaviate_connection.test_connection():
                logger.error("Weaviate连接测试失败")
                return False
                
            self._is_initialized = True
            logger.info("RAG服务初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"RAG服务初始化失败: {e}")
            self._is_initialized = False
            return False
        
    def _get_reranker(self):
        """获取重排序模型（延迟加载）"""
        if self._reranker is None:
            model_name = settings.RERANKER_CONFIG['MODEL_NAME']
            model_path = os.path.join(settings.RERANKER_CONFIG['CACHE_DIR'], model_name)
            
            try:
                # 尝试从本地加载模型
                if os.path.exists(model_path):
                    logger.info(f"从本地路径加载重排序模型: {model_path}")
                    self._reranker = CrossEncoder(model_path, device=settings.RERANKER_CONFIG['DEVICE'])
                else:
                    logger.info(f"本地模型不存在，从在线下载: {model_name}")
                    self._reranker = CrossEncoder(model_name, device=settings.RERANKER_CONFIG['DEVICE'])
                    
                    # 保存模型到本地
                    os.makedirs(settings.RERANKER_CONFIG['CACHE_DIR'], exist_ok=True)
                    self._reranker.save(model_path)
                    logger.info(f"重排序模型已保存到本地: {model_path}")
                    
            except Exception as e:
                logger.error(f"重排序模型初始化失败: {e}")
                self._reranker = None
                
        return self._reranker
    
    def test_connection(self) -> bool:
        """测试连接状态"""
        return self.weaviate_connection.test_connection()
    
    def vector_search(self, query: str, top_k: int = 5, document_id: str = None, limit: int = None) -> List[SearchResult]:
        """向量搜索"""
        try:
            # 如果提供了limit参数，使用它作为top_k
            if limit is not None:
                top_k = limit
                
            logger.info(f"开始向量搜索，查询: {query[:50]}..., top_k: {top_k}")
            
            # 使用统一的嵌入服务
            query_vector = self.embedding_service.encode([query])[0]
            logger.info(f"查询向量生成成功，维度: {len(query_vector)}")
            
            client = self.weaviate_connection.get_client()
            collection = client.collections.get("PDFDocument")
            logger.info(f"Weaviate客户端连接成功，集合: PDFDocument")
            
            # 构建查询 - 修复where参数问题
            if document_id:
                where_filter = weaviate.classes.query.Filter.by_property("document_id").equal(document_id)
                response = collection.query.near_vector(
                    near_vector=query_vector,
                    limit=top_k,
                    where=where_filter,
                    return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
                )
            else:
                response = collection.query.near_vector(
                    near_vector=query_vector,
                    limit=top_k,
                    return_metadata=weaviate.classes.query.MetadataQuery(distance=True)
                )
            
            results = []
            seen_chunks = set()  # 用于去重 (document_id + chunk_index)
            logger.info(f"Weaviate查询返回 {len(response.objects)} 个结果")
            
            for i, obj in enumerate(response.objects):
                content = obj.properties.get('content', '')
                title = obj.properties.get('title', '') or '未知文档'
                document_id = obj.properties.get('document_id', '')
                page = obj.properties.get('page_number', 0)
                score = 1.0 - (obj.metadata.distance if obj.metadata else 0.0)
                chunk_index = obj.properties.get('chunk_index', -1)
                
                dedupe_key = (document_id, chunk_index if chunk_index is not None else page)
                
                # 去重逻辑：按文档ID + chunk索引，避免误删同文档的其它片段
                if dedupe_key in seen_chunks:
                    logger.info(
                        "跳过重复结果: 文档ID='%s', chunk_index=%s, 页码=%s",
                        document_id,
                        chunk_index,
                        page,
                    )
                    continue
                seen_chunks.add(dedupe_key)
                
                logger.info(f"结果 {len(results)+1}: 标题='{title}', 文档ID='{document_id}', 页码={page}, 分数={score:.3f}, 内容长度={len(content)}")
                
                results.append(SearchResult(
                    content=content,
                    score=score,
                    metadata={
                        'document_id': document_id,
                        'page_number': page,
                        'chunk_index': obj.properties.get('chunk_index'),
                        'distance': obj.metadata.distance if obj.metadata else None
                    },
                    document_id=document_id,
                    page=page,
                    title=title,
                    chunk_index=chunk_index
                ))
                
                # 限制结果数量
                if len(results) >= top_k:
                    break
            
            logger.info(f"向量搜索完成，返回 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []

    def rerank_contexts(self, query: str, search_results: List[SearchResult], top_k: int = None) -> List[SearchResult]:
        """
        使用重排序模型对搜索结果进行重新排序
        
        Args:
            query: 查询问题
            search_results: 搜索结果列表
            top_k: 返回的结果数量，如果为None则返回所有结果
            
        Returns:
            重排序后的搜索结果列表
        """
        try:
            if not search_results:
                return []
            
            # 获取重排序模型
            reranker = self._get_reranker()
            if reranker is None:
                logger.warning("重排序模型未初始化，返回原始搜索结果")
                return search_results[:top_k] if top_k else search_results
            
            # 准备重排序的输入数据
            query_doc_pairs = []
            for result in search_results:
                # 组合文档内容用于重排序
                doc_text = f"{result.content}"
                if hasattr(result, 'metadata') and result.metadata:
                    # 添加元数据信息
                    if 'title' in result.metadata:
                        doc_text = f"标题: {result.metadata['title']}\n内容: {doc_text}"
                    if 'source' in result.metadata:
                        doc_text = f"{doc_text}\n来源: {result.metadata['source']}"
                
                query_doc_pairs.append([query, doc_text])
            
            # 执行重排序
            logger.info(f"开始重排序 {len(query_doc_pairs)} 个搜索结果")
            scores = reranker.predict(query_doc_pairs)
            
            # 将分数与原始结果配对并排序
            scored_results = list(zip(search_results, scores))
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # 提取重排序后的结果
            reranked_results = [result for result, score in scored_results]
            
            # 更新结果的相关性分数
            for i, (result, score) in enumerate(scored_results):
                if hasattr(result, 'score'):
                    result.score = float(score)
                elif hasattr(result, 'metadata'):
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata['rerank_score'] = float(score)
            
            # 返回指定数量的结果
            final_results = reranked_results[:top_k] if top_k else reranked_results
            logger.info(f"重排序完成，返回 {len(final_results)} 个结果")
            
            return final_results
            
        except Exception as e:
            logger.error(f"重排序过程中发生错误: {e}")
            # 发生错误时返回原始搜索结果
            return search_results[:top_k] if top_k else search_results

    def calculate_confidence(self, search_results: List[SearchResult], query: str) -> dict:
        """
        计算答案的置信度
        
        Args:
            search_results: 搜索结果列表
            query: 查询问题
            
        Returns:
            包含置信度和影响因素的字典
        """
        try:
            if not search_results:
                return {
                    'confidence': 0.0,
                    'factors': {
                        'result_count': 0,
                        'avg_score': 0.0,
                        'score_variance': 0.0,
                        'content_length': 0
                    }
                }
            
            # 提取分数
            scores = []
            total_content_length = 0
            
            for result in search_results:
                # 尝试获取重排序分数或原始分数
                score = 0.0
                if hasattr(result, 'score') and result.score is not None:
                    score = float(result.score)
                elif hasattr(result, 'metadata') and result.metadata:
                    if 'rerank_score' in result.metadata:
                        score = float(result.metadata['rerank_score'])
                    elif 'distance' in result.metadata:
                        # 将距离转换为相似度分数（距离越小，相似度越高）
                        distance = float(result.metadata['distance'])
                        score = max(0.0, 1.0 - distance)
                
                scores.append(score)
                total_content_length += len(result.content) if result.content else 0
            
            # 计算统计指标
            avg_score = sum(scores) / len(scores) if scores else 0.0
            score_variance = sum((s - avg_score) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0.0
            
            # 计算基础置信度
            base_confidence = avg_score
            
            # 调整因子
            result_count_factor = min(1.0, len(search_results) / 5.0)  # 结果数量因子
            variance_factor = max(0.5, 1.0 - score_variance)  # 分数一致性因子
            content_factor = min(1.0, total_content_length / 1000.0)  # 内容丰富度因子
            
            # 综合置信度计算
            confidence = base_confidence * result_count_factor * variance_factor * content_factor
            confidence = max(0.0, min(1.0, confidence))  # 限制在0-1范围内
            
            return {
                'confidence': confidence,
                'factors': {
                    'result_count': len(search_results),
                    'avg_score': avg_score,
                    'score_variance': score_variance,
                    'content_length': total_content_length,
                    'result_count_factor': result_count_factor,
                    'variance_factor': variance_factor,
                    'content_factor': content_factor
                }
            }
            
        except Exception as e:
            logger.error(f"置信度计算过程中发生错误: {e}")
            return {
                'confidence': 0.5,  # 默认中等置信度
                'factors': {
                    'error': str(e)
                }
            }
    
    def generate_answer(self, question: str, contexts: List[str], search_results: List[SearchResult] = None, use_multi_pass: bool = None) -> RAGAnswer:
        """生成答案（升级版：multi-stage structured multi-doc fusion with English chain-of-bullet prompts）"""
        if self._qa_service is None:
            self._qa_service = get_qa_service()
        try:
            import requests
            from .pdf_utils import GlobalConfig
            base_llm_url = getattr(GlobalConfig, 'LLM_BASE_URL', 'http://localhost:11434')
            llm_endpoint = f"{base_llm_url.rstrip('/')}/v1/chat/completions"
            # -------- Step 1: 每个context结构化英文摘要 --------
            summaries = []
            for i, ctx in enumerate(contexts):
                summary_prompt = (
                    f"Please carefully extract and structure all content in the passage relevant to the following question.\n"
                    f"Passage [{i+1}]:\n{ctx}\n\n"
                    f"Question: {question}\n"
                    "- List key facts, evidence, findings, or scientific claims separately.\n"
                    "- Include short supporting details (e.g., mineral names, measured values, observational context) when present.\n"
                    "- If method, data, or conclusions are described, mention them explicitly.\n"
                    "- Output as a clear English bullet list. If irrelevant, say 'No relevant info.'"
                )
                payload = {
                    "model": "llama3.1:8b-instruct-q4_K_M",
                    "messages": [
                        {"role": "system", "content": "You are an expert scientific document summarizer."},
                        {"role": "user", "content": summary_prompt}
                    ],
                    "max_tokens": 600, "temperature": 0.2, "stream": False
                }
                resp = requests.post(
                    llm_endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=45
                )
                if resp.status_code == 200:
                    res_json = resp.json()
                    summary = res_json['choices'][0]['message']['content']
                else:
                    summary = "No relevant info."
                summaries.append(f"Summary [{i+1}]: {summary}")
            # -------- Step 2: 汇总所有摘要，结构化融合聚合 --------
            all_summaries = "\n".join(summaries)
            fusion_prompt = (
                "Here are segment-wise bullet summaries from multiple sources related to the user’s question.\n"
                "- Synthesize these into a structured answer for a scientific audience with informative detail.\n"
                "- For each point, indicate [Summary X] for the source(s) and include short supporting context (e.g., mineral phases, locations, experimental notes) when available.\n"
                "- Explicitly list consensus, unique findings, and conflicting points, if any.\n"
                "- Output as a numbered English bullet list.\n"
                f"Summaries:\n{all_summaries}\n\n"
                f"Question: {question}\n"
                "Only use the extracted summaries, do not make up content."
            )
            payload2 = {
                "model": "llama3.1:8b-instruct-q4_K_M",
                "messages": [
                    {"role": "system", "content": "You are a scientific research assistant."},
                    {"role": "user", "content": fusion_prompt}
                ],
                "max_tokens": 1500, "temperature": 0.4, "stream": False
            }
            fused_response = requests.post(
                llm_endpoint, json=payload2, headers={"Content-Type": "application/json"}, timeout=90
            )
            if fused_response.status_code == 200:
                result = fused_response.json()
                answer = result['choices'][0]['message']['content']
            else:
                answer = "抱歉，LLM服务暂时不可用。"
            # -------- Sources --------
            sources = []
            if search_results:
                for result in search_results:
                    sources.append({
                        "content": result.content,
                        "title": result.title or "未知文档",
                        "page": result.page,
                        "score": result.score,
                        "document_id": result.document_id
                    })
            else:
                for i, context in enumerate(contexts):
                    sources.append({
                        "content": context,
                        "title": f"文档片段 {i+1}",
                        "page": 1,
                        "score": 0.8,
                        "document_id": f"fragment_{i+1}"
                    })
            return RAGAnswer(
                answer=answer,
                sources=sources,
                confidence=0.8,
                total_contexts=len(contexts)
            )
        except Exception as e:
            logger.error(f"答案生成失败: {e}")
            return RAGAnswer(
                answer="抱歉，生成答案时出现错误。",
                sources=[],
                confidence=0.0,
                total_contexts=0
            )

    def get_status(self) -> dict:
        """获取RAG服务状态"""
        try:
            # 获取文档数量
            client = self.weaviate_connection.get_client()
            collection = client.collections.get("PDFDocument")
            
            # 获取集合统计信息
            aggregate_response = collection.aggregate.over_all(
                total_count=True
            )
            document_count = aggregate_response.total_count or 0
            
            # 测试连接状态
            weaviate_connected = self.test_connection()
            
            # 测试LLM连接并获取模型名称
            llm_connected = False
            model_name = "未知"
            try:
                import requests
                response = requests.get('http://localhost:11434/api/tags', timeout=10)
                if response.status_code == 200:
                    llm_connected = True
                    models = response.json().get('models', [])
                    if models:
                        # 获取第一个模型的名称
                        model_name = models[0].get('name', '未知')
                    else:
                        model_name = "无可用模型"
                else:
                    model_name = "连接失败"
            except Exception as e:
                model_name = f"连接错误: {str(e)}"
            
            return {
                "document_count": document_count,
                "weaviate_connected": weaviate_connected,
                "llm_connected": llm_connected,
                "is_initialized": self.is_initialized,
                "model": model_name
            }
            
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return {
                "document_count": 0,
                "weaviate_connected": False,
                "llm_connected": False,
                "is_initialized": False,
                "model": f"错误: {str(e)}"
            }

    def ask_question(self, question: str, top_k: int = 5, use_multi_pass: bool = False) -> RAGAnswer:
        """
        Ask a question and get an answer using RAG
        
        Args:
            question: The question to ask
            top_k: Number of top results to retrieve
            use_multi_pass: Whether to use multi-pass processing (currently not implemented)
            
        Returns:
            RAGAnswer object containing the answer and sources
        """
        try:
            if not self.is_initialized:
                raise ValueError("RAG service not initialized")
            
            # Perform vector search
            search_results = self.vector_search(question, top_k=top_k)
            
            # Generate answer using the search results
            contexts = [result.content for result in search_results]  # 提取内容字符串
            answer = self.generate_answer(question, contexts, search_results=search_results, use_multi_pass=use_multi_pass)
            
            return answer
            
        except Exception as e:
            logger.error(f"Error in ask_question: {str(e)}")
            return RAGAnswer(
                answer=f"抱歉，处理您的问题时出现错误: {str(e)}",
                sources=[],
                confidence=0.0,
                total_contexts=0
            )
