"""
陨石数据提取器
从PDF论文中提取符合数据库格式的陨石数据
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

# 导入新的智能系统
from .intelligent_meteorite_extraction_system import IntelligentMeteoriteExtractionSystem, ExtractionResult

logger = logging.getLogger(__name__)

@dataclass
class MeteoriteData:
    """陨石数据结构"""
    name: str
    classification: str
    discovery_location: str
    origin: str
    organic_compounds: Dict[str, Any]
    contamination_exclusion_method: str
    references: List[Dict[str, str]]
    confidence_score: float = 0.0
    extraction_notes: str = ""

class MeteoriteDataExtractor:
    """陨石数据提取器"""
    
    # 专门的数据提取Prompt模板
    EXTRACTION_PROMPT_TEMPLATE = """You are a meteorite data extraction specialist. Your task is to extract structured meteorite data from scientific text.

CRITICAL INSTRUCTIONS:
1. If the text is NOT specifically about meteorites (space rocks, meteorite samples, meteorite analysis), return EXACTLY: null
2. If the text mentions meteorites but contains NO specific meteorite data (names, classifications, locations, compounds), return EXACTLY: null
3. If the text IS about meteorites and contains specific meteorite data, extract it and return EXACTLY the JSON format below.
4. DO NOT summarize the text content. DO NOT return true/false statements about the content.
5. DO NOT return bibliographic information, author details, or paper abstracts.
6. ONLY extract actual meteorite specimen data (names, classifications, locations, compounds found).

REQUIRED JSON FORMAT (return EXACTLY this structure):
{{
    "name": "specific meteorite name or Unknown",
    "classification": "meteorite classification (e.g., H4, L5, CM2) or Unknown", 
    "discovery_location": "specific location where found or Unknown",
    "origin": "parent body or origin information or Unknown",
    "organic_compounds": {{
        "amino_acids": ["list specific amino acids found, or empty array"],
        "carboxylic_acids": ["list specific carboxylic acids found, or empty array"],
        "aromatic_compounds": ["list specific aromatic compounds found, or empty array"],
        "aliphatic_compounds": ["list specific aliphatic compounds found, or empty array"],
        "nucleotide_bases": ["list specific nucleotide bases found, or empty array"],
        "other_organics": ["list other organic compounds found, or empty array"],
        "total_organic_carbon": "specific TOC value with units or Not specified",
        "isotopic_signatures": {{
            "carbon_isotope_ratio": "specific δ13C value or Not specified",
            "nitrogen_isotope_ratio": "specific δ15N value or Not specified"
        }}
    }},
    "contamination_exclusion_method": "specific method used to exclude contamination or Not specified",
    "references": []
}}

TEXT TO ANALYZE:
{context}

RESPOND WITH ONLY THE JSON OBJECT - NO OTHER TEXT, NO EXPLANATIONS, NO MARKDOWN:"""

    VALIDATION_PROMPT = """Review the following extracted meteorite data for accuracy and completeness:

{extracted_data}

**VALIDATION CHECKLIST:**
1. Are all required fields present?
2. Is the JSON structure valid?
3. Are the organic compounds specific (not just categories)?
4. Is the contamination exclusion method described?
5. Are references complete and properly formatted?

**CORRECTIONS NEEDED:**
- Fix any JSON syntax errors
- Replace generic terms with specific compound names
- Ensure all fields follow the required format
- Add missing required information if available in source

