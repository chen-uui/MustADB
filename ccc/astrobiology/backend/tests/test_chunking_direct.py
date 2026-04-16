#!/usr/bin/env python
"""
直接测试分块功能
"""
import os
import sys
sys.path.insert(0, '.')

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')

import django
django.setup()

from pdf_processor.pdf_utils import PDFUtils

def test_chunking():
    print("🧪 直接测试分块功能...")
    
    # 获取第一个PDF文档
    from pdf_processor.models import PDFDocument
    doc = PDFDocument.objects.first()
    if not doc:
        print("❌ 没有找到文档")
        return
    
    print(f"📄 测试文档: {doc.title}")
    print(f"   文件路径: {doc.file_path}")
    
    # 测试不同的分块大小（token）
    chunk_sizes = [700, 1200]
    
    for chunk_size in chunk_sizes:
        print(f"\n📦 测试分块大小: {chunk_size} token")
        try:
            extraction_result = PDFUtils.extract_text_and_chunks(
                doc.file_path, 
                chunk_size=chunk_size, 
                overlap=120
            )
            
            if extraction_result['success']:
                chunks = extraction_result['chunks']
                print(f"  分块数量: {len(chunks)}")
                if chunks:
                    avg_length = sum(chunk['chunk_length'] for chunk in chunks) / len(chunks)
                    max_length = max(chunk['chunk_length'] for chunk in chunks)
                    min_length = min(chunk['chunk_length'] for chunk in chunks)
                    print(f"  平均长度: {avg_length:.0f} token")
                    print(f"  最大长度: {max_length} token")
                    print(f"  最小长度: {min_length} token")
                    print(f"  第一个分块预览: {chunks[0]['chunk_text'][:100]}...")
            else:
                print(f"  ❌ 提取失败: {extraction_result.get('error', '未知错误')}")
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")

if __name__ == "__main__":
    test_chunking()

