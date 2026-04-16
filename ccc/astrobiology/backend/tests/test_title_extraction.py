#!/usr/bin/env python
"""
测试PDF标题提取优化效果
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from pdf_processor.pdf_utils import PDFUtils
from pdf_processor.models import PDFDocument

def test_title_extraction():
    """测试标题提取效果"""
    print("🔍 测试PDF标题提取优化效果...")
    
    # 获取几个已处理的文档进行测试
    documents = PDFDocument.objects.filter(processed=True)[:5]
    
    for doc in documents:
        print(f"\n📄 测试文档: {doc.filename}")
        print(f"   当前标题: {doc.title}")
        
        # 重新提取标题
        if os.path.exists(doc.file_path):
            try:
                result = PDFUtils.extract_text_and_metadata(doc.file_path)
                if result['success']:
                    new_title = result['metadata'].get('title', '')
                    print(f"   提取的标题: {new_title}")
                    
                    # 检查是否是DOI
                    import re
                    if re.match(r'^10\.\d{4,}\/[^\s]+', new_title):
                        print("   ⚠️  仍然是DOI格式")
                    else:
                        print("   ✅ 成功提取到非DOI标题")
                else:
                    print(f"   ❌ 提取失败: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"   ❌ 处理错误: {e}")
        else:
            print("   ❌ 文件不存在")

if __name__ == "__main__":
    test_title_extraction()
