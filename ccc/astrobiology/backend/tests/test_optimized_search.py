#!/usr/bin/env python
"""
测试优化后的搜索性能
验证大分块 + 无聚合的搜索效果
"""
import os
import sys
import time
import json

# 设置路径
sys.path.insert(0, '.')

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')

import django
django.setup()

from pdf_processor.unified_rag_service import unified_rag_service

def test_search_performance():
    """测试搜索性能"""
    print("🚀 测试优化后的搜索性能...")
    
    # 测试查询
    test_queries = [
        "火星陨石中的有机化合物",
        "Gale Crater的挥发物分析",
        "火星表面水的证据",
        "陨石中的矿物组成",
        "火星大气层的化学成分"
    ]
    
    # 初始化服务
    print("\n1. 初始化RAG服务...")
    if not unified_rag_service.initialize():
        print("❌ 统一RAG服务初始化失败")
        return False
    
    print("✅ 服务初始化成功")
    
    # 测试传统模式（无聚合）
    print("\n2. 测试传统模式（大分块 + 无聚合）...")
    for i, query in enumerate(test_queries, 1):
        print(f"\n查询 {i}: {query}")
        
        start_time = time.time()
        try:
            results = unified_rag_service.search(
                query=query,
                limit=5,
                use_hybrid=True,
                use_rerank=True,
                use_aggregation=False  # 关闭聚合
            )
            end_time = time.time()
            
            print(f"  结果数量: {len(results)}")
            print(f"  搜索时间: {end_time - start_time:.2f}秒")
            
            if results:
                print(f"  最高分: {results[0].score:.4f}")
                print(f"  内容长度: {len(results[0].content)}字符")
                print(f"  文档标题: {results[0].title[:50]}...")
            
        except Exception as e:
            print(f"  ❌ 搜索失败: {e}")
    
    return True

if __name__ == "__main__":
    test_search_performance()