Provide the corrected JSON data:"""

    def __init__(self, rag_service: Optional[Any] = None):
        """初始化数据提取器"""
        self.rag_service = rag_service
        
        # 初始化新的智能系统
        self.intelligent_system = IntelligentMeteoriteExtractionSystem(rag_service)
        
        # 保持向后兼容的统计信息
        self.extraction_stats: Dict[str, int] = {
            'total_extractions': 0,
            'successful_extractions': 0,
            'validation_failures': 0,
            'high_confidence_extractions': 0,
            'medium_confidence_extractions': 0,
            'low_confidence_extractions': 0
        }

    def extract_meteorite_data(self, context: str, source_info: Optional[Dict[str, str]] = None) -> Optional[MeteoriteData]:
        """
        从文本中提取陨石数据
        
        Args:
            context: 源文本内容
            source_info: 源文档信息
            
        Returns:
            提取的陨石数据或None
        """
        try:
            self.extraction_stats['total_extractions'] += 1
            
            # 直接传递纯文本内容，不使用模板格式化
            print(f"待分析文本: {context[:500]}...")  # 调试信息
            
            # 使用RAG服务进行数据提取
            if self.rag_service:
                print("开始调用LLM...")  # 调试信息
                response = self._call_llm_for_extraction(context)  # 直接传递纯文本
                print(f"LLM响应: {repr(response)}")  # 调试信息
                if response:
                    # 解析JSON响应
                    meteorite_data = self._parse_extraction_response(response, original_context=context)
                    if meteorite_data:
                        # 添加源信息
                        if source_info:
                            meteorite_data.references.append({
                                'title': source_info.get('title', 'Unknown'),
                                'authors': source_info.get('authors', 'Unknown'),
                                'journal': source_info.get('journal', 'Unknown'),
                                'year': source_info.get('year', 'Unknown'),
                                'doi': source_info.get('doi', 'Unknown')
                            })
                        
                        self.extraction_stats['successful_extractions'] += 1
                        return meteorite_data
                else:
                    print("LLM返回空响应")  # 调试信息
            else:
                print("RAG服务未初始化")  # 调试信息
            
            return None
            
        except Exception as e:
            print(f"数据提取异常: {repr(e)}")  # 调试信息，使用repr显示异常的完整信息
            logger.error(f"数据提取失败: {str(e)}")
            import traceback
            print(f"异常堆栈: {traceback.format_exc()}")  # 打印完整的异常堆栈
            return None

    async def extract_meteorite_data_enhanced(self, context: str, source_info: Optional[Dict[str, str]] = None) -> Optional[MeteoriteData]:
        """
        增强版陨石数据提取 - 使用新的智能系统
        
        Args:
            context: 源文本内容
            source_info: 源文档信息
            
        Returns:
            提取的陨石数据或None
        """
        try:
            # 使用新的智能系统进行提取
            result = await self.intelligent_system.extract_meteorite_data(
                content=context,
                source_info=source_info
            )
            
            if result.success and result.meteorite_data:
                # 转换为现有格式以保持向后兼容
                enhanced_data = result.meteorite_data
                
                meteorite_data = MeteoriteData(
                    name=enhanced_data.name,
                    classification=enhanced_data.classification,
                    discovery_location=enhanced_data.discovery_location,
                    origin=enhanced_data.origin,
                    organic_compounds=enhanced_data.organic_compounds,
                    contamination_exclusion_method="智能验证",
                    references=enhanced_data.source_references,
                    extraction_notes=f"置信度: {enhanced_data.extraction_confidence.overall_score:.2f}, 方法: {enhanced_data.extraction_method}"
                )
                
                # 更新统计信息
                self.extraction_stats['successful_extractions'] += 1
                confidence_score = enhanced_data.extraction_confidence.overall_score
                
                if confidence_score >= 0.8:
                    self.extraction_stats['high_confidence_extractions'] += 1
                elif confidence_score >= 0.6:
                    self.extraction_stats['medium_confidence_extractions'] += 1
                else:
                    self.extraction_stats['low_confidence_extractions'] += 1
                
                return meteorite_data
            
            # 如果智能系统提取失败，回退到原有方法
            logger.warning("智能系统提取失败，回退到原有方法")
            return self.extract_meteorite_data(context, source_info)
            
        except Exception as e:
            logger.error(f"增强版数据提取失败: {str(e)}")
            # 回退到原有方法
            return self.extract_meteorite_data(context, source_info)

    def _call_llm_for_extraction(self, prompt: str) -> Optional[str]:
        """调用LLM进行数据提取"""
        try:
            if not self.rag_service:
                logger.error("RAG服务未初始化")
                return None
            
            if not self.rag_service.is_initialized:
                logger.error("RAG服务未正确初始化")
                return None
            
            logger.info("调用LLM进行数据提取...")
            
            # 使用RAG服务的LLM端点直接调用
            import requests
            from .llama_config import Llama3Config
            
            # 获取生成参数 - 使用general_academic而不是data_extraction
            generation_params = Llama3Config.get_generation_params("general_academic")
            
            # 从全局配置获取正确的LLM端点
            from .pdf_utils import GlobalConfig
            base_llm_url = getattr(GlobalConfig, 'LLM_BASE_URL', 'http://localhost:11434')
            llm_endpoint = f"{base_llm_url.rstrip('/')}/v1/chat/completions"
            
            payload = {
                "model": "llama3.1:8b-instruct-q4_K_M",
                "messages": [
                    {"role": "system", "content": """You are a meteorite data extraction specialist. Your task is to extract structured meteorite data from scientific text.

