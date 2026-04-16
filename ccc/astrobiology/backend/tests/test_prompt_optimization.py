#!/usr/bin/env python3
"""
测试Prompt优化效果
"""

import os
import sys
import django
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from pdf_processor.direct_processing.prompt_templates import PromptTemplates
from pdf_processor.direct_processing.direct_processor import DirectProcessor
from pdf_processor.models import DirectProcessingResult

def test_prompt_template():
    """测试新的prompt模板"""
    print("=== 测试Prompt模板优化 ===")
    
    # 初始化prompt模板
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
    print(prompt)
    print("-" * 50)
    
    # 检查关键结构
    if "associations" in prompt:
        print("✅ 包含associations字段")
    else:
        print("❌ 缺少associations字段")
    
    if "association_type" in prompt:
        print("✅ 包含association_type字段")
    else:
        print("❌ 缺少association_type字段")
    
    if "evidence" in prompt:
        print("✅ 包含evidence字段")
    else:
        print("❌ 缺少evidence字段")
    
    if "significance" in prompt:
        print("✅ 包含significance字段")
    else:
        print("❌ 缺少significance字段")

def test_extraction_with_sample_papers():
    """使用样本论文测试提取效果"""
    print("\n=== 测试样本论文提取 ===")
    
    # 查找PDF文件
    pdf_dir = project_root / "pdfs"
    if not pdf_dir.exists():
        pdf_dir = project_root.parent / "pdfs"
    
    if not pdf_dir.exists():
        print("❌ 未找到PDF目录")
        return
    
    # 获取前3个PDF文件
    pdf_files = list(pdf_dir.glob("*.pdf"))[:3]
    
    if not pdf_files:
        print("❌ 未找到PDF文件")
        return
    
    processor = DirectProcessor()
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n--- 测试论文 {i}: {pdf_file.name} ---")
        
        try:
            # 处理PDF
            result = processor.process_document(str(pdf_file))
            
            if result:
                print(f"✅ 处理成功")
                print(f"   文档标题: {result.document_title}")
                print(f"   置信度: {result.confidence_score}")
                
                # 检查mineral_relationships结构
                mineral_data = result.mineral_relationships
                if isinstance(mineral_data, dict):
                    print(f"   矿物数据: {mineral_data.get('minerals', 'N/A')}")
                    
                    associations = mineral_data.get('associations', [])
                    if isinstance(associations, list):
                        print(f"   关联数量: {len(associations)}")
                        
                        for j, assoc in enumerate(associations[:2]):  # 只显示前2个
                            if isinstance(assoc, dict):
                                print(f"     关联 {j+1}:")
                                print(f"       矿物: {assoc.get('mineral', 'N/A')}")
                                print(f"       有机化合物: {assoc.get('organic_compounds', 'N/A')}")
                                print(f"       关联类型: {assoc.get('association_type', 'N/A')}")
                                print(f"       证据: {assoc.get('evidence', 'N/A')[:50]}...")
                    else:
                        print(f"   ❌ associations不是列表格式")
                else:
                    print(f"   ❌ mineral_relationships不是字典格式")
            else:
                print(f"❌ 处理失败")
                
        except Exception as e:
            print(f"❌ 处理异常: {str(e)}")

def analyze_existing_results():
    """分析现有的处理结果"""
    print("\n=== 分析现有处理结果 ===")
    
    # 获取最近的5个处理结果
    results = DirectProcessingResult.objects.all().order_by('-created_at')[:5]
    
    if not results:
        print("❌ 没有找到处理结果")
        return
    
    print(f"找到 {len(results)} 个处理结果")
    
    for i, result in enumerate(results, 1):
        print(f"\n--- 结果 {i}: {result.document_title} ---")
        
        # 分析mineral_relationships结构
        mineral_data = result.mineral_relationships
        
        if isinstance(mineral_data, dict):
            minerals = mineral_data.get('minerals', [])
            associations = mineral_data.get('associations', [])
            
            print(f"   矿物种类: {len(minerals) if isinstance(minerals, list) else 'N/A'}")
            print(f"   关联数量: {len(associations) if isinstance(associations, list) else 'N/A'}")
            
            # 检查关联结构
            if isinstance(associations, list) and associations:
                first_assoc = associations[0]
                if isinstance(first_assoc, dict):
                    required_fields = ['mineral', 'organic_compounds', 'association_type', 'description', 'evidence', 'significance']
                    missing_fields = [field for field in required_fields if field not in first_assoc]
                    
                    if missing_fields:
                        print(f"   ❌ 缺少字段: {missing_fields}")
                    else:
                        print(f"   ✅ 关联结构完整")
                else:
                    print(f"   ❌ 关联不是字典格式")
            else:
                print(f"   ℹ️  无关联数据")
        else:
            print(f"   ❌ mineral_relationships不是字典格式")

if __name__ == "__main__":
    try:
        test_prompt_template()
        test_extraction_with_sample_papers()
        analyze_existing_results()
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
