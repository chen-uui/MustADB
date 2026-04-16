#!/usr/bin/env python
"""
测试分块功能
"""
import os
import sys
sys.path.insert(0, '.')

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')

import django
django.setup()

from pdf_processor.pdf_utils import PDFUtils

# 测试分块功能
def test_chunking():
    print("🧪 测试分块功能...")
    
    # 创建一个测试文本
    test_text = "A" * 50000  # 5万字符（仅用于长度测试）
    print(f"测试文本长度: {len(test_text)} 字符")
    
    # 模拟页面数据
    pages = [{'text': test_text, 'page_num': 1}]
    
    # 测试不同的分块大小（token）
    chunk_sizes = [700, 1200]
    
    for chunk_size in chunk_sizes:
        print(f"\n📦 测试分块大小: {chunk_size} token")
        chunks = PDFUtils.chunk_text_by_pages(pages, chunk_size=chunk_size, overlap=120)
        print(f"  分块数量: {len(chunks)}")
        if chunks:
            print(f"  第一个分块长度(token): {chunks[0]['chunk_length']}")
            print(f"  平均分块长度(token): {sum(chunk['chunk_length'] for chunk in chunks) / len(chunks):.0f}")

if __name__ == "__main__":
    test_chunking()

