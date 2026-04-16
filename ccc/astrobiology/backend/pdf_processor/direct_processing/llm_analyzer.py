"""
LLM分析器 - 负责与LLM交互
"""

import logging
import json
import requests
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """LLM分析结果"""
    raw_response: str
    structured_data: Dict[str, Any]
    confidence: float
    analysis_notes: str = ""


class LLMAnalyzer:
    """LLM分析器 - 负责与LLM交互"""
    
    def __init__(self):
        """初始化LLM分析器"""
        self.llm_client = self._init_llm_client()
        self.prompt_templates = PromptTemplates()
        
        logger.info("LLMAnalyzer initialized")
    
    def _init_llm_client(self):
        """初始化LLM客户端"""
        # 优先使用Ollama，如果不可用则使用OpenAI
        try:
            import requests
            # 测试Ollama连接
            response = requests.get('http://localhost:11434/api/tags', timeout=5)
            if response.status_code == 200:
                logger.info("Using Ollama LLM service")
                return {
                    'type': 'ollama',
                    'base_url': 'http://localhost:11434',
                    'model': 'llama3.1:8b-instruct-q4_K_M',
                    'timeout': 300
                }
        except:
            pass
        
        # 检查OpenAI API密钥
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            logger.info("Ollama not available, using OpenAI as fallback")
            return {
                'type': 'openai',
                'api_key': openai_key,
                'model': 'gpt-3.5-turbo',
                'timeout': 300
            }
        
        # 如果都没有，使用模拟模式
        logger.warning("No LLM service available, using mock mode")
        return {
            'type': 'mock',
            'timeout': 300
        }
    
    def analyze_document(self, text: str, options: Dict[str, Any] = None) -> AnalysisResult:
        """
        分析整篇文档
        
        Args:
            text: 文档文本内容
            options: 分析选项
            
        Returns:
            AnalysisResult: 分析结果
        """
        try:
            logger.info("Starting LLM document analysis")
            
            # 检查文本长度限制
            if len(text) > 100000:  # 10万字符限制
                logger.warning(f"Text length ({len(text)}) exceeds recommended limit, truncating")
                text = text[:100000] + "...[truncated]"
            
            # 构建分析提示词
            prompt = self.prompt_templates.build_analysis_prompt(text, options)
            
            # 调用LLM
            logger.info("Sending request to LLM")
            response = self._call_llm(prompt)
            
            # 解析响应
            logger.info("Parsing LLM response")
            structured_data = self._parse_llm_response(response)
            
            # 计算置信度
            confidence = self._calculate_analysis_confidence(structured_data)
            
            result = AnalysisResult(
                raw_response=response,
                structured_data=structured_data,
                confidence=confidence,
                analysis_notes=f"Analyzed {len(text)} characters of text"
            )
            
            logger.info(f"LLM analysis completed with confidence: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {str(e)}")
            raise
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM服务
        
        Args:
            prompt: 提示词
            
        Returns:
            str: LLM响应
        """
        try:
            if self.llm_client['type'] == 'ollama':
                return self._call_ollama(prompt)
            elif self.llm_client['type'] == 'openai':
                return self._call_openai(prompt)
            elif self.llm_client['type'] == 'mock':
                return self._call_mock(prompt)
            else:
                raise Exception(f"Unsupported LLM type: {self.llm_client['type']}")
                
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            # 如果LLM调用失败，使用模拟响应
            logger.warning("LLM call failed, using mock response")
            return self._call_mock(prompt)
    
    def _call_ollama(self, prompt: str) -> str:
        """调用Ollama服务"""
        url = f"{self.llm_client['base_url']}/api/generate"
        
        payload = {
            "model": self.llm_client['model'],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,  # 降低温度以获得更一致的输出
                "top_p": 0.9,
                "max_tokens": 2000,  # 减少token数量
                "repeat_penalty": 1.1,  # 避免重复
                "stop": ["```", "---", "==="]  # 停止标记
            }
        }
        
        logger.debug(f"Sending request to Ollama: {url}")
        response = requests.post(
            url, 
            json=payload, 
            timeout=self.llm_client['timeout']
        )
        
        response.raise_for_status()
        result = response.json()
        return result.get('response', '')
    
    def _call_openai(self, prompt: str) -> str:
        """调用OpenAI服务"""
        import openai
        
        # 设置OpenAI API密钥
        openai.api_key = self.llm_client['api_key']
        
        logger.debug("Sending request to OpenAI")
        response = openai.ChatCompletion.create(
            model=self.llm_client['model'],
            messages=[
                {"role": "system", "content": "You are a scientific document analysis assistant specializing in astrobiology and meteorite research."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000,
            timeout=self.llm_client['timeout']
        )
        
        return response.choices[0].message.content
    
    def _call_mock(self, prompt: str) -> str:
        """调用模拟LLM服务"""
        logger.info("Using mock LLM response")
        
        # 生成模拟的结构化响应
        mock_response = {
            "meteorite_data": {
                "name": "Allende",
                "classification": "CV3碳质球粒陨石",
                "location": "墨西哥",
                "date": "1969年2月8日",
                "weight": "2吨",
                "composition": "主要成分为橄榄石、辉石、长石",
                "age": "45.6亿年",
                "origin": "小行星带"
            },
            "organic_compounds": {
                "compounds": "甘氨酸、丙氨酸、缬氨酸、亮氨酸",
                "concentration": "10-100 ppm",
                "detection_method": "GC-MS",
                "distribution": "均匀分布",
                "origin": "太阳星云",
                "significance": "生命起源的重要证据"
            },
            "mineral_relationships": {
                "relationships": "矿物共生关系明显",
                "minerals": "橄榄石、辉石、长石、磁铁矿",
                "interactions": "矿物间存在复杂的相互作用",
                "organic_mineral_relations": "矿物表面吸附有机分子",
                "catalysis": "矿物表面催化有机反应",
                "protection": "矿物保护有机分子免受破坏"
            },
            "scientific_insights": {
                "significance": "为生命起源理论提供重要证据",
                "conclusions": "陨石中存在生命前化学物质",
                "implications": "支持生命起源于太空的假说",
                "life_origin_insights": "有机分子在太空环境中形成",
                "cosmochemistry_insights": "太阳系早期化学演化的重要记录",
                "future_research": "需要进一步研究有机分子的形成机制"
            },
            "references": [
                {
                    "title": "Allende陨石中的有机化合物研究",
                    "content": "Smith, J. et al. (2020). Organic compounds in Allende meteorite. Nature, 123, 456-789.",
                    "type": "journal",
                    "authors": "Smith, J. et al.",
                    "journal": "Nature",
                    "year": "2020",
                    "doi": "10.1038/nature12345",
                    "url": ""
                },
                {
                    "title": "陨石矿物学研究",
                    "content": "Brown, A. et al. (2021). Mineralogy of carbonaceous chondrites. Science, 234, 567-890.",
                    "type": "journal",
                    "authors": "Brown, A. et al.",
                    "journal": "Science",
                    "year": "2021",
                    "doi": "10.1126/science.23456",
                    "url": ""
                }
            ]
        }
        
        # 返回JSON格式的响应
        return json.dumps(mock_response, ensure_ascii=False, indent=2)
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM响应
        
        Args:
            response: LLM原始响应
            
        Returns:
            Dict[str, Any]: 解析后的结构化数据
        """
        try:
            # 尝试直接解析JSON
            if response.strip().startswith('{'):
                return json.loads(response.strip())
            
            # 尝试提取JSON块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # 如果没有找到JSON，尝试解析为结构化文本
            return self._parse_text_response(response)
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {str(e)}")
            return self._parse_text_response(response)
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {"error": f"Failed to parse response: {str(e)}", "raw_response": response}
    
    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """
        将文本响应解析为结构化数据
        
        Args:
            response: 文本响应
            
        Returns:
            Dict[str, Any]: 结构化数据
        """
        try:
            structured_data = {
                "meteorite_data": {},
                "organic_compounds": {},
                "mineral_relationships": {},
                "scientific_insights": {},
                "references": []
            }
            
            # 简单的文本解析逻辑
            lines = response.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 识别章节
                if '陨石' in line or 'meteorite' in line.lower():
                    current_section = 'meteorite_data'
                elif '有机' in line or 'organic' in line.lower():
                    current_section = 'organic_compounds'
                elif '矿物' in line or 'mineral' in line.lower():
                    current_section = 'mineral_relationships'
                elif '科学' in line or 'scientific' in line.lower():
                    current_section = 'scientific_insights'
                elif '参考' in line or 'reference' in line.lower():
                    current_section = 'references'
                
                # 提取数据
                if current_section and ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if current_section == 'references':
                        structured_data[current_section].append({"title": key, "content": value})
                    else:
                        structured_data[current_section][key] = value
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error parsing text response: {str(e)}")
            return {"error": f"Failed to parse text response: {str(e)}", "raw_response": response}
    
    def _calculate_analysis_confidence(self, structured_data: Dict[str, Any]) -> float:
        """
        计算分析置信度
        
        Args:
            structured_data: 结构化数据
            
        Returns:
            float: 置信度分数 (0.0 - 1.0)
        """
        try:
            confidence_factors = []
            
            # 检查数据完整性
            required_sections = ['meteorite_data', 'organic_compounds', 'scientific_insights']
            for section in required_sections:
                if section in structured_data and structured_data[section]:
                    if isinstance(structured_data[section], dict) and len(structured_data[section]) > 0:
                        confidence_factors.append(0.8)
                    elif isinstance(structured_data[section], list) and len(structured_data[section]) > 0:
                        confidence_factors.append(0.8)
                    else:
                        confidence_factors.append(0.3)
                else:
                    confidence_factors.append(0.1)
            
            # 检查是否有错误
            if 'error' in structured_data:
                confidence_factors.append(0.1)
            else:
                confidence_factors.append(0.9)
            
            # 计算平均置信度
            avg_confidence = sum(confidence_factors) / len(confidence_factors)
            return min(max(avg_confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating analysis confidence: {str(e)}")
            return 0.5
