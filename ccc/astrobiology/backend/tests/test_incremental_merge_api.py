"""
测试增量合并API的简单脚本
"""
import requests
import json

def test_incremental_merge_api():
    """测试增量合并API"""
    
    # API端点
    url = "http://localhost:8000/api/pdf/extraction/start-from-db/"
    
    # 测试数据
    test_data = {
        "searchConfig": {
            "searchQuery": "meteorite",
            "maxDocuments": 3,
            "relevanceThreshold": 0.6
        },
        "extractionOptions": {
            "extractBasicInfo": True,
            "extractLocation": True,
            "extractClassification": True,
            "extractOrganicCompounds": True,
            "extractContamination": False,
            "extractReferences": False
        },
        "preview_mode": True  # 预览模式
    }
    
    try:
        print("🚀 测试增量合并API...")
        print(f"📡 请求URL: {url}")
        print(f"📊 测试数据: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
        
        # 发送请求
        response = requests.post(
            url,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=60  # 60秒超时
        )
        
        print(f"\n📈 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功!")
            print(f"📋 响应数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查关键字段
            if result.get('success'):
                data = result.get('data', {})
                print(f"\n🎯 关键指标:")
                print(f"  任务ID: {data.get('task_id')}")
                print(f"  状态: {data.get('status')}")
                print(f"  总文档数: {data.get('total_documents')}")
                print(f"  成功提取: {data.get('successful_extractions')}")
                print(f"  失败提取: {data.get('failed_extractions')}")
                
                merge_stats = data.get('merge_stats', {})
                if merge_stats:
                    print(f"  合并率: {merge_stats.get('merge_rate', 0):.1f}%")
                    print(f"  唯一陨石数: {merge_stats.get('total_unique_meteorites', 0)}")
                    print(f"  平均置信度: {merge_stats.get('avg_confidence', 0):.3f}")
                
                print(f"  消息: {data.get('message')}")
            else:
                print(f"❌ API返回失败: {result.get('error')}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"错误详情: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ 请求超时 - 这可能是正常的，因为处理需要时间")
    except requests.exceptions.ConnectionError:
        print("🔌 连接错误 - 请确保Django服务器正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_incremental_merge_api()
