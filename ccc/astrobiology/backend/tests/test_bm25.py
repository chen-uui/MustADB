#!/usr/bin/env python3
"""
测试BM25搜索功能
"""

import os
import sys
import django

# 设置环境变量
os.environ['SECRET_KEY'] = 'django-insecure-test-key-for-development-only'
os.environ['JWT_SECRET'] = 'jwt-secret-key-for-development-only'

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

def test_bm25_search():
    """测试BM25搜索功能"""
    print("🔍 测试BM25搜索功能")
    print("=" * 50)
    
    try:
        from pdf_processor.rag_service import RAGService
        
        rag = RAGService()
        rag.initialize()
        
        client = rag.weaviate_client
        collection = client.collections.get('PDFDocument')
        
        print("✅ Weaviate连接成功")
        
        # 测试BM25搜索
        print("\n🔍 测试BM25搜索 'meteorite'...")
        response = collection.query.bm25(
            query='meteorite',
            limit=5,
            return_properties=[
                "content", "metadata", "document_id", "page_number",
                "document_title", "chunk_index", "chunk_length"
            ]
        )
        
        print(f"📊 BM25搜索结果数量: {len(response.objects)}")
        
        if response.objects:
            print("\n📋 前3个结果:")
            for i, obj in enumerate(response.objects[:3], 1):
                title = obj.properties.get("document_title", "N/A")
                content = obj.properties.get("content", "")
                print(f"  {i}. 标题: {title[:60]}...")
                print(f"     内容长度: {len(content)}")
                print(f"     内容预览: {content[:100]}...")
        else:
            print("❌ BM25搜索没有返回结果")
            return False
        
        # 测试快速检查函数
        print("\n🧪 测试快速检查函数...")
        from pdf_processor.rag_meteorite_extractor import RAGMeteoriteExtractor
        extractor = RAGMeteoriteExtractor()
        
        test_contents = [
            "The Winchcombe meteorite, a unique and pristine witness from the outer solar system",
            "Molecular distribution and 13C isotope composition of volatile organic compounds in the Murchison and Sutters Mill carbonaceous chondrites",
            "This is a regular document about protein folding"
        ]
        
        for i, content in enumerate(test_contents, 1):
            result = extractor._quick_meteorite_check(content)
            print(f"  {i}. {content[:50]}... -> {result}")
        
        print("\n✅ BM25搜索功能正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bm25_search()
    
    if success:
        print("\n🎉 BM25搜索功能正常，问题可能在其他地方")
    else:
        print("\n⚠️ BM25搜索功能有问题")
    
    sys.exit(0 if success else 1)
