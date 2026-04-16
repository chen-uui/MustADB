#!/usr/bin/env python
"""
测试改进的搜索策略
"""
import os
import sys
import django

# 设置Django环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from pdf_processor.unified_rag_service import UnifiedRAGService
from pdf_processor.weaviate_connection import weaviate_connection
from pdf_processor.embedding_service import embedding_service
import weaviate

def test_improved_search():
    """测试改进的搜索策略"""
    print("=" * 80)
    print("改进搜索策略测试")
    print("=" * 80)
    
    try:
        # 初始化服务
        rag_service = UnifiedRAGService()
        if not rag_service.initialize():
            print("❌ RAG服务初始化失败")
            return
        
        # 测试查询
        test_queries = [
            "Allende meteorite",
            "Murchison meteorite", 
            "Tissint meteorite",
            "Zagami meteorite",
            "ALH 84001 meteorite"
        ]
        
        for query in test_queries:
            print(f"\n🔍 测试查询: '{query}'")
            print("-" * 60)
            
            # 方法1：增加搜索数量
            print("方法1：增加搜索数量 (limit=50)")
            results_50 = rag_service.search(query, limit=50)
            print(f"找到 {len(results_50)} 个结果")
            
            # 检查是否包含陨石名称
            meteorite_name = query.split()[0]  # 提取陨石名称
            found_meteorite = False
            for result in results_50[:10]:  # 只检查前10个结果
                if meteorite_name.lower() in result.content.lower():
                    found_meteorite = True
                    print(f"✅ 在文档 '{result.title}' 中找到陨石名称")
                    print(f"   内容片段: {result.content[:200]}...")
                    break
            
            if not found_meteorite:
                print(f"❌ 在前10个结果中未找到陨石名称 '{meteorite_name}'")
                print("前5个结果的内容片段:")
                for i, result in enumerate(results_50[:5], 1):
                    print(f"  {i}. {result.title}: {result.content[:100]}...")
            
            # 方法2：文档级聚合
            print(f"\n方法2：文档级聚合分析")
            doc_groups = {}
            for result in results_50:
                doc_id = result.document_id
                if doc_id not in doc_groups:
                    doc_groups[doc_id] = {
                        'title': result.title,
                        'chunks': [],
                        'total_score': 0
                    }
                doc_groups[doc_id]['chunks'].append(result)
                doc_groups[doc_id]['total_score'] += result.score
            
            # 按总分排序
            sorted_docs = sorted(doc_groups.items(), key=lambda x: x[1]['total_score'], reverse=True)
            
            print(f"找到 {len(sorted_docs)} 个相关文档:")
            for i, (doc_id, doc_data) in enumerate(sorted_docs[:5], 1):
                print(f"  {i}. {doc_data['title']} (总分: {doc_data['total_score']:.3f}, 片段数: {len(doc_data['chunks'])})")
                
                # 检查这个文档是否包含陨石名称
                doc_content = ' '.join([chunk.content for chunk in doc_data['chunks']])
                if meteorite_name.lower() in doc_content.lower():
                    print(f"     ✅ 包含陨石名称 '{meteorite_name}'")
                else:
                    print(f"     ❌ 不包含陨石名称 '{meteorite_name}'")
        
        # 方法3：混合搜索测试
        print(f"\n🔍 混合搜索测试")
        print("-" * 60)
        
        client = weaviate_connection.get_client()
        collection = client.collections.get("PDFDocument")
        
        # 测试关键词搜索
        keyword_query = "Allende"
        print(f"关键词搜索: '{keyword_query}'")
        
        try:
            # 使用BM25关键词搜索
            response = collection.query.bm25(
                query=keyword_query,
                limit=10,
                return_metadata=weaviate.classes.query.MetadataQuery(score=True)
            )
            
            print(f"BM25搜索找到 {len(response.objects)} 个结果:")
            for i, obj in enumerate(response.objects[:5], 1):
                content = obj.properties.get('content', '')
                title = obj.properties.get('title', '未知')
                score = obj.metadata.score if obj.metadata else 0.0
                
                print(f"  {i}. {title} (BM25分数: {score:.3f})")
                if keyword_query.lower() in content.lower():
                    print(f"     ✅ 包含关键词")
                    print(f"     内容: {content[:150]}...")
                else:
                    print(f"     ❌ 不包含关键词")
                    
        except Exception as e:
            print(f"❌ BM25搜索失败: {e}")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_improved_search()
