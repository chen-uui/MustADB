#!/usr/bin/env python
"""
测试RAG系统回答火星陨石中有机质和矿物关系的问题
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from pdf_processor.unified_rag_service import UnifiedRAGService
import json

def test_martian_meteorite_organics():
    """测试火星陨石中有机质和矿物关系的问题"""
    print("=" * 80)
    print("测试RAG系统回答火星陨石中有机质和矿物关系的问题")
    print("=" * 80)
    
    try:
        # 初始化RAG服务
        rag_service = UnifiedRAGService()
        if not rag_service.initialize():
            print("[ERROR] RAG服务初始化失败")
            return
        
        print("\n[OK] RAG服务初始化成功")
        
        # 测试问题列表
        questions = [
            "哪种类型的火星陨石中分别发现了什么有机质？",
            "火星陨石中有机质和矿物之间的关系是什么？",
            "organics-mineral association in martian meteorites",
            "What organic compounds are found in different types of martian meteorites?",
            "火星陨石中发现的有机质与矿物的关联关系"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n[问题 {i}]: {question}")
            print("-" * 60)
            
            try:
                # 使用RAG系统回答问题
                answer_result = rag_service.ask_question(question)
                
                # RAGAnswer对象转换为字典
                if hasattr(answer_result, 'answer'):
                    answer_text = answer_result.answer
                    confidence = answer_result.confidence
                    sources = answer_result.sources
                    total_contexts = answer_result.total_contexts
                    
                    print(f"[OK] 回答成功")
                    print(f"置信度: {confidence:.2%}")
                    print(f"上下文数量: {total_contexts}")
                    print(f"\n答案:")
                    print(answer_text[:800] + "..." if len(answer_text) > 800 else answer_text)
                    
                    if sources:
                        print(f"\n来源 ({len(sources)} 个):")
                        for j, source in enumerate(sources[:3], 1):
                            title = source.get('title', '未知') if isinstance(source, dict) else getattr(source, 'title', '未知')
                            print(f"  {j}. {title[:80]}...")
                    
                else:
                    print(f"[ERROR] 回答失败: 返回格式错误")
                    
            except Exception as e:
                print(f"[ERROR] 测试失败: {e}")
        
        # 测试搜索功能
        print(f"\n🔍 测试搜索功能:")
        print("-" * 60)
        
        search_queries = [
            "martian meteorite organic compounds",
            "火星陨石 有机质 矿物",
            "organics-mineral association martian"
        ]
        
        for query in search_queries:
            print(f"\n搜索: {query}")
            try:
                results = rag_service.search(query, limit=5)
                print(f"[OK] 找到 {len(results)} 个结果")
                
                for j, result in enumerate(results[:2], 1):
                    print(f"\n结果 {j}:")
                    print(f"  文档: {result.title[:60]}...")
                    print(f"  分数: {result.score:.3f}")
                    print(f"  内容预览: {result.content[:150]}...")
                    
            except Exception as e:
                print(f"[ERROR] 搜索失败: {e}")
        
        print("\n" + "=" * 80)
        print("测试完成！")
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_martian_meteorite_organics()
