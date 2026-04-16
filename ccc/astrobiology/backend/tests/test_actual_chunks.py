#!/usr/bin/env python
"""
测试实际分块数量
"""
import os
import sys
sys.path.insert(0, '.')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')

import django
django.setup()

from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateDocumentProcessor, WeaviateConfig

def test_actual_chunks():
    print("🔍 检查实际分块数量...")
    
    # 获取第一个文档
    doc = PDFDocument.objects.first()
    if not doc:
        print("❌ 没有找到文档")
        return
    
    print(f"📄 文档: {doc.title}")
    print(f"   页数: {doc.page_count}")
    print(f"   处理状态: {doc.processed}")
    
    # 初始化Weaviate处理器
    processor = WeaviateDocumentProcessor(WeaviateConfig())
    
    # 获取该文档的分块
    chunks = processor.get_document_chunks(str(doc.id), limit=10000, offset=0)
    
    print(f"\n📊 实际分块数量: {len(chunks)}")
    
    if chunks:
        print(f"\n📝 前3个分块信息:")
        for i, chunk in enumerate(chunks[:3]):
            content = chunk.get('content', '')
            print(f"  {i+1}. 长度: {len(content)} 字符")
            print(f"     内容预览: {content[:100]}...")
    
    processor.close()

if __name__ == "__main__":
    test_actual_chunks()