CRITICAL INSTRUCTIONS:
1. If the text is NOT specifically about meteorites (space rocks, meteorite samples, meteorite analysis), return EXACTLY: null
2. If the text mentions meteorites but contains NO specific meteorite data (names, classifications, locations, compounds), return EXACTLY: null
3. If the text IS about meteorites and contains specific meteorite data, extract it and return EXACTLY the JSON format below.
4. DO NOT summarize the text content. DO NOT return true/false statements about the content.
5. DO NOT return bibliographic information, author details, or paper abstracts.
6. ONLY extract actual meteorite specimen data (names, classifications, locations, compounds found).

REQUIRED JSON FORMAT (return EXACTLY this structure):
{
    "name": "specific meteorite name or Unknown",
    "classification": "meteorite classification (e.g., H4, L5, CM2) or Unknown", 
    "discovery_location": "specific location where found or Unknown",
    "origin": "parent body or origin information or Unknown",
    "organic_compounds": {
        "amino_acids": ["list specific amino acids found, or empty array"],
        "carboxylic_acids": ["list specific carboxylic acids found, or empty array"],
        "aromatic_compounds": ["list specific aromatic compounds found, or empty array"],
        "aliphatic_compounds": ["list specific aliphatic compounds found, or empty array"],
        "nucleotide_bases": ["list specific nucleotide bases found, or empty array"],
        "other_organics": ["list other organic compounds found, or empty array"],
        "total_organic_carbon": "specific TOC value with units or Not specified",
        "isotopic_signatures": {
            "carbon_isotope_ratio": "specific δ13C value or Not specified",
            "nitrogen_isotope_ratio": "specific δ15N value or Not specified"
        }
    },
    "contamination_exclusion_method": "specific method used to exclude contamination or Not specified",
    "references": []
}

