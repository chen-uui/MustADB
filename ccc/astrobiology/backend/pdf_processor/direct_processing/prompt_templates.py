"""
提示词模板 - 用于构建LLM分析提示词
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class PromptTemplates:
    """提示词模板"""
    
    def __init__(self):
        """初始化提示词模板"""
        self.DOCUMENT_ANALYSIS_PROMPT = self._build_document_analysis_prompt()
        self.METEORITE_EXTRACTION_PROMPT = self._build_meteorite_extraction_prompt()
        self.ORGANIC_ANALYSIS_PROMPT = self._build_organic_analysis_prompt()
        
        logger.info("PromptTemplates initialized")
    
    def build_analysis_prompt(self, text: str, options: Dict[str, Any] = None) -> str:
        """
        构建分析提示词
        
        Args:
            text: 文档文本
            options: 分析选项
            
        Returns:
            str: 完整的提示词
        """
        try:
            # 统一使用简化的文档分析提示词
            base_prompt = self.DOCUMENT_ANALYSIS_PROMPT
            
            # 构建完整提示词
            full_prompt = f"{base_prompt}\n\n文档内容：\n{text}"
            
            return full_prompt
            
        except Exception as e:
            logger.error(f"Error building analysis prompt: {str(e)}")
            return self._build_fallback_prompt(text)
    
    def _build_document_analysis_prompt(self) -> str:
        """构建文档分析提示词"""
        return """你是一个专业的天体生物学研究助手。请分析以下文档，提取相关信息并返回JSON格式数据。

重要规则：
1. 仔细阅读文档，寻找具体的陨石名称、发现地点、分类信息
2. 如果文档不包含陨石、小行星、彗星等天体生物学相关内容，请在相应字段中明确说明"该论文不包含相关内容"
3. 每个字段都必须填写，不能为空
4. 优先提取具体信息，避免使用"Unknown"或"Not specified"
5. 在explanation字段中详细解释为什么没有相关数据

{
  "meteorite_data": {
    "name": "陨石名称（优先提取具体名称如'NWA 7034'、'Murchison'、'Allende'等，如无具体名称请填写'该论文不包含陨石相关内容'）",
    "classification": "分类（优先提取具体分类如'Martian shergottite'、'CM chondrite'、'CI chondrite'等，如无具体分类请填写'该论文不包含陨石相关内容'）",
    "location": "地点（优先提取具体发现地点如'Antarctica'、'Australia'、'Northwest Africa'等，如无具体地点请填写'该论文不包含陨石相关内容'）",
    "date": "日期（优先提取具体发现年份如'1969'、'2011'等，如无具体日期请填写'该论文不包含陨石相关内容'）",
    "explanation": "陨石数据说明（解释陨石数据的发现情况，例如：'论文中详细分析了NWA 7034陨石的矿物学和有机化合物组成'）"
  },
  "organic_compounds": {
    "amino_acids": ["具体氨基酸名称列表，如['glycine', 'alanine', 'valine']，如无请填写[]"],
    "carboxylic_acids": ["具体羧酸名称列表，如['formic acid', 'acetic acid']，如无请填写[]"],
    "nucleotide_bases": ["具体核苷酸碱基名称列表，如['adenine', 'guanine']，如无请填写[]"],
    "aromatic_compounds": ["具体芳香化合物名称列表，如['benzene', 'toluene']，如无请填写[]"],
    "isotopic_signatures": {
      "carbon_isotope_ratio": "碳同位素比值（如'δ13C = -25‰'），如无请填写'Not specified'",
      "nitrogen_isotope_ratio": "氮同位素比值（如'δ15N = +50‰'），如无请填写'Not specified'"
    },
    "total_organic_carbon": "总有机碳含量（如'2.5 wt%'），如无请填写'Not specified'"
  },
  "mineral_relationships": {
    "minerals": ["矿物种类列表，如无矿物内容，请填写['该论文不包含矿物相关内容']"],
    "associations": [
      {
        "mineral": "矿物名称",
        "organic_compounds": ["关联的有机化合物列表"],
        "association_type": "关联类型（如：离子交换、吸附、络合、物理包裹等）",
        "description": "关联描述（详细说明矿物与有机化合物的相互作用）",
        "evidence": "证据（如：FTIR光谱特征、XRD衍射峰、TEM图像等）",
        "significance": "科学意义（如：保护有机分子、催化反应、生命起源意义等）"
      }
    ],
    "explanation": "矿物关系说明（解释矿物关系的发现情况，例如：'论文中分析了矿物与有机质的相互作用'）"
  },
  "scientific_insights": {
    "significance": "科学意义（如无相关科学意义，请填写'该论文不包含相关科学意义'）",
    "explanation": "科学意义说明（解释论文的科学价值，例如：'该研究为理解小行星表面有机物质的来源和分布提供了重要信息'）"
  },
  "document_analysis": {
    "content_type": "文档类型（陨石研究/小行星研究/彗星研究/其他天体生物学研究/非天体生物学研究）",
    "relevance": "与天体生物学研究的相关性（高/中/低/无）",
    "suggestion": "建议（如不相关，请说明原因并建议使用其他类型的论文）",
    "summary": "文档总结（简要说明论文的主要内容和发现）"
  }
}

