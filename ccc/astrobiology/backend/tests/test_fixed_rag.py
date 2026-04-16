#!/usr/bin/env python
"""
测试修复后的RAG系统
"""
import os
import sys
import django

# 设置环境变量
os.environ['EMBEDDING_MODEL'] = 'sentence-transformers/all-mpnet-base-v2'
os.environ['RERANKER_MODEL'] = 'cross-encoder/ms-marco-MiniLM-L-6-v2'

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from pdf_processor.unified_rag_service import UnifiedRAGService

def test_fixed_rag_system():
    """测试修复后的RAG系统"""
    print("=" * 80)
    print("测试修复后的RAG系统")
    print("=" * 80)
    
    try:
        # 初始化RAG服务
        rag_service = UnifiedRAGService()
        if not rag_service.initialize():
            print("[ERROR] RAG服务初始化失败")
            return
        
        print("[OK] RAG服务初始化成功")
        
        # 检查嵌入模型维度
        if rag_service.embedding_service and rag_service.embedding_service._model:
            test_embedding = rag_service.embedding_service.encode(["测试文本"])[0]
            print(f"[OK] 嵌入模型维度: {len(test_embedding)} (应该是768)")
        
        # 检查重排序模型
        if hasattr(rag_service, 'reranker_service') and rag_service.reranker_service:
            if rag_service.reranker_service.model:
                print("[OK] 重排序模型已初始化")
            else:
                print("[WARNING] 重排序模型未初始化，但不影响基本功能")
        
        # 测试搜索功能
        print("\n测试搜索功能:")
        print("-" * 40)
        
        test_queries = [
            "火星陨石中有机质和矿物的关系",
            "Shergottite meteorite organic compounds",
            "martian meteorite organics mineral association"
        ]
        
        for query in test_queries:
            print(f"\n搜索: {query}")
            try:
                results = rag_service.search(query, limit=3)
                print(f"[OK] 找到 {len(results)} 个结果")
                
                for i, result in enumerate(results[:2], 1):
                    print(f"  结果 {i}: {result.title[:60]}... (分数: {result.score:.3f})")
                    
            except Exception as e:
                print(f"[ERROR] 搜索失败: {e}")
        
        # 测试问答功能
        print(f"\n测试问答功能:")
        print("-" * 40)
        
        test_questions = [
            "火星陨石中有机质和矿物的关系是什么？",
            "What are the organic compounds found in martian meteorites?"
        ]
        
        for question in test_questions:
            print(f"\n问题: {question}")
            try:
                answer = rag_service.ask_question(question)
                if hasattr(answer, 'answer'):
                    print(f"[OK] 回答成功")
                    print(f"置信度: {answer.confidence:.2%}")
                    print(f"答案预览: {answer.answer[:200]}...")
                else:
                    print(f"[ERROR] 回答格式错误")
                    
            except Exception as e:
                print(f"[ERROR] 问答失败: {e}")
        
        print("\n" + "=" * 80)
        print("测试完成！")
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fixed_rag_system()
