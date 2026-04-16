"""
数据提取器 - 从LLM响应中提取结构化数据
"""

import logging
import re
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StructuredData:
    """结构化数据"""
    meteorite_data: Dict[str, Any]
    organic_compounds: Dict[str, Any]
    mineral_relationships: Dict[str, Any]
    scientific_insights: Dict[str, Any]
    references: List[Dict[str, str]]


class DataExtractor:
    """数据提取器 - 从LLM响应中提取结构化数据"""
    
    def __init__(self):
        """初始化数据提取器"""
        logger.info("DataExtractor initialized")
    
    def extract_structured_data(self, analysis_result: 'AnalysisResult') -> StructuredData:
        """
        提取结构化数据
        
        Args:
            analysis_result: LLM分析结果
            
        Returns:
            StructuredData: 结构化数据
        """
        try:
            logger.info("Starting structured data extraction")
            
            # 从AnalysisResult对象中获取结构化数据
            if hasattr(analysis_result, 'structured_data'):
                raw_data = analysis_result.structured_data
                logger.info(f"Using structured_data from AnalysisResult: {type(raw_data)}")
                logger.info(f"Raw data keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'Not a dict'}")
            else:
                # 如果analysis_result是字符串，尝试解析
                raw_data = analysis_result
                logger.info(f"Using analysis_result directly: {type(raw_data)}")
            
            # 确保raw_data是字典格式
            if not isinstance(raw_data, dict):
                logger.warning(f"Raw data is not a dict, type: {type(raw_data)}")
                # 尝试从原始响应中提取数据
                if hasattr(analysis_result, 'raw_response'):
                    raw_data = {'raw_response': analysis_result.raw_response}
                else:
                    raw_data = {}
            
            # 提取各类数据
            meteorite_data = self.extract_meteorite_data(raw_data)
            organic_compounds = self.extract_organic_compounds(raw_data)
            mineral_relationships = self.extract_mineral_relationships(raw_data)
            scientific_insights = self.extract_scientific_insights(raw_data)
            references = self.extract_references(raw_data)
            
            # 如果所有数据都为空，尝试从原始响应中提取
            if (not meteorite_data and not organic_compounds and 
                not mineral_relationships and not scientific_insights):
                logger.warning("All extracted data is empty, trying fallback extraction")
                fallback_data = self._extract_fallback_data(raw_data)
                if fallback_data:
                    meteorite_data = fallback_data.get('meteorite_data', {})
                    organic_compounds = fallback_data.get('organic_compounds', {})
                    mineral_relationships = fallback_data.get('mineral_relationships', {})
                    scientific_insights = fallback_data.get('scientific_insights', {})
                    references = fallback_data.get('references', [])
            
            structured_data = StructuredData(
                meteorite_data=meteorite_data,
                organic_compounds=organic_compounds,
                mineral_relationships=mineral_relationships,
                scientific_insights=scientific_insights,
                references=references
            )
            
            logger.info("Structured data extraction completed")
            logger.info(f"Extracted data summary: meteorite={len(meteorite_data)}, organic={len(organic_compounds)}, mineral={len(mineral_relationships)}, insights={len(scientific_insights)}, refs={len(references)}")
            return structured_data
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            # 返回空的结构化数据而不是抛出异常
            return StructuredData(
                meteorite_data={},
                organic_compounds={},
                mineral_relationships={},
                scientific_insights={},
                references=[]
            )
    
    def extract_meteorite_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取陨石数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            Dict[str, Any]: 陨石数据
        """
        try:
            meteorite_data = {}
            
            # 从structured_data中获取陨石数据
            if 'meteorite_data' in raw_data:
                raw_meteorite_data = raw_data['meteorite_data']
                logger.info(f"Raw meteorite_data type: {type(raw_meteorite_data)}, value: {raw_meteorite_data}")
                
                if isinstance(raw_meteorite_data, dict):
                    meteorite_data = raw_meteorite_data.copy()
                    logger.info(f"Found meteorite_data in structured_data: {list(meteorite_data.keys())}")
                elif isinstance(raw_meteorite_data, list):
                    if len(raw_meteorite_data) > 0:
                        # 如果是列表，尝试转换为字典
                        meteorite_data = self._convert_list_to_dict(raw_meteorite_data)
                        logger.info(f"Converted list meteorite_data to dict: {list(meteorite_data.keys())}")
                    else:
                        # 空列表，尝试从原始响应中提取
                        meteorite_data = self._extract_meteorite_from_text(raw_data)
                        logger.info(f"Empty list, extracted from text: {list(meteorite_data.keys())}")
                else:
                    meteorite_data = {}
                    logger.info("meteorite_data is invalid format")
            else:
                # 从文本中提取陨石相关信息
                meteorite_data = self._extract_meteorite_from_text(raw_data)
                logger.info(f"Extracted meteorite data from text: {list(meteorite_data.keys())}")
            
            # 标准化陨石数据字段
            standardized_data = self._standardize_meteorite_data(meteorite_data)
            
            # 如果数据为空，提供默认说明
            if not standardized_data or all(not v or v == "" for v in standardized_data.values()):
                standardized_data = {
                    "name": "该论文不包含陨石相关内容",
                    "classification": "该论文不包含陨石相关内容", 
                    "location": "该论文不包含陨石相关内容",
                    "date": "该论文不包含陨石相关内容",
                    "explanation": "该论文主要研究其他天体生物学内容，不涉及陨石样本分析。请上传陨石研究相关的论文以获得陨石数据。"
                }
                logger.info("No meteorite data found, providing default explanation")
            
            logger.info(f"Extracted meteorite data: {len(standardized_data)} fields")
            logger.info(f"Standardized meteorite data: {list(standardized_data.keys())}")
            return standardized_data
            
        except Exception as e:
            logger.error(f"Error extracting meteorite data: {str(e)}")
            return {
                "name": "数据提取错误",
                "classification": "数据提取错误",
                "location": "数据提取错误", 
                "date": "数据提取错误",
                "explanation": "在提取陨石数据时发生错误，请重试或联系技术支持。"
            }
    
    def extract_organic_compounds(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取有机化合物数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            Dict[str, Any]: 有机化合物数据
        """
        try:
            organic_compounds = {}
            
            # 从structured_data中获取有机化合物数据
            if 'organic_compounds' in raw_data:
                organic_compounds = raw_data['organic_compounds'].copy()
            else:
                # 从文本中提取有机化合物信息
                organic_compounds = self._extract_organic_from_text(raw_data)
            
            # 标准化有机化合物数据
            standardized_data = self._standardize_organic_data(organic_compounds)
            
            # 如果数据为空，提供默认说明
            if not standardized_data or all(not v or v == "" for v in standardized_data.values()):
                standardized_data = {
                    "compounds": "该论文不包含有机化合物相关内容",
                    "concentration": "该论文不包含有机化合物相关内容",
                    "explanation": "该论文主要研究其他天体生物学内容，不涉及有机化合物分析。请上传有机化合物研究相关的论文以获得有机化合物数据。"
                }
                logger.info("No organic compounds data found, providing default explanation")
            
            logger.info(f"Extracted organic compounds data: {len(standardized_data)} fields")
            return standardized_data
            
        except Exception as e:
            logger.error(f"Error extracting organic compounds data: {str(e)}")
            return {
                "compounds": "数据提取错误",
                "concentration": "数据提取错误",
                "explanation": "在提取有机化合物数据时发生错误，请重试或联系技术支持。"
            }
    
    def extract_mineral_relationships(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取矿物关系数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            Dict[str, Any]: 矿物关系数据
        """
        try:
            mineral_relationships = {}
            
            # 从structured_data中获取矿物关系数据
            if 'mineral_relationships' in raw_data:
                mineral_relationships = raw_data['mineral_relationships'].copy()
            else:
                # 从文本中提取矿物关系信息
                mineral_relationships = self._extract_mineral_from_text(raw_data)
            
            # 标准化矿物关系数据
            standardized_data = self._standardize_mineral_data(mineral_relationships)
            
            # 如果数据为空，提供默认说明
            if not standardized_data or all(not v or v == "" for v in standardized_data.values()):
                standardized_data = {
                    "relationships": "该论文不包含矿物关系相关内容",
                    "minerals": "该论文不包含矿物相关内容",
                    "explanation": "该论文主要研究其他天体生物学内容，不涉及矿物关系分析。请上传矿物学研究相关的论文以获得矿物关系数据。"
                }
                logger.info("No mineral relationships data found, providing default explanation")
            
            logger.info(f"Extracted mineral relationships data: {len(standardized_data)} fields")
            return standardized_data
            
        except Exception as e:
            logger.error(f"Error extracting mineral relationships data: {str(e)}")
            return {
                "relationships": "数据提取错误",
                "minerals": "数据提取错误",
                "explanation": "在提取矿物关系数据时发生错误，请重试或联系技术支持。"
            }
    
    def extract_scientific_insights(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取科学洞察数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            Dict[str, Any]: 科学洞察数据
        """
        try:
            scientific_insights = {}
            
            # 从structured_data中获取科学洞察数据
            if 'scientific_insights' in raw_data:
                scientific_insights = raw_data['scientific_insights'].copy()
            else:
                # 从文本中提取科学洞察信息
                scientific_insights = self._extract_insights_from_text(raw_data)
            
            # 标准化科学洞察数据
            standardized_data = self._standardize_insights_data(scientific_insights)
            
            # 如果数据为空，提供默认说明
            if not standardized_data or all(not v or v == "" for v in standardized_data.values()):
                standardized_data = {
                    "significance": "该论文不包含相关科学意义",
                    "explanation": "该论文主要研究其他天体生物学内容，不涉及相关科学洞察。请上传相关研究领域的论文以获得科学洞察数据。"
                }
                logger.info("No scientific insights data found, providing default explanation")
            
            logger.info(f"Extracted scientific insights data: {len(standardized_data)} fields")
            return standardized_data
            
        except Exception as e:
            logger.error(f"Error extracting scientific insights data: {str(e)}")
            return {
                "significance": "数据提取错误",
                "explanation": "在提取科学洞察数据时发生错误，请重试或联系技术支持。"
            }
    
    def extract_references(self, raw_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        提取参考文献数据
        
        Args:
            raw_data: 原始数据
            
        Returns:
            List[Dict[str, str]]: 参考文献列表
        """
        try:
            references = []
            
            # 从structured_data中获取参考文献数据
            if 'references' in raw_data and isinstance(raw_data['references'], list):
                references = raw_data['references'].copy()
            else:
                # 从文本中提取参考文献信息
                references = self._extract_references_from_text(raw_data)
            
            # 标准化参考文献数据
            standardized_references = self._standardize_references_data(references)
            
            logger.info(f"Extracted references: {len(standardized_references)} items")
            return standardized_references
            
        except Exception as e:
            logger.error(f"Error extracting references data: {str(e)}")
            return []
    
    def _extract_meteorite_from_text(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """从文本中提取陨石数据"""
        meteorite_data = {}
        
        # 从raw_response中提取
        if 'raw_response' in raw_data:
            text = raw_data['raw_response']
            
            # 提取陨石名称 - 多种模式
            name_patterns = [
                r'(?:陨石|meteorite)[\s:：]*(.+?)(?:\n|$)',
                r'(?:名称|name)[\s:：]*(.+?)(?:\n|$)',
                r'(?:样本|sample)[\s:：]*(.+?)(?:\n|$)',
                r'([A-Z]{2,4}\d{4,6})',  # 陨石编号模式
                r'([A-Z]{2,4}-\d{4,6})'  # 陨石编号模式2
            ]
            
            for pattern in name_patterns:
                name_match = re.search(pattern, text, re.IGNORECASE)
                if name_match:
                    meteorite_data['name'] = name_match.group(1).strip()
                    break
            
            # 提取分类信息 - 多种模式
            class_patterns = [
                r'(?:分类|classification)[\s:：]*(.+?)(?:\n|$)',
                r'(?:类型|type)[\s:：]*(.+?)(?:\n|$)',
                r'(?:chondrite|achondrite|iron|stony-iron|carbonaceous)',
                r'(?:普通球粒陨石|碳质球粒陨石|顽辉石球粒陨石)'
            ]
            
            for pattern in class_patterns:
                class_match = re.search(pattern, text, re.IGNORECASE)
                if class_match:
                    meteorite_data['classification'] = class_match.group(1).strip()
                    break
            
            # 提取发现地点
            location_patterns = [
                r'(?:发现地点|location|found at)[\s:：]*(.+?)(?:\n|$)',
                r'(?:发现位置|discovery site)[\s:：]*(.+?)(?:\n|$)',
                r'(?:来源|origin)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            for pattern in location_patterns:
                location_match = re.search(pattern, text, re.IGNORECASE)
                if location_match:
                    meteorite_data['location'] = location_match.group(1).strip()
                    break
            
            # 提取重量信息
            weight_patterns = [
                r'(?:重量|weight|mass)[\s:：]*(.+?)(?:\n|$)',
                r'(\d+\.?\d*)\s*(?:g|kg|克|千克)',
                r'(\d+\.?\d*)\s*(?:grams?|kilograms?)'
            ]
            
            for pattern in weight_patterns:
                weight_match = re.search(pattern, text, re.IGNORECASE)
                if weight_match:
                    meteorite_data['weight'] = weight_match.group(1).strip()
                    break
            
            # 提取发现日期
            date_patterns = [
                r'(?:发现日期|date|found)[\s:：]*(.+?)(?:\n|$)',
                r'(\d{4}年\d{1,2}月\d{1,2}日)',
                r'(\d{4}-\d{1,2}-\d{1,2})',
                r'(\d{4}/\d{1,2}/\d{1,2})'
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, text, re.IGNORECASE)
                if date_match:
                    meteorite_data['date'] = date_match.group(1).strip()
                    break
        
        return meteorite_data
    
    def _extract_organic_from_text(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """从文本中提取有机化合物数据"""
        organic_data = {}
        
        # 从raw_response中提取
        if 'raw_response' in raw_data:
            text = raw_data['raw_response']
            
            # 提取有机化合物名称 - 多种模式
            compound_patterns = [
                r'(?:有机化合物|organic compound)[\s:：]*(.+?)(?:\n|$)',
                r'(?:氨基酸|amino acid)[\s:：]*(.+?)(?:\n|$)',
                r'(?:蛋白质|protein)[\s:：]*(.+?)(?:\n|$)',
                r'(?:脂质|lipid)[\s:：]*(.+?)(?:\n|$)',
                r'(?:碳水化合物|carbohydrate)[\s:：]*(.+?)(?:\n|$)',
                r'(?:核酸|nucleic acid)[\s:：]*(.+?)(?:\n|$)',
                r'(?:糖类|sugar)[\s:：]*(.+?)(?:\n|$)',
                r'(?:醇类|alcohol)[\s:：]*(.+?)(?:\n|$)',
                r'(?:酸类|acid)[\s:：]*(.+?)(?:\n|$)',
                r'(?:胺类|amine)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            compounds = []
            for pattern in compound_patterns:
                compound_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in compound_matches:
                    if match.strip() and match.strip() not in compounds:
                        compounds.append(match.strip())
            
            if compounds:
                organic_data['compounds'] = '; '.join(compounds)
            
            # 提取浓度信息
            concentration_patterns = [
                r'(?:浓度|concentration)[\s:：]*(.+?)(?:\n|$)',
                r'(?:含量|content)[\s:：]*(.+?)(?:\n|$)',
                r'(?:ppm|ppb|%|mg/kg|μg/g)',
                r'(\d+\.?\d*)\s*(?:ppm|ppb|%|mg/kg|μg/g)'
            ]
            
            for pattern in concentration_patterns:
                concentration_match = re.search(pattern, text, re.IGNORECASE)
                if concentration_match:
                    organic_data['concentration'] = concentration_match.group(1).strip()
                    break
            
            # 提取检测方法
            method_patterns = [
                r'(?:检测方法|detection method)[\s:：]*(.+?)(?:\n|$)',
                r'(?:分析方法|analysis method)[\s:：]*(.+?)(?:\n|$)',
                r'(?:GC-MS|LC-MS|HPLC|NMR|FTIR|XPS|TEM|SEM)',
                r'(?:气相色谱|液相色谱|核磁共振|红外光谱|X射线光电子能谱)'
            ]
            
            methods = []
            for pattern in method_patterns:
                method_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in method_matches:
                    if match.strip() and match.strip() not in methods:
                        methods.append(match.strip())
            
            if methods:
                organic_data['detection_method'] = '; '.join(methods)
            
            # 提取分布信息
            distribution_patterns = [
                r'(?:分布|distribution)[\s:：]*(.+?)(?:\n|$)',
                r'(?:位置|location)[\s:：]*(.+?)(?:\n|$)',
                r'(?:区域|region)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            for pattern in distribution_patterns:
                distribution_match = re.search(pattern, text, re.IGNORECASE)
                if distribution_match:
                    organic_data['distribution'] = distribution_match.group(1).strip()
                    break
        
        return organic_data
    
    def _extract_mineral_from_text(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """从文本中提取矿物关系数据"""
        mineral_data = {}
        
        # 从raw_response中提取
        if 'raw_response' in raw_data:
            text = raw_data['raw_response']
            
            # 提取矿物关系信息 - 多种模式
            relationship_patterns = [
                r'(?:矿物关系|mineral relationship)[\s:：]*(.+?)(?:\n|$)',
                r'(?:矿物相互作用|mineral interaction)[\s:：]*(.+?)(?:\n|$)',
                r'(?:矿物组合|mineral assemblage)[\s:：]*(.+?)(?:\n|$)',
                r'(?:矿物共生|mineral paragenesis)[\s:：]*(.+?)(?:\n|$)',
                r'(?:矿物结构|mineral structure)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            relationships = []
            for pattern in relationship_patterns:
                relationship_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in relationship_matches:
                    if match.strip() and match.strip() not in relationships:
                        relationships.append(match.strip())
            
            if relationships:
                mineral_data['relationships'] = '; '.join(relationships)
            
            # 提取矿物种类 - 多种模式
            mineral_patterns = [
                r'(?:矿物种类|mineral species)[\s:：]*(.+?)(?:\n|$)',
                r'(?:矿物成分|mineral composition)[\s:：]*(.+?)(?:\n|$)',
                r'(?:主要矿物|major minerals)[\s:：]*(.+?)(?:\n|$)',
                r'(?:次要矿物|minor minerals)[\s:：]*(.+?)(?:\n|$)',
                r'(?:olivine|pyroxene|plagioclase|feldspar|quartz|carbonate|sulfide|oxide)',
                r'(?:橄榄石|辉石|长石|石英|碳酸盐|硫化物|氧化物)'
            ]
            
            minerals = []
            for pattern in mineral_patterns:
                mineral_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in mineral_matches:
                    if match.strip() and match.strip() not in minerals:
                        minerals.append(match.strip())
            
            if minerals:
                mineral_data['minerals'] = '; '.join(minerals)
            
            # 提取相互作用机制
            interaction_patterns = [
                r'(?:相互作用|interaction)[\s:：]*(.+?)(?:\n|$)',
                r'(?:反应机制|reaction mechanism)[\s:：]*(.+?)(?:\n|$)',
                r'(?:形成过程|formation process)[\s:：]*(.+?)(?:\n|$)',
                r'(?:变质作用|metamorphism)[\s:：]*(.+?)(?:\n|$)',
                r'(?:蚀变作用|alteration)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            interactions = []
            for pattern in interaction_patterns:
                interaction_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in interaction_matches:
                    if match.strip() and match.strip() not in interactions:
                        interactions.append(match.strip())
            
            if interactions:
                mineral_data['interactions'] = '; '.join(interactions)
            
            # 提取矿物-有机质关系
            organic_mineral_patterns = [
                r'(?:矿物-有机质|mineral-organic)[\s:：]*(.+?)(?:\n|$)',
                r'(?:有机质-矿物|organic-mineral)[\s:：]*(.+?)(?:\n|$)',
                r'(?:矿物表面|mineral surface)[\s:：]*(.+?)(?:\n|$)',
                r'(?:吸附作用|adsorption)[\s:：]*(.+?)(?:\n|$)',
                r'(?:催化作用|catalysis)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            organic_mineral_relations = []
            for pattern in organic_mineral_patterns:
                relation_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in relation_matches:
                    if match.strip() and match.strip() not in organic_mineral_relations:
                        organic_mineral_relations.append(match.strip())
            
            if organic_mineral_relations:
                mineral_data['organic_mineral_relations'] = '; '.join(organic_mineral_relations)
        
        return mineral_data
    
    def _extract_insights_from_text(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """从文本中提取科学洞察数据"""
        insights_data = {}
        
        # 从raw_response中提取
        if 'raw_response' in raw_data:
            text = raw_data['raw_response']
            
            # 提取科学意义 - 多种模式
            significance_patterns = [
                r'(?:科学意义|scientific significance)[\s:：]*(.+?)(?:\n|$)',
                r'(?:研究意义|research significance)[\s:：]*(.+?)(?:\n|$)',
                r'(?:科学价值|scientific value)[\s:：]*(.+?)(?:\n|$)',
                r'(?:重要性|importance)[\s:：]*(.+?)(?:\n|$)',
                r'(?:意义|significance)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            significance = []
            for pattern in significance_patterns:
                significance_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in significance_matches:
                    if match.strip() and match.strip() not in significance:
                        significance.append(match.strip())
            
            if significance:
                insights_data['significance'] = '; '.join(significance)
            
            # 提取研究结论 - 多种模式
            conclusion_patterns = [
                r'(?:结论|conclusion)[\s:：]*(.+?)(?:\n|$)',
                r'(?:主要结论|main conclusion)[\s:：]*(.+?)(?:\n|$)',
                r'(?:研究发现|research finding)[\s:：]*(.+?)(?:\n|$)',
                r'(?:结果|result)[\s:：]*(.+?)(?:\n|$)',
                r'(?:发现|finding)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            conclusions = []
            for pattern in conclusion_patterns:
                conclusion_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in conclusion_matches:
                    if match.strip() and match.strip() not in conclusions:
                        conclusions.append(match.strip())
            
            if conclusions:
                insights_data['conclusions'] = '; '.join(conclusions)
            
            # 提取科学影响 - 多种模式
            implication_patterns = [
                r'(?:影响|implication)[\s:：]*(.+?)(?:\n|$)',
                r'(?:科学影响|scientific implication)[\s:：]*(.+?)(?:\n|$)',
                r'(?:研究影响|research implication)[\s:：]*(.+?)(?:\n|$)',
                r'(?:应用前景|application prospect)[\s:：]*(.+?)(?:\n|$)',
                r'(?:未来研究|future research)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            implications = []
            for pattern in implication_patterns:
                implication_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in implication_matches:
                    if match.strip() and match.strip() not in implications:
                        implications.append(match.strip())
            
            if implications:
                insights_data['implications'] = '; '.join(implications)
            
            # 提取生命起源相关洞察
            life_origin_patterns = [
                r'(?:生命起源|origin of life)[\s:：]*(.+?)(?:\n|$)',
                r'(?:天体生物学|astrobiology)[\s:：]*(.+?)(?:\n|$)',
                r'(?:生命前化学|prebiotic chemistry)[\s:：]*(.+?)(?:\n|$)',
                r'(?:有机合成|organic synthesis)[\s:：]*(.+?)(?:\n|$)',
                r'(?:化学演化|chemical evolution)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            life_origin_insights = []
            for pattern in life_origin_patterns:
                life_origin_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in life_origin_matches:
                    if match.strip() and match.strip() not in life_origin_insights:
                        life_origin_insights.append(match.strip())
            
            if life_origin_insights:
                insights_data['life_origin_insights'] = '; '.join(life_origin_insights)
            
            # 提取宇宙化学洞察
            cosmochemistry_patterns = [
                r'(?:宇宙化学|cosmochemistry)[\s:：]*(.+?)(?:\n|$)',
                r'(?:太阳系形成|solar system formation)[\s:：]*(.+?)(?:\n|$)',
                r'(?:行星形成|planetary formation)[\s:：]*(.+?)(?:\n|$)',
                r'(?:星际介质|interstellar medium)[\s:：]*(.+?)(?:\n|$)',
                r'(?:分子云|molecular cloud)[\s:：]*(.+?)(?:\n|$)'
            ]
            
            cosmochemistry_insights = []
            for pattern in cosmochemistry_patterns:
                cosmochemistry_matches = re.findall(pattern, text, re.IGNORECASE)
                for match in cosmochemistry_matches:
                    if match.strip() and match.strip() not in cosmochemistry_insights:
                        cosmochemistry_insights.append(match.strip())
            
            if cosmochemistry_insights:
                insights_data['cosmochemistry_insights'] = '; '.join(cosmochemistry_insights)
        
        return insights_data
    
    def _extract_references_from_text(self, raw_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """从文本中提取参考文献数据"""
        references = []
        
        # 从raw_response中提取
        if 'raw_response' in raw_data:
            text = raw_data['raw_response']
            
            # 提取参考文献 - 多种模式
            ref_patterns = [
                r'(?:参考文献|references?)[\s:：]*(.+?)(?:\n\n|\Z)',
                r'(?:引用文献|cited references?)[\s:：]*(.+?)(?:\n\n|\Z)',
                r'(?:文献列表|bibliography)[\s:：]*(.+?)(?:\n\n|\Z)',
                r'(?:引用|citation)[\s:：]*(.+?)(?:\n\n|\Z)'
            ]
            
            ref_text = ""
            for pattern in ref_patterns:
                ref_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if ref_match:
                    ref_text = ref_match.group(1)
                    break
            
            if ref_text:
                # 分割参考文献
                ref_lines = [line.strip() for line in ref_text.split('\n') if line.strip()]
                
                for i, ref_line in enumerate(ref_lines):
                    # 尝试提取更多信息
                    ref_info = self._parse_reference_line(ref_line, i+1)
                    references.append(ref_info)
            
            # 如果没有找到参考文献部分，尝试从文本中提取引用
            if not references:
                references = self._extract_citations_from_text(text)
        
        return references
    
    def _parse_reference_line(self, ref_line: str, index: int) -> Dict[str, str]:
        """解析参考文献行"""
        try:
            # 初始化参考文献信息
            ref_info = {
                'title': f'Reference {index}',
                'content': ref_line,
                'type': 'unknown',
                'authors': '',
                'journal': '',
                'year': '',
                'doi': '',
                'url': ''
            }
            
            # 检测DOI
            doi_match = re.search(r'doi[:\s]*([^\s,]+)', ref_line, re.IGNORECASE)
            if doi_match:
                ref_info['doi'] = doi_match.group(1)
                ref_info['type'] = 'journal'
            
            # 检测URL
            url_match = re.search(r'(https?://[^\s,]+)', ref_line)
            if url_match:
                ref_info['url'] = url_match.group(1)
                ref_info['type'] = 'web'
            
            # 检测年份
            year_match = re.search(r'(19|20)\d{2}', ref_line)
            if year_match:
                ref_info['year'] = year_match.group(0)
            
            # 检测期刊名称
            journal_patterns = [
                r'(?:Nature|Science|PNAS|Cell|Journal of|Proceedings of)',
                r'(?:Nature|Science|PNAS|Cell|Journal of|Proceedings of)[^,]*',
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Journal|Proceedings|Review|Letters))'
            ]
            
            for pattern in journal_patterns:
                journal_match = re.search(pattern, ref_line)
                if journal_match:
                    ref_info['journal'] = journal_match.group(0)
                    ref_info['type'] = 'journal'
                    break
            
            # 检测作者
            author_patterns = [
                r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+et\s+al\.?)?)',
                r'([A-Z][a-z]+,\s+[A-Z]\.)',
                r'([A-Z][a-z]+,\s+[A-Z][a-z]+)'
            ]
            
            for pattern in author_patterns:
                author_match = re.search(pattern, ref_line)
                if author_match:
                    ref_info['authors'] = author_match.group(0)
                    break
            
            # 如果没有找到作者，尝试提取标题
            if not ref_info['authors'] and not ref_info['journal']:
                # 简单提取可能的标题
                title_match = re.search(r'^([^,]+)', ref_line)
                if title_match:
                    ref_info['title'] = title_match.group(1).strip()
            
            return ref_info
            
        except Exception as e:
            logger.error(f"Error parsing reference line: {str(e)}")
            return {
                'title': f'Reference {index}',
                'content': ref_line,
                'type': 'unknown',
                'authors': '',
                'journal': '',
                'year': '',
                'doi': '',
                'url': ''
            }
    
    def _extract_citations_from_text(self, text: str) -> List[Dict[str, str]]:
        """从文本中提取引用"""
        references = []
        
        try:
            # 提取引用模式
            citation_patterns = [
                r'\(([A-Z][a-z]+\s+et\s+al\.?,?\s*(?:19|20)\d{2})\)',
                r'\(([A-Z][a-z]+,\s*(?:19|20)\d{2})\)',
                r'\(([A-Z][a-z]+\s+and\s+[A-Z][a-z]+,?\s*(?:19|20)\d{2})\)',
                r'\(([A-Z][a-z]+\s+[A-Z][a-z]+,?\s*(?:19|20)\d{2})\)'
            ]
            
            for pattern in citation_patterns:
                citation_matches = re.findall(pattern, text)
                for i, citation in enumerate(citation_matches):
                    references.append({
                        'title': f'Citation {i+1}',
                        'content': citation,
                        'type': 'citation',
                        'authors': citation,
                        'journal': '',
                        'year': re.search(r'(19|20)\d{2}', citation).group(0) if re.search(r'(19|20)\d{2}', citation) else '',
                        'doi': '',
                        'url': ''
                    })
            
            # 去重
            unique_references = []
            seen_citations = set()
            for ref in references:
                if ref['content'] not in seen_citations:
                    unique_references.append(ref)
                    seen_citations.add(ref['content'])
            
            return unique_references
            
        except Exception as e:
            logger.error(f"Error extracting citations from text: {str(e)}")
            return []
    
    def _standardize_meteorite_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化陨石数据"""
        standardized = {}
        
        # 检测无效数据（论文引用等）
        def is_valid_meteorite_field(key, value):
            """检查是否为有效的陨石数据字段"""
            if not value or isinstance(value, (list, dict)):
                return False
            
            # 检查键名是否包含常见的引用模式
            key_str = str(key).lower()
            value_str = str(value).lower()
            
            # 如果键名包含引用、作者、期刊等关键词，可能是无效数据
            invalid_keywords = ['* ', 'et al', 'journal', 'reference', 'author', 'doi', 'http']
            if any(kw in key_str for kw in invalid_keywords):
                return False
            
            # 如果值包含引用格式
            if any(kw in value_str for kw in invalid_keywords):
                return False
            
            return True
        
        # 标准字段映射
        field_mapping = {
            'name': ['name', '名称', '陨石名称'],
            'classification': ['classification', '分类', '类型'],
            'location': ['location', '地点', '发现地点'],
            'date': ['date', '日期', '发现日期'],
            'weight': ['weight', '重量', '质量']
        }
        
        # 首先映射标准字段
        for standard_field, possible_fields in field_mapping.items():
            for field in possible_fields:
                if field in data:
                    standardized[standard_field] = data[field]
                    break
        
        # 然后保留所有其他有效字段
        for key, value in data.items():
            if key not in standardized and is_valid_meteorite_field(key, value):
                standardized[key] = value
        
        return standardized
    
    def _convert_list_to_dict(self, data_list: List[Any]) -> Dict[str, Any]:
        """将列表转换为字典"""
        try:
            if not data_list:
                return {}
            
            # 如果列表中的元素是字典，尝试合并
            if isinstance(data_list[0], dict):
                result = {}
                for item in data_list:
                    if isinstance(item, dict):
                        result.update(item)
                return result
            
            # 如果列表中的元素是字符串，创建简单映射
            elif isinstance(data_list[0], str):
                return {'data': data_list}
            
            return {}
        except Exception as e:
            logger.error(f"Error converting list to dict: {str(e)}")
            return {}
    
    def _standardize_organic_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化有机化合物数据"""
        standardized = {}
        
        # 标准字段映射
        field_mapping = {
            'compounds': ['compounds', '化合物', '有机化合物'],
            'concentration': ['concentration', '浓度', '含量'],
            'detection_method': ['detection_method', '检测方法', '分析方法']
        }
        
        # 首先映射标准字段
        for standard_field, possible_fields in field_mapping.items():
            for field in possible_fields:
                if field in data:
                    standardized[standard_field] = data[field]
                    break
        
        # 然后保留所有其他字段
        for key, value in data.items():
            if key not in standardized and value:  # 只保留非空值
                standardized[key] = value
        
        return standardized
    
    def _standardize_mineral_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化矿物关系数据"""
        standardized = {}
        
        # 标准字段映射
        field_mapping = {
            'relationships': ['relationships', '关系', '矿物关系'],
            'minerals': ['minerals', '矿物', '矿物种类'],
            'interactions': ['interactions', '相互作用', '交互作用']
        }
        
        # 首先映射标准字段
        for standard_field, possible_fields in field_mapping.items():
            for field in possible_fields:
                if field in data:
                    standardized[standard_field] = data[field]
                    break
        
        # 然后保留所有其他字段
        for key, value in data.items():
            if key not in standardized and value:  # 只保留非空值
                standardized[key] = value
        
        return standardized
    
    def _standardize_insights_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化科学洞察数据"""
        standardized = {}
        
        # 标准字段映射
        field_mapping = {
            'significance': ['significance', '意义', '科学意义'],
            'conclusions': ['conclusions', '结论', '研究结论'],
            'implications': ['implications', '影响', '科学影响']
        }
        
        # 首先映射标准字段
        for standard_field, possible_fields in field_mapping.items():
            for field in possible_fields:
                if field in data:
                    standardized[standard_field] = data[field]
                    break
        
        # 然后保留所有其他字段
        for key, value in data.items():
            if key not in standardized and value:  # 只保留非空值
                standardized[key] = value
        
        return standardized
    
    def _standardize_references_data(self, data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """标准化参考文献数据"""
        standardized = []
        
        for ref in data:
            standardized_ref = {
                'title': ref.get('title', ''),
                'content': ref.get('content', ''),
                'type': 'unknown'
            }
            
            # 检测参考文献类型
            content = ref.get('content', '').lower()
            if 'doi:' in content or 'doi.org' in content:
                standardized_ref['type'] = 'doi'
            elif '@' in content and '.' in content:
                standardized_ref['type'] = 'journal'
            elif any(year in content for year in ['2020', '2021', '2022', '2023', '2024']):
                standardized_ref['type'] = 'publication'
            
            standardized.append(standardized_ref)
        
        return standardized
    
    def _extract_fallback_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """备用数据提取方法"""
        try:
            fallback_data = {
                'meteorite_data': {},
                'organic_compounds': {},
                'mineral_relationships': {},
                'scientific_insights': {},
                'references': []
            }
            
            # 从原始响应中提取数据
            if 'raw_response' in raw_data:
                text = raw_data['raw_response']
                
                # 简单的关键词提取
                if '陨石' in text or 'meteorite' in text.lower():
                    fallback_data['meteorite_data'] = {
                        'name': '从文本中提取的陨石信息',
                        'classification': '需要进一步分析',
                        'location': '需要进一步分析'
                    }
                
                if '有机' in text or 'organic' in text.lower():
                    fallback_data['organic_compounds'] = {
                        'compounds': '从文本中识别的有机化合物',
                        'concentration': '需要进一步分析',
                        'detection_method': '需要进一步分析'
                    }
                
                if '矿物' in text or 'mineral' in text.lower():
                    fallback_data['mineral_relationships'] = {
                        'minerals': '从文本中识别的矿物',
                        'relationships': '需要进一步分析'
                    }
                
                if '科学' in text or 'scientific' in text.lower():
                    fallback_data['scientific_insights'] = {
                        'significance': '从文本中提取的科学意义',
                        'conclusions': '需要进一步分析'
                    }
                
                # 提取参考文献
                if '参考文献' in text or 'references' in text.lower():
                    fallback_data['references'] = [
                        {
                            'title': '从文本中提取的参考文献',
                            'content': '需要进一步分析',
                            'type': 'unknown'
                        }
                    ]
            
            return fallback_data
            
        except Exception as e:
            logger.error(f"Error in fallback data extraction: {str(e)}")
            return {}