重要：请严格按照上述JSON格式返回，特别注意mineral_relationships结构：
- minerals: 矿物种类数组
- associations: 关联信息数组，每个关联包含：
  * mineral: 矿物名称
  * organic_compounds: 关联的有机化合物数组
  * association_type: 关联类型
  * description: 详细描述
  * evidence: 实验证据
  * significance: 科学意义
- explanation: 整体说明

如果论文中没有矿物-有机化合物关联信息，associations应为空数组[]，但minerals和explanation仍需填写。

请不要返回references（参考文献）或其他未指定的字段。不要在字段值中包含论文引用、作者信息或参考文献列表。

确保每个字段都有值，即使是"该论文不包含相关内容"也要填写。

请直接返回JSON，不要添加任何markdown格式、代码块标记或其他文字。"""
    
    def _build_meteorite_extraction_prompt(self) -> str:
        """构建陨石数据提取提示词"""
        return """
你是一个专业的陨石学研究助手，具有深厚的陨石学、矿物学和宇宙化学背景。请专注于从以下科学论文中提取陨石相关信息。

请重点提取以下信息：

1. 陨石基本信息
   - 陨石名称和编号
   - 分类类型（球粒陨石、无球粒陨石、铁陨石、石铁陨石等）
   - 亚分类信息
   - 发现地点和日期
   - 发现者信息

2. 物理化学特征
   - 重量和尺寸
   - 密度和磁性
   - 颜色和质地
   - 主要矿物组成
   - 化学成分分析
   - 同位素组成

3. 形成历史和来源
   - 形成年龄
   - 母体信息
   - 形成环境
   - 演化历史
   - 撞击历史

4. 特殊发现或异常特征
   - 异常矿物
   - 特殊结构
   - 有机物质
   - 水蚀变特征
   - 冲击变质特征

5. 科学意义
   - 对陨石学的贡献
   - 对太阳系演化的认识
   - 对生命起源研究的启示

返回JSON格式的陨石数据：
{
  "meteorite_data": {
    "name": "陨石名称或编号",
    "classification": "详细分类信息",
    "location": "发现地点",
    "date": "发现日期",
    "weight": "重量",
    "composition": "化学成分",
    "age": "形成年龄",
    "origin": "来源信息",
    "physical_properties": "物理性质",
    "chemical_properties": "化学性质",
    "mineralogy": "矿物学特征",
    "special_features": "特殊特征",
    "scientific_significance": "科学意义"
  }
}
"""
    
    def _build_organic_analysis_prompt(self) -> str:
        """构建有机化合物分析提示词"""
        return """
你是一个专业的有机化学和天体生物学研究助手，具有深厚的有机化学、分析化学和生命起源研究背景。请专注于从以下科学论文中分析有机化合物相关信息。

请重点分析以下内容：

1. 识别的有机化合物种类
   - 氨基酸及其衍生物
   - 蛋白质和肽类
   - 脂质和脂肪酸
   - 碳水化合物和糖类
   - 核酸和核苷酸
   - 芳香族化合物
   - 醇类、酸类、胺类
   - 其他有机化合物

2. 化合物浓度和分布
   - 具体浓度数值（包括单位）
   - 空间分布特征
   - 时间变化规律
   - 浓度梯度分析

3. 检测方法和分析技术
   - 气相色谱-质谱（GC-MS）
   - 液相色谱-质谱（LC-MS）
   - 高效液相色谱（HPLC）
   - 核磁共振（NMR）
   - 红外光谱（FTIR）
   - X射线光电子能谱（XPS）
   - 透射电镜（TEM）
   - 扫描电镜（SEM）
   - 其他分析技术

