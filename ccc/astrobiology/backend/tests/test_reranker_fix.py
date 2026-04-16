#!/usr/bin/env python
"""
测试重排序服务修复
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

from pdf_processor.reranker_service import reranker_service

def test_reranker_service():
    """测试重排序服务"""
    print("=" * 80)
    print("测试重排序服务")
    print("=" * 80)
    
    try:
        # 检查重排序服务
        if reranker_service.model:
            print("✅ 重排序模型已成功初始化")
            print(f"模型类型: {type(reranker_service.model)}")
            
            # 测试重排序功能
            print("\n测试重排序功能...")
            
            # 创建测试数据
            from pdf_processor.hybrid_search_service import HybridSearchResult
            
            test_results = [
                HybridSearchResult(
                    content="这是关于火星陨石的研究",
                    score=0.8,
                    vector_score=0.8,
                    bm25_score=0.0,
                    metadata={"title": "火星陨石研究"},
                    document_id="doc1",
                    page=1,
                    title="火星陨石研究",
                    chunk_index=0
                ),
                HybridSearchResult(
                    content="这是关于地球地质的研究",
                    score=0.6,
                    vector_score=0.6,
                    bm25_score=0.0,
                    metadata={"title": "地球地质研究"},
                    document_id="doc2",
                    page=1,
                    title="地球地质研究",
                    chunk_index=0
                )
            ]
            
            query = "火星陨石中有机质和矿物的关系"
            
            try:
                reranked = reranker_service.rerank_results(query, test_results, top_k=2)
                print(f"✅ 重排序成功，返回 {len(reranked)} 个结果")
                
                for i, result in enumerate(reranked, 1):
                    print(f"  结果 {i}: 分数={result.final_score:.3f}, 内容={result.content[:50]}...")
                    
            except Exception as e:
                print(f"❌ 重排序测试失败: {e}")
                
        else:
            print("❌ 重排序模型未初始化")
            print(f"错误信息: {getattr(reranker_service, 'error', '未知错误')}")
        
        print("\n" + "=" * 80)
        print("重排序服务测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_reranker_service()