RESPOND WITH ONLY THE JSON OBJECT OR null - NO OTHER TEXT, NO EXPLANATIONS, NO MARKDOWN:"""},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.1,  # 低温度确保一致性
                "stream": False
            }
            
            response = requests.post(
                llm_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_answer = result["choices"][0]["message"]["content"]
                
                # 添加详细的调试信息
                print(f"LLM原始响应: {repr(raw_answer)}")  # 使用print确保输出
                logger.info(f"LLM原始响应: {raw_answer[:1000]}...")
                
                if raw_answer and raw_answer.strip():
                    logger.info("LLM数据提取成功")
                    return raw_answer.strip()
                else:
                    logger.warning("LLM返回空响应")
                    return None
            else:
                logger.error(f"LLM API错误: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return None
            
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            return None

    def _parse_extraction_response(self, response: str, original_context: Optional[str] = None) -> Optional[MeteoriteData]:
        """解析LLM响应为结构化数据"""
        try:
            # 检查是否返回null（表示无陨石数据）
            if response.strip().lower() in ['null', 'none', '']:
                logger.info("LLM明确表示无陨石数据")
                return None
            
            logger.info(f"原始LLM响应: {repr(response[:1000])}")  # 显示原始响应的repr格式
            
            # 清理响应文本
            cleaned_response = self._clean_json_response(response)
            logger.info(f"清理后的JSON响应: {repr(cleaned_response[:500])}")  # 显示清理后响应的repr格式
            
            # 解析JSON
            data = json.loads(cleaned_response)
            logger.info(f"解析后的数据结构: {list(data.keys()) if isinstance(data, dict) else f'数组长度: {len(data)}'}")  # 显示JSON的键或数组长度
            
            # 如果返回的是数组，取第一个元素
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                    logger.info(f"使用数组中的第一个元素: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                else:
                    logger.warning("返回的数组为空")
                    return None
            
            # 检查是否为"无陨石数据"的响应
            if isinstance(data, dict) and data.get('no_meteorite_data'):
                logger.info("文档不包含陨石数据")
                return None
            
            # 使用统一的DataValidator进行验证
            from .data_validator import DataValidator
            validator = DataValidator()
            validation_result = validator.validate_meteorite_data(data)
            
            if validation_result.is_valid:
                # 使用验证后的清洗数据
                cleaned_data = validation_result.cleaned_data
                # 启发式补全缺失字段，尽量减少Unknown
                if original_context:
                    cleaned_data = self._heuristic_fill_missing_fields(original_context, cleaned_data)
                return MeteoriteData(
                    name=cleaned_data.get('name') or 'Unknown',
                    classification=cleaned_data.get('classification') or 'Unknown',
                    discovery_location=cleaned_data.get('discovery_location') or 'Unknown',
                    origin=cleaned_data.get('origin') or 'Unknown',
                    organic_compounds=cleaned_data.get('organic_compounds', {}),
                    contamination_exclusion_method=cleaned_data.get('contamination_exclusion_method', 'Not specified'),
                    references=cleaned_data.get('references', []),
                    confidence_score=validation_result.confidence_score,
                    extraction_notes=f"Extracted on {datetime.now().isoformat()}"
                )
            else:
                logger.warning(f"数据验证失败: {validation_result.errors}")
            
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            logger.error(f"原始响应: {response[:500]}...")  # 显示原始响应
            # 初始化cleaned_response变量，避免未绑定错误
            cleaned_response = ""
            try:
                cleaned_response = self._clean_json_response(response)
            except Exception as clean_error:
                logger.error(f"清理响应时出错: {str(clean_error)}")
            logger.error(f"清理后响应: {cleaned_response[:500]}...")  # 显示清理后响应
            
            # 检查是否是格式错误的响应（不是标准的陨石数据格式）
            if any(key in cleaned_response.lower() for key in ['organic matter is characterized', 'heterogeneity cannot be', 'cold chemistry']):
                logger.warning("LLM返回了文本摘要而不是陨石数据格式，跳过此文档")
                return None
            
            # 尝试更激进的修复
            try:
                # 如果是因为额外数据导致的错误，尝试只取第一个完整的JSON对象
                if "Extra data" in str(e):
                    logger.info("尝试修复'Extra data'错误...")
                    # 找到第一个完整的JSON对象
                    brace_count = 0
                    end_pos = 0
                    for i, char in enumerate(cleaned_response):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_pos = i + 1
                                break
                    
                    if end_pos > 0:
                        fixed_response = cleaned_response[:end_pos]
                        logger.info(f"修复后的响应: {fixed_response[:200]}...")
                        data = json.loads(fixed_response)
                        
                        # 检查是否为"无陨石数据"的响应
                        if isinstance(data, dict) and data.get('no_meteorite_data'):
                            logger.info("文档不包含陨石数据")
                            return None
                        
                        # 使用统一的DataValidator进行验证
                        from .data_validator import DataValidator
                        validator = DataValidator()
                        validation_result = validator.validate_meteorite_data(data)
                        
                        if validation_result.is_valid:
                            # 使用验证后的清洗数据
                            cleaned_data = validation_result.cleaned_data
                            if original_context:
                                cleaned_data = self._heuristic_fill_missing_fields(original_context, cleaned_data)
                            return MeteoriteData(
                                name=cleaned_data.get('name') or 'Unknown',
                                classification=cleaned_data.get('classification') or 'Unknown',
                                discovery_location=cleaned_data.get('discovery_location') or 'Unknown',
                                origin=cleaned_data.get('origin') or 'Unknown',
                                organic_compounds=cleaned_data.get('organic_compounds', {}),
                                contamination_exclusion_method=cleaned_data.get('contamination_exclusion_method', 'Not specified'),
                                references=cleaned_data.get('references', []),
                                confidence_score=validation_result.confidence_score,
                                extraction_notes=f"Extracted on {datetime.now().isoformat()}"
                            )
            except Exception as fix_error:
                logger.error(f"修复尝试失败: {str(fix_error)}")
            
            self.extraction_stats['validation_failures'] += 1
            return None
        except Exception as e:
            logger.error(f"数据解析异常: {str(e)}")
            logger.error(f"原始响应: {response[:500]}...")
            return None

    def _clean_json_response(self, response: str) -> str:
        """清理LLM响应中的非JSON内容"""
        # 移除``json\s*```
        response = re.sub(r'``json\s*', '', response)
        response = re.sub(r'```\s*$', '', response)
        response = re.sub(r'```', '', response)
        
        # 先去除首尾空白字符
        response = response.strip()
        
        # 优先查找JSON对象（从第一个{到最后一个}）
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            cleaned = json_match.group(0)
            logger.info(f"找到JSON对象: {cleaned[:200]}...")
            return cleaned
        
        # 如果没有找到JSON对象，再查找JSON数组（从第一个[到最后一个]）
        # 但只有当响应明确以[开头时才认为是数组响应
        if response.strip().startswith('['):
            array_match = re.search(r'\[.*\]', response, re.DOTALL)
            if array_match:
                cleaned = array_match.group(0)
                logger.info(f"找到JSON数组: {cleaned[:200]}...")
                return cleaned
        
        # 如果没有找到完整的JSON，尝试修复常见问题
        if response.startswith('"name"') or response.startswith('\n    "name"'):
            # 如果响应以字段名开始，说明缺少开头的{
            response = '{' + response
        
        if not response.endswith('}') and not response.endswith(']'):
            # 如果没有结束符，尝试添加
            if '{' in response:
                response = response + '}'
            elif '[' in response:
                response = response + ']'
        
        # 处理截断的JSON - 如果发现不完整的结构，尝试修复
        if response.count('{') > response.count('}'):
            # 缺少结束括号
            missing_braces = response.count('{') - response.count('}')
            response += '}' * missing_braces
            logger.info(f"修复缺少的结束括号: {missing_braces}个")
        
        if response.count('[') > response.count(']'):
            # 缺少结束方括号
            missing_brackets = response.count('[') - response.count(']')
            response += ']' * missing_brackets
            logger.info(f"修复缺少的结束方括号: {missing_brackets}个")
        
        return response

    def _heuristic_fill_missing_fields(self, context: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """基于上下文的启发式补全，尽量减少关键字段为Unknown的情况。
        仅在字段缺失或为空时尝试填充，不覆盖已有值。
        """
        try:
            if not isinstance(data, dict):
                return data

            filled = dict(data)
            text = context or ""

            # 规范化空值
            def is_missing(val: Any) -> bool:
                if val is None:
                    return True
                if isinstance(val, str) and val.strip() in ['', 'Unknown', 'Not specified']:
                    return True
                return False

            # 尝试识别常见的陨石分类模式（如 H5、L6、LL3、CM2 等）
            if is_missing(filled.get('classification')):
                class_match = re.search(r"\b(CI|CM|CO|CV|CR|CK|CH|CB|H|L|LL)\s?([1-7])\b", text, re.IGNORECASE)
                if class_match:
                    classification = f"{class_match.group(1).upper()}{class_match.group(2)}"
                    filled['classification'] = classification

            # 尝试识别名称：在包含 meteorite/chondrite 的邻近词作为候选
            if is_missing(filled.get('name')):
                name_match = re.search(r"\b([A-Z][a-zA-Z\-']{2,}\s?(?:[A-Z][a-zA-Z\-']{2,})?)\s+(?:meteorite|chondrite)\b", text)
                if name_match:
                    filled['name'] = name_match.group(1).strip()

            # 尝试识别发现地点（简单 at/in/from 后接大写开头的地名片段）
            if is_missing(filled.get('discovery_location')):
                loc_match = re.search(r"\b(?:found|discovered|collected|from|at|in)\s+([A-Z][A-Za-z\- ]{2,})(?:\.|,|;|\))", text)
                if loc_match:
                    candidate = loc_match.group(1).strip()
                    # 排除明显的非地名词
                    if len(candidate.split()) <= 6:
                        filled['discovery_location'] = candidate

            # 尝试识别起源（parent body/origin）
            if is_missing(filled.get('origin')):
                origin_match = re.search(r"\b(parent\s+body|origin)\s*[:\-]?\s*([A-Za-z0-9\- ]{3,})\b", text, re.IGNORECASE)
                if origin_match:
                    filled['origin'] = origin_match.group(2).strip()

            # 统计仍然缺失的关键字段，输出日志帮助后续优化
            missing_keys = [k for k in ['name', 'classification', 'discovery_location', 'origin'] if is_missing(filled.get(k))]
            if missing_keys:
                logger.info(f"启发式补全后仍缺失字段: {missing_keys}")

            return filled
        except Exception as e:
            logger.warning(f"启发式补全失败: {str(e)}")
            return data

    # 移除已废弃的验证方法，现在统一使用DataValidator
    # def _validate_extracted_data(self, data: Dict[str, Any]) -> bool:
    #     """已废弃：验证提取的数据是否符合要求 - 现在使用DataValidator"""
    #     pass

    # def _calculate_confidence_score(self, data: Dict[str, Any]) -> float:
    #     """已废弃：计算数据提取的置信度分数 - 现在使用DataValidator"""
    #     pass

    def get_extraction_stats(self) -> Dict[str, Any]:
        """获取提取统计信息"""
        success_rate = 0.0
        if self.extraction_stats['total_extractions'] > 0:
            success_rate = self.extraction_stats['successful_extractions'] / self.extraction_stats['total_extractions']
        
        return {
            **self.extraction_stats,
            'success_rate': success_rate
        }

    def get_system_performance(self) -> Dict[str, Any]:
        """获取系统性能信息"""
        try:
            performance = self.intelligent_system.get_system_performance()
            return {
                'total_extractions': performance.total_extractions,
                'successful_extractions': performance.successful_extractions,
                'success_rate': performance.successful_extractions / performance.total_extractions if performance.total_extractions > 0 else 0,
                'average_confidence': performance.average_confidence,
                'average_processing_time': performance.average_processing_time,
                'user_satisfaction': performance.user_satisfaction,
                'common_issues': performance.common_issues,
                'optimization_opportunities': performance.optimization_opportunities
            }
        except Exception as e:
            logger.error(f"获取系统性能失败: {str(e)}")
            return {}

    def submit_user_feedback(self, extraction_id: str, feedback_data: Dict[str, Any], user_id: str = "anonymous") -> bool:
        """提交用户反馈"""
        try:
            return self.intelligent_system.submit_user_feedback(extraction_id, feedback_data, user_id)
        except Exception as e:
            logger.error(f"提交用户反馈失败: {str(e)}")
            return False

    def optimize_system(self) -> Dict[str, Any]:
        """执行系统优化"""
        try:
            return self.intelligent_system.optimize_system()
        except Exception as e:
            logger.error(f"系统优化失败: {str(e)}")
            return {'error': str(e)}

    def batch_extract_from_documents(self, document_ids: List[str]) -> List[MeteoriteData]:
        """批量从文档中提取陨石数据"""
        extracted_data = []
        
        for doc_id in document_ids:
            try:
                # 获取文档内容
                if self.rag_service:
                    # 这里需要实现从Weaviate获取文档内容的逻辑
                    pass
                
            except Exception as e:
                logger.error(f"处理文档 {doc_id} 时出错: {str(e)}")
                continue
        
        return extracted_data


def main():
    """命令行接口"""
    import argparse
    import sys
    from .rag_service import RAGService
    from .pdf_utils import GlobalConfig
    
    parser = argparse.ArgumentParser(description='陨石数据提取工具')
    parser.add_argument('command', choices=['extract_meteorite_data'], help='要执行的命令')
    parser.add_argument('--query', required=True, help='搜索查询')
    parser.add_argument('--max-docs', type=int, default=5, help='最大文档数量')
    
    args = parser.parse_args()
    
    if args.command == 'extract_meteorite_data':
        try:
            # 初始化RAG服务
            print("初始化RAG服务...")
            rag_service = RAGService()
            
            # 确保RAG服务完全初始化
            if not rag_service.is_initialized:
                print("正在初始化RAG服务...")
                rag_service.initialize()
            
            # 初始化数据提取器
            extractor = MeteoriteDataExtractor(rag_service)
            
            # 执行向量搜索
            print(f"搜索查询: {args.query}")
            search_results = rag_service.vector_search(args.query, top_k=args.max_docs)
            
            if not search_results:
                print("未找到相关文档")
                return
            
            print(f"找到 {len(search_results)} 个相关文档片段")
            
            # 提取数据
            extracted_count = 0
            failed_count = 0
            
            for i, result in enumerate(search_results):
                print(f"\n处理文档片段 {i+1}/{len(search_results)}")
                print(f"相关性分数: {result.score}")
                
                content = result.content
                if not content:
                    print("文档内容为空，跳过")
                    continue
                
                # 提取陨石数据
                meteorite_data = extractor.extract_meteorite_data(content)
                
                if meteorite_data:
                    print(f"✓ 成功提取数据: {meteorite_data.name}")
                    print(f"  分类: {meteorite_data.classification}")
                    print(f"  发现地点: {meteorite_data.discovery_location}")
                    print(f"  置信度: {meteorite_data.confidence_score:.2f}")
                    extracted_count += 1
                else:
                    print("✗ 数据提取失败")
                    failed_count += 1
            
            # 输出统计信息
            print(f"\n=== 提取统计 ===")
            print(f"成功提取: {extracted_count}")
            print(f"提取失败: {failed_count}")
            print(f"总计处理: {len(search_results)}")
            
            # 输出提取器统计
            stats = extractor.get_extraction_stats()
            print(f"提取器统计: {stats}")
            
        except Exception as e:
            print(f"执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()