4. 有机化合物的来源和形成机制
   - 原生来源（太阳星云、星际介质）
   - 次生来源（水蚀变、热变质）
   - 形成机制（合成、分解、转化）
   - 环境条件（温度、压力、pH值）

5. 与生命起源的关联
   - 生命前化学意义
   - 有机合成路径
   - 化学演化过程
   - 生命起源假说支持

6. 科学意义和影响
   - 对天体生物学的贡献
   - 对生命起源研究的启示
   - 对有机化学的贡献
   - 未来研究方向

返回JSON格式的有机化合物数据：
{
  "organic_compounds": {
    "compounds": "识别的有机化合物列表",
    "concentration": "浓度信息（包括单位）",
    "detection_method": "检测方法",
    "distribution": "分布特征",
    "origin": "来源分析",
    "formation_mechanism": "形成机制",
    "life_origin_significance": "生命起源意义",
    "scientific_impact": "科学影响",
    "analytical_techniques": "分析技术",
    "environmental_conditions": "环境条件"
  }
}
"""
    
    def _build_additional_instructions(self, options: Dict[str, Any] = None) -> str:
        """构建额外指令"""
        if not options:
            return ""
        
        instructions = []
        
        # 添加关注点指令
        if options.get('focus'):
            focus = options['focus']
            if focus == 'meteorite':
                instructions.append("请重点关注陨石相关的数据和信息。")
            elif focus == 'organic':
                instructions.append("请重点关注有机化合物相关的数据和信息。")
            elif focus == 'mineral':
                instructions.append("请重点关注矿物关系相关的数据和信息。")
        
        # 添加详细程度指令
        if options.get('detail_level'):
            detail_level = options['detail_level']
            if detail_level == 'high':
                instructions.append("请提供详细的分析和数据提取。")
            elif detail_level == 'medium':
                instructions.append("请提供中等详细程度的分析。")
            elif detail_level == 'low':
                instructions.append("请提供简要的分析摘要。")
        
        # 添加语言指令
        if options.get('language'):
            language = options['language']
            if language == 'chinese':
                instructions.append("请使用中文进行分析和输出。")
            elif language == 'english':
                instructions.append("Please provide analysis in English.")
        
        # 添加置信度要求
        if options.get('confidence_threshold'):
            threshold = options['confidence_threshold']
            instructions.append(f"请确保分析结果的置信度不低于{threshold}。")
        
        return "\n".join(instructions) if instructions else ""
    
    def _build_fallback_prompt(self, text: str) -> str:
        """构建备用提示词"""
        return f"""
请分析以下科学论文内容，提取关键信息：

{text}

请返回JSON格式的结构化数据，包含：
- meteorite_data: 陨石相关信息
- organic_compounds: 有机化合物信息
- scientific_insights: 科学洞察
- references: 参考文献

请确保数据准确性和完整性。
"""
    
    def build_validation_prompt(self, extracted_data: Dict[str, Any]) -> str:
        """
        构建验证提示词
        
        Args:
            extracted_data: 提取的数据
            
        Returns:
            str: 验证提示词
        """
        return f"""
请验证以下从天体生物学论文中提取的数据的准确性和完整性：

{extracted_data}

请检查：
1. 数据的科学准确性
2. 信息的完整性
3. 逻辑一致性
4. 格式正确性

返回验证结果，包括：
- 准确性评分 (0-100)
- 完整性评分 (0-100)
- 建议改进点
- 置信度评估
"""
    
    def build_summary_prompt(self, analysis_result: Dict[str, Any]) -> str:
        """
        构建摘要提示词
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            str: 摘要提示词
        """
        return f"""
请基于以下天体生物学论文分析结果，生成一个简洁的科学摘要：

{analysis_result}

请生成：
1. 研究概述 (100字以内)
2. 主要发现 (200字以内)
3. 科学意义 (150字以内)
4. 关键数据摘要

请使用专业的科学写作风格，确保准确性和可读性。
"""
    
    def build_comparison_prompt(self, data1: Dict[str, Any], data2: Dict[str, Any]) -> str:
        """
        构建比较分析提示词
        
        Args:
            data1: 第一个分析结果
            data2: 第二个分析结果
            
        Returns:
            str: 比较分析提示词
        """
        return f"""
请比较以下两个天体生物学论文的分析结果：

论文1分析结果：
{data1}

论文2分析结果：
{data2}

请提供：
1. 相似性分析
2. 差异性分析
3. 互补性分析
4. 综合科学意义
5. 研究趋势分析

请使用结构化的比较框架，确保分析的客观性和科学性。
"""
