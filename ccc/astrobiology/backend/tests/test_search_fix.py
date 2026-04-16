#!/usr/bin/env python3
"""
测试搜索功能修复
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

def test_search_fix():
    """测试搜索功能修复"""
    print("🔍 测试搜索功能修复")
    print("=" * 50)
    
    try:
        from pdf_processor.rag_meteorite_extractor import RAGMeteoriteExtractor
        
        extractor = RAGMeteoriteExtractor()
        if not extractor.initialize_services():
            print("❌ RAG服务初始化失败")
            return False
        
        print("✅ RAG服务初始化成功")
        
        # 测试搜索陨石片段
        print("\n🔍 搜索陨石片段...")
        segments = extractor._search_meteorite_segments_optimized('meteorite', limit=5)
        
        print(f"📊 找到 {len(segments)} 个陨石相关片段")
        
        if segments:
            print("\n📋 前3个片段:")
            for i, seg in enumerate(segments[:3], 1):
                print(f"  {i}. {seg['title'][:60]}...")
                print(f"     内容长度: {len(seg['content'])}")
                print(f"     分数: {seg['score']}")
        else:
            print("❌ 没有找到陨石相关片段")
            return False
        
        print("\n✅ 搜索功能修复成功！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_search_fix()
    
    if success:
        print("\n🎉 搜索功能已修复，现在可以正常进行数据提取了！")
    else:
        print("\n⚠️ 搜索功能仍有问题，需要进一步调试")
    
    sys.exit(0 if success else 1)
