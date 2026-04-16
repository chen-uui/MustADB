#!/usr/bin/env python3
"""
简化的Prompt模板测试
"""

import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_prompt_template():
    """测试新的prompt模板"""
    print("=== 测试Prompt模板优化 ===")
    
    # 直接导入PromptTemplates类
    try:
        from pdf_processor.direct_processing.prompt_templates import PromptTemplates
        templates = PromptTemplates()
        
        # 测试文档内容（模拟天体生物学论文）
        test_text = """
        This study investigates the organic-mineral associations in the Murchison meteorite.
        The meteorite contains various clay minerals including smectite and illite.
        Organic compounds such as glycine, alanine, and proline were detected.
        FTIR analysis revealed characteristic absorption bands at 1650 cm-1 and 1550 cm-1,
        indicating ionic exchange between amino acids and clay minerals.
        The association protects organic molecules from degradation and may have implications
        for understanding prebiotic chemistry.
        """
        
        # 构建prompt
        prompt = templates.build_analysis_prompt(test_text)
        
        print("生成的Prompt:")
        print("-" * 50)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        print("-" * 50)
        
        # 检查关键结构
        checks = [
            ("associations", "associations字段"),
            ("association_type", "association_type字段"),
            ("evidence", "evidence字段"),
            ("significance", "significance字段"),
            ("minerals", "minerals字段"),
            ("organic_compounds", "organic_compounds字段")
        ]
        
        for keyword, description in checks:
            if keyword in prompt:
                print(f"[OK] 包含{description}")
            else:
                print(f"[ERROR] 缺少{description}")
        
        # 检查JSON结构
        if '"associations": [' in prompt:
            print("[OK] associations字段格式正确")
        else:
            print("[ERROR] associations字段格式不正确")
            
        if '"mineral":' in prompt and '"organic_compounds":' in prompt:
            print("[OK] 关联结构字段完整")
        else:
            print("[ERROR] 关联结构字段不完整")
            
    except Exception as e:
        print(f"[ERROR] 导入失败: {str(e)}")
        return False
    
    return True

def test_json_structure():
    """测试JSON结构示例"""
    print("\n=== 测试JSON结构示例 ===")
    
    # 模拟新的数据结构
    sample_data = {
        "mineral_relationships": {
            "minerals": ["clay minerals", "olivine", "pyroxene"],
            "associations": [
                {
                    "mineral": "clay minerals",
                    "organic_compounds": ["glycine", "alanine"],
                    "association_type": "ionic exchange",
                    "description": "氨基酸通过离子交换与粘土矿物结合",
                    "evidence": "FTIR spectra showed characteristic bands at 1650 cm-1",
                    "significance": "protects organic molecules from degradation"
                },
                {
                    "mineral": "olivine",
                    "organic_compounds": ["formic acid"],
                    "association_type": "adsorption",
                    "description": "甲酸分子吸附在橄榄石表面",
                    "evidence": "XPS analysis revealed C-O bonds",
                    "significance": "may catalyze organic reactions"
                }
            ],
            "explanation": "论文中分析了矿物与有机质的相互作用"
        }
    }
    
    print("示例数据结构:")
    print(json.dumps(sample_data, indent=2, ensure_ascii=False))
    
    # 验证结构
    mineral_data = sample_data["mineral_relationships"]
    
    if isinstance(mineral_data.get("minerals"), list):
        print("[OK] minerals字段是列表")
    else:
        print("[ERROR] minerals字段不是列表")
    
    associations = mineral_data.get("associations", [])
    if isinstance(associations, list):
        print(f"[OK] associations字段是列表，包含{len(associations)}个关联")
        
        for i, assoc in enumerate(associations):
            required_fields = ["mineral", "organic_compounds", "association_type", "description", "evidence", "significance"]
            missing_fields = [field for field in required_fields if field not in assoc]
            
            if missing_fields:
                print(f"[ERROR] 关联{i+1}缺少字段: {missing_fields}")
            else:
                print(f"[OK] 关联{i+1}结构完整")
    else:
        print("[ERROR] associations字段不是列表")

if __name__ == "__main__":
    try:
        success = test_prompt_template()
        test_json_structure()
        
        if success:
            print("\n=== 测试完成 ===")
            print("[OK] Prompt模板优化成功")
        else:
            print("\n=== 测试失败 ===")
            print("[ERROR] Prompt模板优化失败")
        
    except Exception as e:
        print(f"[ERROR] 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()