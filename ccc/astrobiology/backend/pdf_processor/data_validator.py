"""
数据验证器
用于验证和清洗提取的陨石数据
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    cleaned_data: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    warnings: List[str] = field(default_factory=list)

class DataValidator:
    """数据验证器"""
    
    def __init__(self):
        """初始化数据验证器"""
        self.required_fields = [
            'name', 'classification', 'discovery_location', 'origin',
            'organic_compounds', 'contamination_exclusion_method', 'references'
        ]
        
        # 定义有效的陨石分类
        self.valid_classifications = {
            # 普通球粒陨石
            'H', 'L', 'LL',
            # 碳质球粒陨石
            'CI', 'CM', 'CO', 'CV', 'CR', 'CK', 'CH', 'CB',
            # 顽火辉石球粒陨石
            'EH', 'EL',
            # 无球粒陨石
            'Acapulcoite', 'Angrite', 'Aubrite', 'Brachinite', 'Diogenite', 
            'Eucrite', 'Howardite', 'Lodranite', 'Martian', 'Lunar',
            'Ureilite', 'Winonaite',
            # 铁陨石
            'IAB', 'IIAB', 'IIIAB', 'IVAB', 'IC', 'IIICD', 'IIF', 'IIG',
            # 石铁陨石
            'Pallasite', 'Mesosiderite'
        }
        
        # 常见的有机化合物
        self.known_organic_compounds = {
            'amino_acids': [
                '甘氨酸', '丙氨酸', '缬氨酸', '亮氨酸', '异亮氨酸',
                '脯氨酸', '苯丙氨酸', '酪氨酸', '色氨酸', '丝氨酸',
                '苏氨酸', '半胱氨酸', '蛋氨酸', '天冬酰胺', '谷氨酰胺',
                '天冬氨酸', '谷氨酸', '赖氨酸', '精氨酸', '组氨酸'
            ],
            'carboxylic_acids': [
                '乙酸', '丙酸', '丁酸', '戊酸', '己酸'
            ],
            'aromatic_compounds': [
                '苯', '甲苯', '二甲苯', '萘', '蒽', '菲'
            ],
            'nucleotide_bases': [
                '腺嘌呤', '鸟嘌呤', '胞嘧啶', '胸腺嘧啶', '尿嘧啶'
            ]
        }
    
    def validate_meteorite_data(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证陨石数据
        
        Args:
            data: 待验证的数据
            
        Returns:
            ValidationResult: 验证结果
        """
        if not isinstance(data, dict):
            return ValidationResult(
                is_valid=False,
                cleaned_data={},
                errors=["数据必须是字典类型"],
                confidence_score=0.0
            )
        
        cleaned_data = {}
        errors = []
        warnings = []
        field_scores = {}
        
        # 验证必需字段
        for field in self.required_fields:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
                field_scores[field] = 0.0
            else:
                # 清洗字段数据
                cleaned_value, score, field_warnings = self._clean_field(field, data[field])
                cleaned_data[field] = cleaned_value
                field_scores[field] = score
                warnings.extend(field_warnings)
        
        # 如果缺少必需字段，直接返回错误
        if errors:
            return ValidationResult(
                is_valid=False,
                cleaned_data=cleaned_data,
                errors=errors,
                confidence_score=0.0,
                warnings=warnings
            )
        
        # 验证特定字段
        self._validate_name(cleaned_data, field_scores, warnings)
        self._validate_classification(cleaned_data, field_scores, warnings)
        self._validate_organic_compounds(cleaned_data, field_scores, warnings)
        
        # 计算总体置信度分数
        total_score = sum(field_scores.values()) / len(field_scores) if field_scores else 0.0
        
        return ValidationResult(
            is_valid=True,
            cleaned_data=cleaned_data,
            errors=errors,
            confidence_score=total_score,
            warnings=warnings
        )
    
    def _clean_field(self, field_name: str, value: Any) -> tuple:
        """
        清洗字段数据
        
        Args:
            field_name: 字段名称
            value: 字段值
            
        Returns:
            tuple: (清洗后的值, 字段分数, 警告列表)
        """
        warnings = []
        score = 1.0
        
        if field_name == 'name':
            if not value or value in ['Unknown', '']:
                warnings.append("陨石名称未知")
                score = 0.5
                return 'Unknown', score, warnings
            return str(value).strip(), score, warnings
            
        elif field_name == 'classification':
            if not value or value in ['Unknown', '']:
                warnings.append("陨石分类未知")
                score = 0.5
                return 'Unknown', score, warnings
            return str(value).strip(), score, warnings
            
        elif field_name == 'discovery_location':
            if not value or value in ['Unknown', '']:
                warnings.append("发现地点未知")
                score = 0.7
                return 'Unknown', score, warnings
            return str(value).strip(), score, warnings
            
        elif field_name == 'origin':
            if not value or value in ['Unknown', '']:
                warnings.append("起源未知")
                score = 0.7
                return 'Unknown', score, warnings
            return str(value).strip(), score, warnings
            
        elif field_name == 'organic_compounds':
            if not isinstance(value, dict):
                warnings.append("有机化合物数据格式不正确")
                score = 0.3
                return {}, score, warnings
            return value, score, warnings
            
        elif field_name == 'contamination_exclusion_method':
            if not value or value in ['Unknown', 'Not specified', '']:
                warnings.append("污染排除方法未指定")
                score = 0.5
                return 'Not specified', score, warnings
            return str(value).strip(), score, warnings
            
        elif field_name == 'references':
            if not isinstance(value, list):
                warnings.append("参考文献必须是列表格式")
                score = 0.8
                return [], score, warnings
            return value, score, warnings
            
        else:
            # 其他字段保持原值
            return value, score, warnings
    
    def _validate_name(self, data: Dict[str, Any], field_scores: Dict[str, float], warnings: List[str]):
        """验证陨石名称"""
        name = data.get('name', '')
        if name and name != 'Unknown':
            # 检查名称格式
            if len(name) < 2:
                warnings.append("陨石名称过短")
                field_scores['name'] = 0.7
    
    def _validate_classification(self, data: Dict[str, Any], field_scores: Dict[str, float], warnings: List[str]):
        """验证陨石分类"""
        classification = data.get('classification', '')
        if classification and classification != 'Unknown':
            # 检查是否为已知分类
            found = False
            for valid_class in self.valid_classifications:
                if valid_class in classification.upper():
                    found = True
                    break
            
            if not found:
                warnings.append(f"未知的陨石分类: {classification}")
                field_scores['classification'] = 0.6
    
    def _validate_organic_compounds(self, data: Dict[str, Any], field_scores: Dict[str, float], warnings: List[str]):
        """验证有机化合物数据"""
        organic_compounds = data.get('organic_compounds', {})
        if not isinstance(organic_compounds, dict):
            warnings.append("有机化合物数据格式不正确")
            field_scores['organic_compounds'] = 0.3
            return
        
        # 检查各个子字段
        total_compounds = 0
        known_compounds = 0
        
        for category, compounds in organic_compounds.items():
            if isinstance(compounds, list):
                total_compounds += len(compounds)
                # 检查是否包含已知化合物
                if category in self.known_organic_compounds:
                    known_list = self.known_organic_compounds[category]
                    for compound in compounds:
                        if compound in known_list:
                            known_compounds += 1
        
        # 根据已知化合物比例调整分数
        if total_compounds > 0:
            known_ratio = known_compounds / total_compounds
            field_scores['organic_compounds'] = 0.5 + (0.5 * known_ratio)
        else:
            field_scores['organic_compounds'] = 0.5
    
    def validate_json_structure(self, json_str: str) -> ValidationResult:
        """
        验证JSON结构
        
        Args:
            json_str: JSON字符串
            
        Returns:
            ValidationResult: 验证结果
        """
        try:
            data = json.loads(json_str)
            return self.validate_meteorite_data(data)
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                cleaned_data={},
                errors=[f"JSON解析错误: {str(e)}"],
                confidence_score=0.0
            )