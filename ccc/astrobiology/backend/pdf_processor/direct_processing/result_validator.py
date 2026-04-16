"""
结果验证器 - 验证提取结果的准确性
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationCheck:
    """验证检查结果"""
    check_name: str
    passed: bool
    message: str
    confidence: float


@dataclass
class ValidatedResult:
    """验证后的结果"""
    data: 'StructuredData'
    validation_checks: List[ValidationCheck]
    confidence_score: float
    validation_notes: str = ""


class ResultValidator:
    """结果验证器 - 验证提取结果的准确性"""
    
    def __init__(self):
        """初始化结果验证器"""
        logger.info("ResultValidator initialized")
    
    def validate_result(self, data: 'StructuredData') -> ValidatedResult:
        """
        验证结果
        
        Args:
            data: 结构化数据
            
        Returns:
            ValidatedResult: 验证后的结果
        """
        try:
            logger.info("Starting result validation")
            
            validation_checks = []
            
            # 执行各种验证检查
            validation_checks.extend(self.check_data_completeness(data))
            validation_checks.extend(self.check_scientific_consistency(data))
            validation_checks.extend(self.check_reference_accuracy(data))
            validation_checks.extend(self.check_data_format(data))
            
            # 计算整体置信度
            confidence_score = self.calculate_confidence(validation_checks)
            
            # 生成验证说明
            validation_notes = self._generate_validation_notes(validation_checks)
            
            result = ValidatedResult(
                data=data,
                validation_checks=validation_checks,
                confidence_score=confidence_score,
                validation_notes=validation_notes
            )
            
            logger.info(f"Result validation completed. Confidence: {confidence_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error validating result: {str(e)}")
            raise
    
    def check_data_completeness(self, data: 'StructuredData') -> List[ValidationCheck]:
        """
        检查数据完整性
        
        Args:
            data: 结构化数据
            
        Returns:
            List[ValidationCheck]: 验证检查结果列表
        """
        checks = []
        
        try:
            # 检查陨石数据完整性
            meteorite_check = self._check_meteorite_completeness(data.meteorite_data)
            checks.append(meteorite_check)
            
            # 检查有机化合物数据完整性
            organic_check = self._check_organic_completeness(data.organic_compounds)
            checks.append(organic_check)
            
            # 检查科学洞察完整性
            insights_check = self._check_insights_completeness(data.scientific_insights)
            checks.append(insights_check)
            
            # 检查参考文献完整性
            references_check = self._check_references_completeness(data.references)
            checks.append(references_check)
            
        except Exception as e:
            logger.error(f"Error checking data completeness: {str(e)}")
            checks.append(ValidationCheck(
                check_name="data_completeness",
                passed=False,
                message=f"Error checking completeness: {str(e)}",
                confidence=0.0
            ))
        
        return checks
    
    def check_scientific_consistency(self, data: 'StructuredData') -> List[ValidationCheck]:
        """
        检查科学一致性
        
        Args:
            data: 结构化数据
            
        Returns:
            List[ValidationCheck]: 验证检查结果列表
        """
        checks = []
        
        try:
            # 检查陨石分类的科学性
            classification_check = self._check_meteorite_classification(data.meteorite_data)
            checks.append(classification_check)
            
            # 检查有机化合物的合理性
            organic_consistency_check = self._check_organic_consistency(data.organic_compounds)
            checks.append(organic_consistency_check)
            
            # 检查矿物关系的科学性
            mineral_consistency_check = self._check_mineral_consistency(data.mineral_relationships)
            checks.append(mineral_consistency_check)
            
        except Exception as e:
            logger.error(f"Error checking scientific consistency: {str(e)}")
            checks.append(ValidationCheck(
                check_name="scientific_consistency",
                passed=False,
                message=f"Error checking consistency: {str(e)}",
                confidence=0.0
            ))
        
        return checks
    
    def check_reference_accuracy(self, data: 'StructuredData') -> List[ValidationCheck]:
        """
        检查参考文献准确性
        
        Args:
            data: 结构化数据
            
        Returns:
            List[ValidationCheck]: 验证检查结果列表
        """
        checks = []
        
        try:
            # 检查参考文献格式
            format_check = self._check_reference_format(data.references)
            checks.append(format_check)
            
            # 检查参考文献数量
            quantity_check = self._check_reference_quantity(data.references)
            checks.append(quantity_check)
            
        except Exception as e:
            logger.error(f"Error checking reference accuracy: {str(e)}")
            checks.append(ValidationCheck(
                check_name="reference_accuracy",
                passed=False,
                message=f"Error checking references: {str(e)}",
                confidence=0.0
            ))
        
        return checks
    
    def check_data_format(self, data: 'StructuredData') -> List[ValidationCheck]:
        """
        检查数据格式
        
        Args:
            data: 结构化数据
            
        Returns:
            List[ValidationCheck]: 验证检查结果列表
        """
        checks = []
        
        try:
            # 检查数据类型
            type_check = self._check_data_types(data)
            checks.append(type_check)
            
            # 检查数据范围
            range_check = self._check_data_ranges(data)
            checks.append(range_check)
            
        except Exception as e:
            logger.error(f"Error checking data format: {str(e)}")
            checks.append(ValidationCheck(
                check_name="data_format",
                passed=False,
                message=f"Error checking format: {str(e)}",
                confidence=0.0
            ))
        
        return checks
    
    def calculate_confidence(self, validation_checks: List[ValidationCheck]) -> float:
        """
        计算整体置信度
        
        Args:
            validation_checks: 验证检查结果列表
            
        Returns:
            float: 置信度分数 (0.0 - 1.0)
        """
        try:
            if not validation_checks:
                return 0.5
            
            # 计算加权平均置信度
            total_weight = 0
            weighted_sum = 0
            
            for check in validation_checks:
                weight = self._get_check_weight(check.check_name)
                weighted_sum += check.confidence * weight
                total_weight += weight
            
            if total_weight == 0:
                return 0.5
            
            confidence = weighted_sum / total_weight
            return min(max(confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating confidence: {str(e)}")
            return 0.5
    
    def _check_meteorite_completeness(self, meteorite_data: Dict[str, Any]) -> ValidationCheck:
        """检查陨石数据完整性"""
        try:
            required_fields = ['name', 'classification']
            missing_fields = []
            
            for field in required_fields:
                if field not in meteorite_data or not meteorite_data[field]:
                    missing_fields.append(field)
            
            if not missing_fields:
                return ValidationCheck(
                    check_name="meteorite_completeness",
                    passed=True,
                    message="All required meteorite fields present",
                    confidence=0.9
                )
            else:
                return ValidationCheck(
                    check_name="meteorite_completeness",
                    passed=False,
                    message=f"Missing fields: {', '.join(missing_fields)}",
                    confidence=0.3
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="meteorite_completeness",
                passed=False,
                message=f"Error checking meteorite completeness: {str(e)}",
                confidence=0.0
            )
    
    def _check_organic_completeness(self, organic_data: Dict[str, Any]) -> ValidationCheck:
        """检查有机化合物数据完整性"""
        try:
            if not organic_data:
                return ValidationCheck(
                    check_name="organic_completeness",
                    passed=False,
                    message="No organic compounds data found",
                    confidence=0.1
                )
            
            has_compounds = 'compounds' in organic_data and organic_data['compounds']
            
            if has_compounds:
                return ValidationCheck(
                    check_name="organic_completeness",
                    passed=True,
                    message="Organic compounds data present",
                    confidence=0.8
                )
            else:
                return ValidationCheck(
                    check_name="organic_completeness",
                    passed=False,
                    message="No organic compounds identified",
                    confidence=0.2
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="organic_completeness",
                passed=False,
                message=f"Error checking organic completeness: {str(e)}",
                confidence=0.0
            )
    
    def _check_insights_completeness(self, insights_data: Dict[str, Any]) -> ValidationCheck:
        """检查科学洞察完整性"""
        try:
            if not insights_data:
                return ValidationCheck(
                    check_name="insights_completeness",
                    passed=False,
                    message="No scientific insights found",
                    confidence=0.1
                )
            
            has_insights = any(field in insights_data and insights_data[field] 
                             for field in ['significance', 'conclusions', 'implications'])
            
            if has_insights:
                return ValidationCheck(
                    check_name="insights_completeness",
                    passed=True,
                    message="Scientific insights present",
                    confidence=0.8
                )
            else:
                return ValidationCheck(
                    check_name="insights_completeness",
                    passed=False,
                    message="No scientific insights identified",
                    confidence=0.2
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="insights_completeness",
                passed=False,
                message=f"Error checking insights completeness: {str(e)}",
                confidence=0.0
            )
    
    def _check_references_completeness(self, references: List[Dict[str, str]]) -> ValidationCheck:
        """检查参考文献完整性"""
        try:
            if not references:
                return ValidationCheck(
                    check_name="references_completeness",
                    passed=False,
                    message="No references found",
                    confidence=0.1
                )
            
            valid_refs = 0
            for ref in references:
                if ref.get('content') and len(ref['content'].strip()) > 10:
                    valid_refs += 1
            
            if valid_refs > 0:
                return ValidationCheck(
                    check_name="references_completeness",
                    passed=True,
                    message=f"Found {valid_refs} valid references",
                    confidence=0.8
                )
            else:
                return ValidationCheck(
                    check_name="references_completeness",
                    passed=False,
                    message="No valid references found",
                    confidence=0.2
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="references_completeness",
                passed=False,
                message=f"Error checking references completeness: {str(e)}",
                confidence=0.0
            )
    
    def _check_meteorite_classification(self, meteorite_data: Dict[str, Any]) -> ValidationCheck:
        """检查陨石分类的科学性"""
        try:
            if 'classification' not in meteorite_data:
                return ValidationCheck(
                    check_name="meteorite_classification",
                    passed=False,
                    message="No classification data",
                    confidence=0.1
                )
            
            classification = meteorite_data['classification'].lower()
            
            # 扩展的陨石分类列表
            valid_classifications = [
                # 球粒陨石
                'chondrite', 'ordinary chondrite', 'carbonaceous chondrite', 'enstatite chondrite',
                '普通球粒陨石', '碳质球粒陨石', '顽辉石球粒陨石',
                # 无球粒陨石
                'achondrite', 'eucrite', 'diogenite', 'howardite', 'shergottite', 'nakhlite', 'chassigny',
                '无球粒陨石', '钙长辉长无球粒陨石', '古铜钙长无球粒陨石',
                # 铁陨石
                'iron', 'iron meteorite', 'hexahedrite', 'octahedrite', 'ataxite',
                '铁陨石', '六面体铁陨石', '八面体铁陨石', '无结构铁陨石',
                # 石铁陨石
                'stony-iron', 'pallasite', 'mesosiderite',
                '石铁陨石', '橄榄陨铁', '中陨铁',
                # 其他
                'carbonaceous', 'primitive', 'differentiated'
            ]
            
            # 检查分类匹配
            classification_score = 0.0
            for valid_class in valid_classifications:
                if valid_class in classification:
                    classification_score = 0.9
                    break
            
            # 检查部分匹配
            if classification_score == 0.0:
                partial_matches = ['chond', 'achond', 'iron', 'stony', 'carbon']
                for partial in partial_matches:
                    if partial in classification:
                        classification_score = 0.6
                        break
            
            if classification_score >= 0.6:
                return ValidationCheck(
                    check_name="meteorite_classification",
                    passed=True,
                    message=f"Valid meteorite classification: {classification}",
                    confidence=classification_score
                )
            else:
                return ValidationCheck(
                    check_name="meteorite_classification",
                    passed=False,
                    message=f"Unrecognized classification: {classification}",
                    confidence=0.3
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="meteorite_classification",
                passed=False,
                message=f"Error checking classification: {str(e)}",
                confidence=0.0
            )
    
    def _check_organic_consistency(self, organic_data: Dict[str, Any]) -> ValidationCheck:
        """检查有机化合物的一致性"""
        try:
            if not organic_data:
                return ValidationCheck(
                    check_name="organic_consistency",
                    passed=True,
                    message="No organic data to check",
                    confidence=0.5
                )
            
            # 扩展的有机化合物列表
            compounds = organic_data.get('compounds', '').lower()
            common_organics = [
                # 氨基酸
                'amino acid', 'glycine', 'alanine', 'valine', 'leucine', 'isoleucine',
                'amino', 'acid', '氨基酸',
                # 蛋白质
                'protein', 'peptide', 'enzyme', '蛋白质', '肽',
                # 脂质
                'lipid', 'fatty acid', 'phospholipid', 'sterol', '脂质', '脂肪酸',
                # 碳水化合物
                'carbohydrate', 'sugar', 'glucose', 'fructose', 'sucrose', 'carbohydrate',
                '碳水化合物', '糖', '葡萄糖', '果糖',
                # 核酸
                'nucleic acid', 'dna', 'rna', 'nucleotide', '核酸', '核苷酸',
                # 其他有机化合物
                'organic compound', 'organic matter', 'organic material',
                '有机物', '有机化合物', '有机物质',
                # 芳香族化合物
                'aromatic', 'benzene', 'phenol', '芳香族', '苯', '酚',
                # 醇类
                'alcohol', 'ethanol', 'methanol', '醇', '乙醇', '甲醇',
                # 酸类
                'organic acid', 'acetic acid', 'formic acid', '有机酸', '乙酸', '甲酸',
                # 胺类
                'amine', 'ammonia', '胺', '氨'
            ]
            
            # 检查化合物匹配
            organic_score = 0.0
            matched_compounds = []
            
            for organic in common_organics:
                if organic in compounds:
                    organic_score = 0.8
                    matched_compounds.append(organic)
                    break
            
            # 检查检测方法的一致性
            detection_method = organic_data.get('detection_method', '').lower()
            valid_methods = [
                'gc-ms', 'lc-ms', 'hplc', 'nmr', 'ftir', 'xps', 'tem', 'sem',
                '气相色谱', '液相色谱', '核磁共振', '红外光谱', 'x射线光电子能谱',
                '透射电镜', '扫描电镜'
            ]
            
            method_score = 0.0
            if detection_method:
                for method in valid_methods:
                    if method in detection_method:
                        method_score = 0.7
                        break
            
            # 检查浓度信息的合理性
            concentration = organic_data.get('concentration', '').lower()
            concentration_score = 0.0
            if concentration:
                # 检查浓度单位
                concentration_units = ['ppm', 'ppb', '%', 'mg/kg', 'μg/g', 'ng/g']
                for unit in concentration_units:
                    if unit in concentration:
                        concentration_score = 0.6
                        break
            
            # 综合评分
            total_score = (organic_score * 0.5) + (method_score * 0.3) + (concentration_score * 0.2)
            
            if total_score >= 0.6:
                return ValidationCheck(
                    check_name="organic_consistency",
                    passed=True,
                    message=f"Reasonable organic compounds identified: {', '.join(matched_compounds[:3])}",
                    confidence=total_score
                )
            else:
                return ValidationCheck(
                    check_name="organic_consistency",
                    passed=False,
                    message="No recognizable organic compounds or methods",
                    confidence=0.4
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="organic_consistency",
                passed=False,
                message=f"Error checking organic consistency: {str(e)}",
                confidence=0.0
            )
    
    def _check_mineral_consistency(self, mineral_data: Dict[str, Any]) -> ValidationCheck:
        """检查矿物关系的一致性"""
        try:
            if not mineral_data:
                return ValidationCheck(
                    check_name="mineral_consistency",
                    passed=True,
                    message="No mineral data to check",
                    confidence=0.5
                )
            
            # 扩展的矿物列表
            minerals = mineral_data.get('minerals', '').lower()
            common_minerals = [
                # 硅酸盐矿物
                'olivine', 'pyroxene', 'plagioclase', 'feldspar', 'quartz', 'amphibole',
                '橄榄石', '辉石', '长石', '石英', '角闪石',
                # 碳酸盐矿物
                'carbonate', 'calcite', 'dolomite', 'aragonite',
                '碳酸盐', '方解石', '白云石', '文石',
                # 硫化物矿物
                'sulfide', 'pyrite', 'pyrrhotite', 'chalcopyrite', 'galena',
                '硫化物', '黄铁矿', '磁黄铁矿', '黄铜矿', '方铅矿',
                # 氧化物矿物
                'oxide', 'magnetite', 'hematite', 'ilmenite', 'chromite',
                '氧化物', '磁铁矿', '赤铁矿', '钛铁矿', '铬铁矿',
                # 其他矿物
                'spinel', 'perovskite', 'garnet', 'apatite', 'zircon',
                '尖晶石', '钙钛矿', '石榴石', '磷灰石', '锆石'
            ]
            
            # 检查矿物匹配
            mineral_score = 0.0
            matched_minerals = []
            
            for mineral in common_minerals:
                if mineral in minerals:
                    mineral_score = 0.8
                    matched_minerals.append(mineral)
                    break
            
            # 检查矿物关系的一致性
            relationships = mineral_data.get('relationships', '').lower()
            relationship_score = 0.0
            if relationships:
                # 检查关系关键词
                relationship_keywords = [
                    'association', 'paragenesis', 'intergrowth', 'replacement',
                    '共生', '伴生', '交生', '交代',
                    'crystallization', 'precipitation', 'dissolution',
                    '结晶', '沉淀', '溶解',
                    'metamorphism', 'alteration', 'weathering',
                    '变质', '蚀变', '风化'
                ]
                
                for keyword in relationship_keywords:
                    if keyword in relationships:
                        relationship_score = 0.7
                        break
            
            # 检查相互作用机制
            interactions = mineral_data.get('interactions', '').lower()
            interaction_score = 0.0
            if interactions:
                # 检查相互作用关键词
                interaction_keywords = [
                    'reaction', 'equilibrium', 'phase transition',
                    '反应', '平衡', '相变',
                    'diffusion', 'migration', 'segregation',
                    '扩散', '迁移', '分异',
                    'catalysis', 'adsorption', 'desorption',
                    '催化', '吸附', '解吸'
                ]
                
                for keyword in interaction_keywords:
                    if keyword in interactions:
                        interaction_score = 0.6
                        break
            
            # 综合评分
            total_score = (mineral_score * 0.4) + (relationship_score * 0.3) + (interaction_score * 0.3)
            
            if total_score >= 0.5:
                return ValidationCheck(
                    check_name="mineral_consistency",
                    passed=True,
                    message=f"Mineral relationships identified: {', '.join(matched_minerals[:3])}",
                    confidence=total_score
                )
            else:
                return ValidationCheck(
                    check_name="mineral_consistency",
                    passed=False,
                    message="No recognizable mineral relationships found",
                    confidence=0.3
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="mineral_consistency",
                passed=False,
                message=f"Error checking mineral consistency: {str(e)}",
                confidence=0.0
            )
    
    def _check_reference_format(self, references: List[Dict[str, str]]) -> ValidationCheck:
        """检查参考文献格式"""
        try:
            if not references:
                return ValidationCheck(
                    check_name="reference_format",
                    passed=True,
                    message="No references to check format",
                    confidence=0.5
                )
            
            valid_format_count = 0
            total_references = len(references)
            
            for ref in references:
                content = ref.get('content', '')
                if not content:
                    continue
                
                # 检查基本格式要求
                format_score = 0.0
                
                # 长度检查
                if len(content) > 20:
                    format_score += 0.2
                
                # 标点符号检查
                if any(char in content for char in ['.', ',', ':', '(', ')']):
                    format_score += 0.2
                
                # 年份检查
                if re.search(r'(19|20)\d{2}', content):
                    format_score += 0.2
                
                # 作者检查
                if re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', content):
                    format_score += 0.2
                
                # 期刊或标题检查
                if any(keyword in content.lower() for keyword in ['journal', 'proceedings', 'nature', 'science', 'journal of', 'proceedings of']):
                    format_score += 0.2
                
                if format_score >= 0.6:
                    valid_format_count += 1
            
            # 计算格式质量分数
            if total_references > 0:
                format_quality = valid_format_count / total_references
            else:
                format_quality = 0.0
            
            if format_quality >= 0.7:
                return ValidationCheck(
                    check_name="reference_format",
                    passed=True,
                    message=f"{valid_format_count}/{total_references} references have valid format",
                    confidence=0.8
                )
            elif format_quality >= 0.4:
                return ValidationCheck(
                    check_name="reference_format",
                    passed=True,
                    message=f"{valid_format_count}/{total_references} references have acceptable format",
                    confidence=0.6
                )
            else:
                return ValidationCheck(
                    check_name="reference_format",
                    passed=False,
                    message=f"Only {valid_format_count}/{total_references} references have valid format",
                    confidence=0.3
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="reference_format",
                passed=False,
                message=f"Error checking reference format: {str(e)}",
                confidence=0.0
            )
    
    def _check_reference_quantity(self, references: List[Dict[str, str]]) -> ValidationCheck:
        """检查参考文献数量"""
        try:
            if not references:
                return ValidationCheck(
                    check_name="reference_quantity",
                    passed=False,
                    message="No references found",
                    confidence=0.1
                )
            
            ref_count = len(references)
            if ref_count >= 5:
                return ValidationCheck(
                    check_name="reference_quantity",
                    passed=True,
                    message=f"Good number of references: {ref_count}",
                    confidence=0.9
                )
            elif ref_count >= 2:
                return ValidationCheck(
                    check_name="reference_quantity",
                    passed=True,
                    message=f"Acceptable number of references: {ref_count}",
                    confidence=0.7
                )
            else:
                return ValidationCheck(
                    check_name="reference_quantity",
                    passed=False,
                    message=f"Few references: {ref_count}",
                    confidence=0.3
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="reference_quantity",
                passed=False,
                message=f"Error checking reference quantity: {str(e)}",
                confidence=0.0
            )
    
    def _check_data_types(self, data: 'StructuredData') -> ValidationCheck:
        """检查数据类型"""
        try:
            # 检查基本数据类型
            type_errors = []
            
            if not isinstance(data.meteorite_data, dict):
                type_errors.append("meteorite_data should be dict")
            
            if not isinstance(data.organic_compounds, dict):
                type_errors.append("organic_compounds should be dict")
            
            if not isinstance(data.references, list):
                type_errors.append("references should be list")
            
            if not type_errors:
                return ValidationCheck(
                    check_name="data_types",
                    passed=True,
                    message="All data types are correct",
                    confidence=0.9
                )
            else:
                return ValidationCheck(
                    check_name="data_types",
                    passed=False,
                    message=f"Type errors: {', '.join(type_errors)}",
                    confidence=0.3
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="data_types",
                passed=False,
                message=f"Error checking data types: {str(e)}",
                confidence=0.0
            )
    
    def _check_data_ranges(self, data: 'StructuredData') -> ValidationCheck:
        """检查数据范围"""
        try:
            # 检查数据合理性
            range_issues = []
            
            # 检查陨石重量范围
            if 'weight' in data.meteorite_data:
                weight = data.meteorite_data['weight']
                if isinstance(weight, (int, float)) and (weight < 0 or weight > 1000000):
                    range_issues.append("meteorite weight out of reasonable range")
            
            if not range_issues:
                return ValidationCheck(
                    check_name="data_ranges",
                    passed=True,
                    message="All data ranges are reasonable",
                    confidence=0.8
                )
            else:
                return ValidationCheck(
                    check_name="data_ranges",
                    passed=False,
                    message=f"Range issues: {', '.join(range_issues)}",
                    confidence=0.4
                )
                
        except Exception as e:
            return ValidationCheck(
                check_name="data_ranges",
                passed=False,
                message=f"Error checking data ranges: {str(e)}",
                confidence=0.0
            )
    
    def _get_check_weight(self, check_name: str) -> float:
        """获取检查权重"""
        weights = {
            'meteorite_completeness': 1.0,
            'organic_completeness': 0.8,
            'insights_completeness': 0.8,
            'references_completeness': 0.6,
            'meteorite_classification': 0.9,
            'organic_consistency': 0.7,
            'mineral_consistency': 0.6,
            'reference_format': 0.5,
            'reference_quantity': 0.4,
            'data_types': 0.3,
            'data_ranges': 0.3
        }
        return weights.get(check_name, 0.5)
    
    def _generate_validation_notes(self, validation_checks: List[ValidationCheck]) -> str:
        """生成验证说明"""
        try:
            passed_checks = [check for check in validation_checks if check.passed]
            failed_checks = [check for check in validation_checks if not check.passed]
            
            notes = f"Validation completed: {len(passed_checks)} checks passed, {len(failed_checks)} checks failed.\n"
            
            if failed_checks:
                notes += "Failed checks:\n"
                for check in failed_checks:
                    notes += f"- {check.check_name}: {check.message}\n"
            
            return notes.strip()
            
        except Exception as e:
            logger.error(f"Error generating validation notes: {str(e)}")
            return f"Error generating validation notes: {str(e)}"
