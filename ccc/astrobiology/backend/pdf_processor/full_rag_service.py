"""Full RAG service combining hybrid retrieval and cross-encoder rerank."""

import os

# Reduce noisy tqdm progress output from underlying SDKs (must be set before importing weaviate)
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
import requests
import json
import re
from typing import Iterable, List, Dict, Any, Optional
from dataclasses import dataclass
import weaviate

from .rag_service import SearchResult, RAGAnswer
from .hybrid_search_service import hybrid_search_service, HybridSearchResult
from .reranker_service import reranker_service, RerankedResult
from .confidence_calculator import confidence_calculator, ConfidenceMetrics
from .extraction_schema import (
    CONTAMINATION_EXCLUSION_PROMPT_GUIDANCE,
    EXTRACTION_OUTPUT_SCHEMA_JSON,
    get_organic_compounds_prompt_guidance,
    normalize_extraction_payload,
)

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


class FullRAGService:
    """完整的 RAG 服务，包含混合检索与交叉编码重排序"""

    def __init__(self):
        self.embedding_service = None
        self.weaviate_connection = None
        self._is_initialized = False
        self.collection_name = "PDFDocument"
        self.ollama_base_url = "http://localhost:11434"
        self._ollama_connection_checked = False
        self._ollama_available = None
        self.last_search_budget: Dict[str, Any] = {}

    def initialize(self) -> bool:
        try:
            if not self.embedding_service:
                from .embedding_service import embedding_service
                self.embedding_service = embedding_service

            if not self.weaviate_connection:
                from .weaviate_connection import weaviate_connection
                self.weaviate_connection = weaviate_connection

            if not self.embedding_service or not self.embedding_service._model:
                logger.error("嵌入服务不可用")
                return False

            if not self.weaviate_connection.test_connection():
                logger.error("Weaviate连接失败")
                return False

            self._is_initialized = True
            logger.info("RAG服务初始化成功")
            return True

        except Exception as e:
            logger.error(f"服务初始化失败: {e}")
            return False

    def search(
        self,
        query: str,
        limit: int = 5,
        use_hybrid: bool = True,
        use_rerank: bool = True,
        allowed_document_ids: Optional[Iterable[Any]] = None,
    ) -> List[SearchResult]:
        if not self._is_initialized:
            raise RAGException("服务未初始化", "SERVICE_NOT_INITIALIZED")

        try:
            logger.info("[full-rag] STEP0 query='%s' limit=%s", query[:60], limit)
            normalized_allowed_ids = None
            remaining_docs = None
            effective_limit = max(1, int(limit))
            if allowed_document_ids is not None:
                normalized_allowed_ids = {
                    str(document_id)
                    for document_id in allowed_document_ids
                    if document_id not in (None, "")
                }
                remaining_docs = len(normalized_allowed_ids)
                if remaining_docs == 0:
                    self.last_search_budget = {
                        "requested_limit": limit,
                        "effective_limit": 0,
                        "remaining_docs": 0,
                        "candidate_limit": 0,
                        "rerank_top_k": 0,
                    }
                    return []
                effective_limit = min(effective_limit, remaining_docs)

            # Weaviate 的最大结果数限制通常是 10000，我们需要确保不超过这个限制
            # 对于大量检索，我们使用 10000 作为初始候选数，然后通过 rerank 筛选
            WEAVIATE_MAX_LIMIT = 10000
            initial_candidate_limit = min(effective_limit * 3, WEAVIATE_MAX_LIMIT)
            if remaining_docs is not None:
                initial_candidate_limit = min(initial_candidate_limit, max(effective_limit, remaining_docs * 3))
            self.last_search_budget = {
                "requested_limit": limit,
                "effective_limit": effective_limit,
                "remaining_docs": remaining_docs,
                "candidate_limit": initial_candidate_limit,
                "rerank_top_k": 0,
            }
            
            if use_hybrid:
                logger.info("[full-rag] STEP1 开始混合检索 target=%s (实际请求数=%s)", limit * 3, initial_candidate_limit)
                hybrid_results = hybrid_search_service.hybrid_search(
                    query,
                    initial_candidate_limit,
                    allowed_document_ids=allowed_document_ids,
                )
                logger.info("[full-rag] STEP1 完成 候选=%s", len(hybrid_results))
                search_results = hybrid_results
            else:
                logger.info("[full-rag] STEP1 使用纯向量检索 target=%s (实际请求数=%s)", limit * 3, initial_candidate_limit)
                search_results = self._fallback_vector_search(
                    query,
                    initial_candidate_limit,
                    allowed_document_ids=allowed_document_ids,
                )
                logger.info("[full-rag] STEP1 完成 候选=%s", len(search_results))

            if use_rerank and reranker_service.is_available():
                logger.info("[full-rag] STEP2 开始交叉编码重排序 候选=%s", len(search_results))
                # 对于大量检索请求（limit > 5000），rerank时对所有候选进行排序，不限制top_k
                # 这样可以获取所有相关片段而不被限制
                rerank_top_k = limit * 2 if limit <= 5000 else len(search_results)
                if remaining_docs is not None:
                    rerank_top_k = min(effective_limit * 2 if effective_limit <= 5000 else len(search_results), max(effective_limit, remaining_docs * 2))
                else:
                    rerank_top_k = effective_limit * 2 if effective_limit <= 5000 else len(search_results)
                self.last_search_budget["rerank_top_k"] = rerank_top_k
                reranked_results = reranker_service.rerank_results(query, search_results, rerank_top_k)
                logger.info("[full-rag] STEP2 完成 重排序后=%s", len(reranked_results))
                search_results = reranked_results

            # 对于大量检索请求（limit > 5000），返回所有reranked结果，不进行截断
            # 这样可以确保获取所有相关片段，而不仅仅是最前面的limit个
            if limit > 5000:
                final_results = self._convert_to_search_results(search_results)
            else:
                final_results = self._convert_to_search_results(search_results[:effective_limit])
            logger.info("[full-rag] STEP3 完成 返回=%s", len(final_results))
            return final_results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise RAGException(f"搜索失败: {str(e)}", "SEARCH_FAILED")

    def _fallback_vector_search(
        self,
        query: str,
        limit: int,
        allowed_document_ids: Optional[Iterable[Any]] = None,
    ) -> List[SearchResult]:
        try:
            query_vector = self.embedding_service.encode([query])[0]
            client = self.weaviate_connection.get_client()
            collection = client.collections.get(self.collection_name)
            normalized_allowed_ids = None
            where_filter = None
            if allowed_document_ids is not None:
                normalized_allowed_ids = {
                    str(document_id)
                    for document_id in allowed_document_ids
                    if document_id not in (None, "")
                }
                if not normalized_allowed_ids:
                    return []
                where_filter = weaviate.classes.query.Filter.any_of(
                    [
                        weaviate.classes.query.Filter.by_property("document_id").equal(document_id)
                        for document_id in sorted(normalized_allowed_ids)
                    ]
                )

            near_vector_kwargs = {
                "near_vector": query_vector,
                "limit": limit,
                "return_metadata": weaviate.classes.query.MetadataQuery(distance=True)
            }
            if where_filter is not None:
                near_vector_kwargs["where"] = where_filter
            response = collection.query.near_vector(**near_vector_kwargs)

            results = []
            for obj in response.objects:
                content = obj.properties.get('content', '')
                title = obj.properties.get('title', '') or '未知文档'
                document_id = obj.properties.get('document_id', '')
                if normalized_allowed_ids is not None and str(document_id or "") not in normalized_allowed_ids:
                    continue
                page = obj.properties.get('page_number', 0)
                score = 1.0 - (obj.metadata.distance if obj.metadata else 0.0)

                results.append(SearchResult(
                    content=content,
                    score=score,
                    metadata={
                        'document_id': document_id,
                        'page_number': page,
                        'distance': obj.metadata.distance if obj.metadata else None
                    },
                    document_id=document_id,
                    page=page,
                    title=title,
                    chunk_index=obj.properties.get('chunk_index', -1)
                ))

            return results

        except Exception as e:
            logger.error(f"降级向量搜索失败: {e}")
            return []

    def _convert_to_search_results(self, results: List[Any]) -> List[SearchResult]:
        search_results = []
        for result in results:
            if hasattr(result, 'content'):
                # RerankedResult使用final_score，其他结果类型可能使用score
                score = getattr(result, 'final_score', None)
                if score is None:
                    score = getattr(result, 'score', 0.0)
                
                search_results.append(SearchResult(
                    content=result.content,
                    score=float(score),
                    metadata=getattr(result, 'metadata', {}),
                    document_id=getattr(result, 'document_id', ''),
                    page=getattr(result, 'page', 0),
                    title=getattr(result, 'title', ''),
                    chunk_index=getattr(result, 'chunk_index', -1)
                ))
        return search_results

    def test_ollama_connection(self, force_check: bool = False) -> bool:
        """测试 Ollama 连接是否可用（带缓存，避免频繁测试）"""
        # 如果已经检查过且不强制检查，直接返回缓存结果
        if self._ollama_connection_checked and not force_check and self._ollama_available is not None:
            return self._ollama_available
        
        try:
            response = requests.get(
                f'{self.ollama_base_url}/api/tags',
                timeout=5
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                if 'llama3.1:8b-instruct-q4_K_M' in model_names:
                    logger.info(f"Ollama连接正常，模型已就绪: llama3.1:8b-instruct-q4_K_M")
                else:
                    logger.warning(f"Ollama连接正常，但模型 llama3.1:8b-instruct-q4_K_M 未找到。可用模型: {model_names}")
                self._ollama_available = True
                self._ollama_connection_checked = True
                return True
            else:
                logger.warning(f"Ollama API响应异常: status={response.status_code}")
                self._ollama_available = False
                self._ollama_connection_checked = True
                return False
        except requests.exceptions.ConnectionError:
            if not self._ollama_connection_checked or force_check:
                logger.error("无法连接到Ollama服务，请确保Ollama正在运行 (ollama serve)")
            self._ollama_available = False
            self._ollama_connection_checked = True
            return False
        except requests.exceptions.Timeout:
            if not self._ollama_connection_checked or force_check:
                logger.error("Ollama连接超时")
            self._ollama_available = False
            self._ollama_connection_checked = True
            return False
        except Exception as e:
            if not self._ollama_connection_checked or force_check:
                logger.error(f"Ollama连接测试失败: {e}")
            self._ollama_available = False
            self._ollama_connection_checked = True
            return False
    
    def extract_meteorite_data(
        self,
        content: str,
        *,
        strict_organics_prompt: bool = False,
    ) -> Optional[MeteoriteData]:
        try:
            # 先测试 Ollama 连接（使用缓存，避免每次都测试）
            if not self.test_ollama_connection():
                # 如果缓存显示不可用，强制再检查一次（可能服务刚启动）
                if not self.test_ollama_connection(force_check=True):
                    logger.error("Ollama服务不可用，无法提取数据。请确保: 1) Ollama正在运行 (ollama serve), 2) 模型已下载 (ollama pull llama3.1:8b-instruct-q4_K_M)")
                    return None
            
            # 预处理内容：移除明显的论文标题、作者信息等噪声
            content_cleaned = self._clean_segment_content(content)
            
            # 基于128K上下文估算：128K tokens ≈ 约100K字符（英文）
            # 考虑到prompt本身也需要tokens，保留约80K字符的内容空间
            # 这足以处理多个完整chunk（每个chunk最多15K字符）
            MAX_CONTENT_LENGTH = 80000  # 约对应64K tokens，留出空间给prompt和响应
            if len(content_cleaned) > MAX_CONTENT_LENGTH:
                logger.info(f"内容较长 ({len(content_cleaned)} 字符)，截取前{MAX_CONTENT_LENGTH}字符进行提取（LLM支持128K上下文）")
                content_preview = content_cleaned[:MAX_CONTENT_LENGTH]
            else:
                content_preview = content_cleaned
            
            good_example = json.dumps(
                {
                    "name": "Murchison",
                    "classification": "CM2",
                    "discovery_location": "Australia",
                    "origin": "",
                    "organic_compounds": ["amino acids"],
                    "contamination_exclusion_method": "",
                    "references": [],
                },
                ensure_ascii=False,
            )
            generic_organic_example = json.dumps(
                {
                    "name": "Orgueil",
                    "classification": "CI1",
                    "discovery_location": "",
                    "origin": "",
                    "organic_compounds": [],
                    "contamination_exclusion_method": "",
                    "references": [],
                },
                ensure_ascii=False,
            )
            organic_guidance = get_organic_compounds_prompt_guidance(strict=strict_organics_prompt)

            prompt = f"""Extract meteorite data from this text fragment. Return ONLY valid JSON.

CRITICAL RULES:
- "name": ONLY actual meteorite names (e.g., "Murchison", "ALH 84001", "Nakhla"). NEVER:
  * Document IDs (e.g., "0004-637X", "0004-637X 783 2 140")
  * Classification codes alone (e.g., "CM2", "CR2" - these go in classification field!)
  * Paper titles (e.g., "Concerns of Organic Contamination...", "Synthesis of...")
  * Names >80 chars or >10 words
- If no specific meteorite name exists, use "" for name field.
- If fragment has only metadata/titles/references, return all empty fields.
- {organic_guidance}
- {CONTAMINATION_EXCLUSION_PROMPT_GUIDANCE}

Return JSON matching this schema exactly:
{EXTRACTION_OUTPUT_SCHEMA_JSON}
For example, use "organic_compounds": ["amino acids"] and use [] when no organic compounds are mentioned.
Example JSON: {good_example}
Any legacy example that shows "organic_compounds" as an object is invalid. Always return a JSON array of strings.

Examples:
Good: "The Murchison meteorite, a CM2 that fell in Australia, contains amino acids."
-> {{"name": "Murchison", "classification": "CM2", "discovery_location": "Australia", "origin": "", "organic_compounds": ["amino acids"], "contamination_exclusion_method": "", "references": []}}
Good: "The Orgueil meteorite contains indigenous organics and an organic inventory, but no specific compounds are named."
-> {generic_organic_example}

Wrong: Document ID "0004-637X 783 2 140" -> name must be ""
Wrong: Classification "CM2" alone -> name must be "", put CM2 in classification field
Wrong: Paper title "Concerns of Organic..." -> name must be ""

Text fragment:
{content_preview}"""

            response = requests.post(
                f'{self.ollama_base_url}/v1/chat/completions',
                json={
                    "model": "llama3.1:8b-instruct-q4_K_M",
                    "messages": [
                        {"role": "system", "content": "You are a professional astrobiology assistant. Always respond with valid JSON only, no markdown formatting."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.0  # 使用0温度以最大化JSON格式稳定性
                },
                timeout=90  # 增加超时时间到90秒
            )

            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content'].strip()

                # 尝试提取JSON（可能包含在markdown代码块中）
                json_str = self._extract_json_from_response(answer)
                
                # 多轮尝试解析JSON
                data = None
                parse_errors = []
                
                # 第一轮：直接解析
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    parse_errors.append(f"直接解析失败: {e}")
                    
                    # 第二轮：尝试修复常见问题
                    try:
                        # 尝试修复未转义的换行符（在某些情况下可能出现）
                        fixed_json = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
                        # 但保留在字符串值中的合法转义
                        fixed_json = re.sub(r'\\n(?!")', ' ', fixed_json)  # 移除不在引号内的换行
                        data = json.loads(fixed_json)
                    except (json.JSONDecodeError, Exception) as e2:
                        parse_errors.append(f"修复后解析失败: {e2}")
                        logger.debug(f"[extract] JSON修复尝试失败: {e2}, 修复后的JSON: {fixed_json[:200]}")
                        
                        # 第三轮：尝试提取第一个完整的JSON对象（如果有多余内容）
                        try:
                            # 找到第一个 { 和匹配的 }
                            brace_count = 0
                            start_idx = json_str.find('{')
                            if start_idx >= 0:
                                for i in range(start_idx, len(json_str)):
                                    if json_str[i] == '{':
                                        brace_count += 1
                                    elif json_str[i] == '}':
                                        brace_count -= 1
                                        if brace_count == 0:
                                            partial_json = json_str[start_idx:i+1]
                                            data = json.loads(partial_json)
                                            logger.info(f"[extract] 通过部分提取成功解析JSON")
                                            break
                        except (json.JSONDecodeError, Exception) as e3:
                            parse_errors.append(f"部分提取失败: {e3}")
                            logger.warning(f"[extract] LLM返回的JSON解析失败，已尝试3种方法: {parse_errors}")
                            json_preview_safe = json_str[:500].encode("ascii", errors="replace").decode("ascii")
                            answer_preview_safe = answer[:500].encode("ascii", errors="replace").decode("ascii")
                            logger.info(f"[extract] 尝试解析的JSON (前500字符): {json_preview_safe}")
                            logger.info(f"[extract] 原始响应 (前500字符): {answer_preview_safe}")
                            logger.debug(f"[extract] 原始内容预览: {content_preview[:300]}")
                
                if data and isinstance(data, dict) and data != {}:
                    # 验证必需字段并检查名称质量
                    try:
                        # 检查名称质量：拒绝明显是论文标题、文档ID、分类代码的名称
                        normalized_data = normalize_extraction_payload(data)
                        name = str(data.get('name') or '').strip()
                        name_is_valid = True
                        if name:
                            # 名称验证：拒绝论文标题、文档ID、分类代码等无效名称
                            invalid_patterns = [
                                # 1. 长度相关
                                len(name) > 80,  # 名称过长（很可能是论文标题）
                                len(name.split()) > 10,  # 单词数超过10个（很可能是句子/标题）
                                name.count(' ') > 8,  # 空格太多（可能是句子）
                                
                                # 2. 文档ID/期刊代码格式
                                re.match(r'^[0-9]{4}[-]?[0-9]{3,4}X', name),  # "0004-637X" 或 "0004637X"
                                re.match(r'^[A-Z0-9]+[-][0-9]+[-][0-9]+', name),  # "S0960-9822(96)00698-7"
                                re.match(r'^[a-z]+[0-9]+[-][0-9]+', name.lower()),  # "isms-2018-TL03"
                                re.match(r'^[0-9]+\s+[0-9]+\s+[0-9]+$', name),  # "783 2 140" (期刊页码)
                                
                                # 3. 分类代码单独作为名称（不是真正的陨石名称）
                                name.upper() in ['CM2', 'CR2', 'CI', 'CI1', 'CM1', 'CV3', 'CO3', 'H5', 'L6', 'SNC', 'HED', 'AUB'],
                                name.upper() in ['CHONDRITE', 'METEORITE', 'MARTIAN', 'LUNAR'],  # 通用类型词
                                
                                # 4. 论文标题特征词
                                any(word in name.lower() for word in [
                                    'exploring', 'investigation', 'analysis', 'assessment', 'evaluation',
                                    'synthesis of', 'concerns of', 'implications for', 'effects of',
                                    'mechanisms of', 'study of', 'research on', 'paper on',
                                    'irradiation of', 'titans surface', 'solid organics',
                                    'rapid communication', 'community assembly', 'cataclysm',
                                    'coldtrapped', 'reply to comment', 'academic paper'
                                ]),
                                
                                # 5. 以常见论文标题开头且较长
                                any(name.lower().startswith(prefix) for prefix in [
                                    'irradiation', 'titans', 'concerns', 'solid', 'rapid',
                                    'community', 'cataclysm', 'coldtrapped', 'reply', 'academic',
                                    'evaluation', 'assessment', 'investigation', 'analysis',
                                    'effects of', 'mechanisms of', 'implications for',
                                    'synthesis of', 'exploring', 'study of', 'research on'
                                ]) and len(name) > 40,
                                
                                # 6. 其他常见无效模式
                                name.lower().startswith(('the ', 'a ', 'an ')) and len(name) > 50,
                                'microsoft' in name.lower(),
                                'word' in name.lower() and 'docx' in name.lower(),
                                name == 'meteorite',
                                'paper' in name.lower() or 'article' in name.lower() or 'study' in name.lower(),
                                name.startswith('NO. ') or name.startswith('PAGES '),
                                # 包含DOI特征
                                'doi:' in name.lower() or 'doi ' in name.lower(),
                                # 包含URL特征
                                'http://' in name.lower() or 'https://' in name.lower(),
                            ]
                            
                            if any(invalid_patterns):
                                name_is_valid = False
                                logger.info(f"[extract] 名称 '{name[:60]}...' 被识别为无效（论文标题/文档ID/分类代码），拒绝此数据")
                        
                        # 检查主要字段（名称必须是有效的）
                        main_fields = ['classification', 'discovery_location', 'origin']
                        has_main_field = any(normalized_data.get(k) for k in main_fields)
                        
                        # 检查次要字段（有机化合物、方法等）
                        has_secondary_field = False
                        if normalized_data.get('organic_compounds'):
                            has_secondary_field = True
                        
                        if normalized_data.get('contamination_exclusion_method'):
                            has_secondary_field = True
                        
                        # 接受条件：
                        # 1. 如果名称明显是论文标题，拒绝此数据（即使有其他字段）
                        # 2. 如果有有效名称，接受
                        # 3. 如果没有名称但有其他有效信息，也接受（名称可以为空）
                        if not name_is_valid and name:
                            # 名称无效（是论文标题），拒绝此数据
                            logger.info(f"[extract] 拒绝数据：名称为论文标题，即使有其他字段也不接受")
                            logger.info(f"[extract] 无效名称: {name[:60]}")
                            logger.debug(f"[extract] JSON内容: {json_str[:300]}")
                        elif name_is_valid and normalized_data.get('name'):
                            # 有有效名称，即使其他字段为空也接受
                            return MeteoriteData(**normalized_data)
                        elif has_main_field or has_secondary_field:
                            # 没有名称但有其他有效信息，也接受（名称可以为空）
                            return MeteoriteData(**normalized_data)
                        else:
                            # 所有字段都为空 - 这可能是正常的（片段确实没有陨石数据）
                            logger.info(f"[extract] 提取的数据质量不足：名称为空或无效，且无其他有效字段")
                            logger.info(f"[extract] JSON内容: {json_str[:300]}")
                            # 记录片段内容的前500字符用于诊断（清理特殊字符以避免编码错误）
                            preview_safe = content_preview[:500].encode('ascii', errors='replace').decode('ascii')
                            logger.info(f"[extract] 片段内容预览（前500字符）: {preview_safe}")
                            logger.info(f"[extract] [注意] 如果所有字段为空，可能是片段本身不包含陨石数据（如元数据、参考文献等），这是正常的")
                    except (TypeError, ValueError) as e:
                        logger.warning(f"[extract] 数据验证失败: {e}, JSON: {json_str[:300]}")
                        logger.debug(f"[extract] 原始内容预览: {content_preview[:200]}")
                elif data:
                    logger.info(f"[extract] 提取的数据不是有效字典，类型: {type(data)}, 内容: {json_str[:200]}")
                else:
                    answer_safe = answer[:300].encode("ascii", errors="replace").decode("ascii")
                    logger.info(f"[extract] LLM返回了空数据或无效JSON，原始响应: {answer_safe}")
            else:
                logger.error(f"Ollama API请求失败: status={response.status_code}, response={response.text[:200]}")

            return None

        except requests.exceptions.Timeout:
            logger.warning(f"[extract] Ollama API请求超时（90秒），内容长度: {len(content)} 字符")
            logger.debug(f"[extract] 超时内容预览: {content[:200]}")
            # 对于超时的内容，可以考虑截取更少的内容重试，但当前先记录
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API请求异常: {e}")
            return None
        except Exception as e:
            logger.error(f"数据提取失败: {e}", exc_info=True)
            return None
    
    def _clean_segment_content(self, content: str) -> str:
        """
        清理片段内容，移除论文标题、作者、期刊信息等噪声，只保留核心数据
        
        Args:
            content: 原始片段内容
            
        Returns:
            清理后的内容
        """
        lines = content.split('\n')
        cleaned_lines = []
        
        # 更严格的清理：跳过前10行中的噪声
        skip_noise_lines = 10
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                cleaned_lines.append('')
                continue
            
            # 跳过前N行的噪声
            if i < skip_noise_lines:
                # 检测论文标题（更全面的关键词）
                title_keywords = [
                    'exploring', 'investigation', 'analysis', 'assessment', 'evaluation',
                    'irradiation', 'titans surface', 'concerns of', 'solid organics',
                    'rapid communication', 'community assembly', 'cataclysm',
                    'effects of', 'mechanisms of', 'implications for', 'chiroptical',
                    'fingerprinting', 'photochemistry', 'reanalysis', 'renaissance',
                    'mystery of', 'integrated', 'hierarchical', 'astrovirology',
                    'received:', 'revised:', 'accepted:', 'published:', 'licensee'
                ]
                
                # 检测是否是论文标题
                is_title = (
                    len(line_stripped) > 20 and len(line_stripped) < 300 and
                    (
                        any(keyword in line_stripped.lower() for keyword in title_keywords) or
                        # 检测标题特征：首字母大写的长句子
                        (line_stripped[0].isupper() and len(line_stripped.split()) > 8 and 
                         line_stripped.count(' ') > 5 and not line_stripped.endswith('.'))
                    )
                )
                
                # 检测作者名模式（更严格）
                is_author = (
                    re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+et\s+al\.)?$', line_stripped) or
                    re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+.*(?:LLC|University|Department|Laboratory|Technologies)', line_stripped) or
                    'and' in line_stripped and len(line_stripped.split()) <= 10 and
                    all(word[0].isupper() if word else False for word in line_stripped.split())
                )
                
                # 检测期刊/日期/引用信息
                is_metadata = (
                    'doi:' in line_stripped.lower() or
                    'http://' in line_stripped.lower() or
                    'https://' in line_stripped.lower() or
                    re.search(r'^\d{4}\s*[,.]', line_stripped) or  # 年份开头
                    re.search(r'\d{4}[,\s]+\d+[,\s]+\d+', line_stripped) or  # 日期格式
                    re.search(r'[A-Z]+\s+\d+[,\s]+\d+', line_stripped) or  # 期刊格式 "Journal 1, 234, 567"
                    re.match(r'^[a-z]+\.[a-z]+\.\d+\.\d+\.\d+', line_stripped.lower()) or  # DOI格式 "j.icarus.2015.02.008"
                    re.match(r'^[a-z]+-\d+-\d+-[a-z]+', line_stripped.lower()) or  # "acp-5-207-2005"
                    re.match(r'^[a-z]+\d+\.\d+', line_stripped.lower()) or  # "isms.2018.TL03"
                    re.match(r'^[a-z]+\d+\.\d+', line_stripped.lower()) or  # "njg.2015.3"
                    re.match(r'^[a-z]+\d+[a-z]$', line_stripped.lower()) or  # "x5039v"
                    re.match(r'^\d+\.\d+', line_stripped) or  # "1.4948783"
                    'abstract' in line_stripped.lower() or
                    'introduction' in line_stripped.lower()
                )
                
                # 检测是否是句子片段（不完整的句子，可能是误提取）
                is_fragment = (
                    len(line_stripped) > 100 and
                    line_stripped.lower().startswith(('almost', 'under', 'along', 'however', 'therefore', 'furthermore')) and
                    not line_stripped.endswith('.') and
                    line_stripped.count('.') < 2
                )
                
                if is_title or is_author or is_metadata or is_fragment:
                    logger.debug(f"[clean] 跳过噪声行 {i+1}: {line_stripped[:60]}...")
                    continue
            
            cleaned_lines.append(line)
        
        cleaned_content = '\n'.join(cleaned_lines)
        
        # 如果清理后内容太短（可能过度清理），返回原始内容但添加警告
        if len(cleaned_content.strip()) < len(content.strip()) * 0.3:
            logger.warning(f"[clean] 清理后内容过短（{len(cleaned_content)}/{len(content)}字符），可能片段质量很差")
            return content

        return cleaned_content
    
    def _extract_json_from_response(self, text: str) -> str:
        """从响应中提取JSON字符串（处理markdown代码块等格式）"""
        import re
        text = text.strip()
        
        # 如果包含```json或```代码块，提取其中的内容
        if '```json' in text:
            start = text.find('```json') + 7
            end = text.find('```', start)
            if end > start:
                text = text[start:end].strip()
        elif '```' in text:
            start = text.find('```') + 3
            end = text.find('```', start)
            if end > start:
                text = text[start:end].strip()
        
        # 如果还没有找到，尝试直接找到第一个 { 和最后一个 }
        if text.startswith('{'):
            start = 0
        else:
            start = text.find('{')
        if start >= 0:
            # 找到最后一个 }
            end = text.rfind('}')
            if end > start:
                text = text[start:end+1]
        
        # 清理控制字符（保留换行和制表符，移除其他控制字符）
        # JSON规范允许的空白字符：\t, \n, \r, 空格
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        return text

    def ask_question(self, question: str) -> RAGAnswer:
        try:
            search_results = self.search(question, limit=3)

            if not search_results:
                return RAGAnswer(
                    answer="Sorry, no relevant information found.",
                    sources=[],
                    confidence=0.0,
                    total_contexts=0
                )

            confidence_metrics = confidence_calculator.calculate_dynamic_confidence(
                search_results, question, use_rerank=True
            )

            adjusted_confidence = min(1.0, confidence_metrics.overall_confidence * 1.1)

            contexts = [result.content for result in search_results]
            answer = self._generate_answer(question, contexts)

            sources = self._build_sources_with_usage(search_results, answer)

            return RAGAnswer(
                answer=answer,
                sources=sources,
                confidence=adjusted_confidence,
                total_contexts=len(contexts)
            )

        except Exception as e:
            logger.error(f"问答失败: {e}")
            return RAGAnswer(
                answer=f"An error occurred while processing the question: {str(e)}",
                sources=[],
                confidence=0.0,
                total_contexts=0
            )

    def _generate_answer(self, question: str, contexts: List[str]) -> str:
        fallback_msg = "The provided documents do not contain information about this topic. Please try rephrasing your question or adding relevant documents."
        try:
            context_text = "\n\n".join([f"Document fragment {i+1}:\n{ctx}" for i, ctx in enumerate(contexts)])

            prompt = f"""You are a professional astrobiology assistant. Answer ONLY with information from the document fragments.

Document content:
{context_text}

Question: {question}

Output format (English, no code fences):
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
- If the fragments do NOT contain the answer, reply exactly: "The provided documents do not contain information about this topic. Please try rephrasing your question or adding relevant documents."
- Do NOT invent information; only use what appears in the fragments.
- Always cite fragment numbers as [S#] that correspond to "Document fragment <#>" above."""

            # 测试连接（仅在必要时）
            if not self.test_ollama_connection():
                return "抱歉，LLM服务当前不可用，无法生成答案。"
            
            response = requests.post(
                f'{self.ollama_base_url}/v1/chat/completions',
                json={
                    "model": "llama3.1:8b-instruct-q4_K_M",
                    "messages": [
                        {"role": "system", "content": "You are a professional astrobiology assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 700,
                    "temperature": 0.1,
                    "top_p": 1
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                answer_text = result['choices'][0]['message']['content']
                return self._validate_and_clean_answer(answer_text, len(contexts), fallback_msg)

            return "No answer available."

        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return "An error occurred while generating the answer."

    def _validate_and_clean_answer(self, answer: str, max_index: int, fallback_msg: str) -> str:
        """确保引用编号与现有片段匹配；如果出现缺失引用或缺少引用标注则返回统一的不可用句式"""
        try:
            text = answer or ""
            lower_text = text.lower()
            if "snippet missing" in lower_text or "missing snippet" in lower_text:
                return fallback_msg
            citations = [int(c) for c in re.findall(r"\[s(\d+)\)", text, flags=re.IGNORECASE)]
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

    def _build_sources_with_usage(self, results, answer_text: str):
        """返回全部片段，并标记是否被引用，供前端区分已用/可用"""
        try:
            citations = {int(c) for c in re.findall(r"\[s(\d+)\]", answer_text or "", flags=re.IGNORECASE)}
            filtered_sources = []
            for idx, result in enumerate(results, start=1):
                filtered_sources.append({
                    "content": result.content,
                    "title": result.title,
                    "page": int(result.page) if result.page is not None else 0,
                    "score": float(result.score) if result.score is not None else 0.0,
                    "document_id": result.document_id,
                    "used": idx in citations
                })
            return filtered_sources
        except Exception as e:
            logger.error(f"构建引用sources失败: {e}")
            return []


full_rag_service = FullRAGService()
