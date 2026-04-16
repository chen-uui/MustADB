"""
RAG系统健康检查API
提供详细的系统状态监控和诊断功能
"""

import os
import logging
import time
import requests

from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .rag_service import get_qa_service
from .models import PDFDocument
from .pdf_utils import GlobalConfig

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    综合健康检查端点
    返回系统各组件的详细状态信息
    """
    try:
        health_status = {
            "timestamp": int(time.time()),
            "overall_status": "healthy",
            "components": {},
            "metrics": {},
            "errors": []
        }
        
        # 检查RAG服务
        try:
            qa_service = get_qa_service()
            rag_status = qa_service.get_status()
            
            health_status["components"]["rag_service"] = {
                "status": "healthy" if rag_status.get("is_initialized", False) else "unhealthy",
                "initialized": rag_status.get("is_initialized", False),
                "document_count": rag_status.get("document_count", 0),
                "model": rag_status.get("model", "unknown")
            }
            
            if not rag_status.get("is_initialized", False):
                health_status["errors"].append("RAG服务未初始化")
                
        except Exception as e:
            health_status["components"]["rag_service"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["errors"].append(f"RAG服务检查失败: {str(e)}")
        
        # 检查Weaviate连接
        try:
            weaviate_url = getattr(GlobalConfig, 'WEAVIATE_URL', f"http://{os.getenv('WEAVIATE_HOST', 'localhost')}:{os.getenv('WEAVIATE_PORT', '8080')}")
            response = requests.get(f"{weaviate_url}/v1/.well-known/ready", timeout=5)
            
            if response.status_code == 200:
                health_status["components"]["weaviate"] = {
                    "status": "healthy",
                    "url": weaviate_url,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                }
            else:
                health_status["components"]["weaviate"] = {
                    "status": "unhealthy",
                    "url": weaviate_url,
                    "status_code": response.status_code
                }
                health_status["errors"].append(f"Weaviate返回状态码: {response.status_code}")
                
        except Exception as e:
            health_status["components"]["weaviate"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["errors"].append(f"Weaviate连接失败: {str(e)}")
        
        # 检查LLM连接
        try:
            llm_url = getattr(GlobalConfig, 'LLM_BASE_URL', 'http://localhost:11434')
            response = None  # 初始化response变量
            
            # 直接使用Ollama API
            try:
                response = requests.get(f"{llm_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    llm_healthy = True
                    models = response.json().get('models', [])
                else:
                    llm_healthy = False
                    models = []
            except Exception as e:
                llm_healthy = False
                models = []
                logger.error(f"Ollama API调用失败: {e}")
            
            # 获取模型名称（优先使用llama模型）
            model_name = "未知"
            if llm_healthy and models:
                # 优先查找llama模型
                llama_models = [m for m in models if 'llama' in m.get('name', '').lower()]
                if llama_models:
                    model_name = llama_models[0].get('name', '未知')
                else:
                    # 如果没有llama模型，使用第一个可用模型
                    model_name = models[0].get('name', '未知')
            
            if llm_healthy and response is not None:
                health_status["components"]["llm"] = {
                    "status": "healthy",
                    "url": llm_url,
                    "model_name": model_name,
                    "models_count": len(models),
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                }
            else:
                health_status["components"]["llm"] = {
                    "status": "unhealthy" if llm_healthy else ("error" if not llm_healthy and models else "unknown"),
                    "url": llm_url,
                    "model_name": "连接失败"
                }
                health_status["errors"].append("LLM服务不可用")
                
        except Exception as e:
            health_status["components"]["llm"] = {
                "status": "error",
                "error": str(e),
                "model_name": f"错误: {str(e)}"
            }
            health_status["errors"].append(f"LLM连接失败: {str(e)}")
        
        # 检查数据库状态 - 优化：使用聚合查询一次性获取统计信息
        try:
            from django.db import connection
            from django.db.models import Count, Q
            
            # 直接使用原生SQL查询避免模型管理器问题
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_docs,
                        COUNT(CASE WHEN processed = true THEN 1 END) as processed_docs
                    FROM pdf_documents
                """)
                row = cursor.fetchone()
                total_docs = row[0] if row[0] is not None else 0
                processed_docs = row[1] if row[1] is not None else 0
                pending_docs = total_docs - processed_docs
            
            health_status["components"]["database"] = {
                "status": "healthy",
                "total_documents": total_docs,
                "processed_documents": processed_docs,
                "pending_documents": pending_docs
            }
            
            health_status["metrics"]["document_processing_rate"] = (
                processed_docs / total_docs * 100 if total_docs > 0 else 0
            )
            
        except Exception as e:
            logger.error(f"数据库检查失败: {str(e)}", exc_info=True)
            health_status["components"]["database"] = {
                "status": "error",
                "error": str(e)
            }
            health_status["errors"].append(f"数据库检查失败: {str(e)}")
        
        # 确定整体状态
        component_statuses = []
        for comp_name, comp in health_status["components"].items():
            comp_status = comp.get("status", "unknown")
            component_statuses.append(comp_status)
            logger.info(f"Component {comp_name} status: {comp_status}")
        
        logger.info(f"All component statuses: {component_statuses}")
        
        if "error" in component_statuses:
            health_status["overall_status"] = "error"
            logger.warning(f"Overall status set to error due to component statuses: {component_statuses}")
        elif "unhealthy" in component_statuses:
            health_status["overall_status"] = "degraded"
        else:
            health_status["overall_status"] = "healthy"
        
        # 根据整体状态确定HTTP状态码
        http_status = status.HTTP_200_OK
        if health_status["overall_status"] == "error":
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_status["overall_status"] == "degraded":
            http_status = status.HTTP_206_PARTIAL_CONTENT
        
        # 转换为前端期望的格式
        rag_init = health_status["components"].get("rag_service", {}).get("initialized", False)
        weav_ok = health_status["components"].get("weaviate", {}).get("status") == "healthy"
        llm_ok = health_status["components"].get("llm", {}).get("status") == "healthy"
        doc_total = health_status["components"].get("database", {}).get("total_documents", 0)
        smart_initialized = bool(rag_init or (weav_ok and llm_ok and doc_total > 0))
        frontend_data = {
            'document_count': health_status["components"].get("rag_service", {}).get("document_count", 0),
            'model_name': health_status["components"].get("llm", {}).get("model_name", "未知"),
            'weaviate_connected': health_status["components"].get("weaviate", {}).get("status") == "healthy",
            'llm_connected': health_status["components"].get("llm", {}).get("status") == "healthy",
            'initialized': smart_initialized,
            'error': None if smart_initialized else (health_status["errors"][0] if health_status["errors"] else None),
            'overall_status': health_status["overall_status"],
            'timestamp': health_status["timestamp"]
        }
        
        return JsonResponse({
            'success': True,
            'data': frontend_data
        }, status=http_status)
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'data': {
                'document_count': 0,
                'model_name': '错误',
                'weaviate_connected': False,
                'llm_connected': False,
                'initialized': False,
                'error': str(e),
                'overall_status': 'error'
            }
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

@csrf_exempt
@require_http_methods(["GET"])
def quick_health(request):
    """
    快速健康检查端点
    仅返回基本的服务可用性状态
    """
    try:
        # 快速检查核心服务
        qa_service = get_qa_service()
        is_healthy = qa_service.is_initialized
        
        if is_healthy:
            return JsonResponse({
                'status': 'healthy',
                'timestamp': int(time.time())
            })
        else:
            return JsonResponse({
                'status': 'unhealthy',
                'timestamp': int(time.time())
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except Exception as e:
        logger.error(f"快速健康检查失败: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'timestamp': int(time.time())
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

@csrf_exempt
@require_http_methods(["GET"])
def metrics(request):
    """
    系统指标端点
    返回性能和使用统计信息
    """
    try:
        qa_service = get_qa_service()
        
        # 获取基本指标
        metrics_data = {
            "timestamp": int(time.time()),
            "system": {
                "uptime_seconds": time.time() - getattr(qa_service, '_start_time', time.time()),
                "initialized": qa_service.is_initialized
            },
            "documents": {},
            "performance": {}
        }
        
        # 文档统计 - 优化：使用聚合查询一次性获取统计信息
        try:
            from django.db import connection
            from django.db.models import Count, Q
            
            # 使用原生SQL查询避免模型管理器问题
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_docs,
                        COUNT(CASE WHEN processed = true THEN 1 END) as processed_docs
                    FROM pdf_documents
                """)
                row = cursor.fetchone()
                total_docs = row[0] if row[0] is not None else 0
                processed_docs = row[1] if row[1] is not None else 0
            
            metrics_data["documents"] = {
                "total": total_docs,
                "processed": processed_docs,
                "pending": total_docs - processed_docs,
                "processing_rate": processed_docs / total_docs * 100 if total_docs > 0 else 0
            }
        except Exception as e:
            logger.warning(f"获取文档统计失败: {e}")
        
        # 向量数据库统计
        try:
            # 检查qa_service是否有weaviate_client属性
            if hasattr(qa_service, 'weaviate_client') and qa_service.weaviate_client:
                # 获取向量数据库统计信息
                client = qa_service.weaviate_client
                if client and hasattr(client, 'collections'):
                    # 获取PDFDocument集合的统计信息
                    collection = client.collections.get("PDFDocument")
                    if collection:
                        aggregate_response = collection.aggregate.over_all(total_count=True)
                        vector_stats = {
                            'document_count': aggregate_response.total_count or 0
                        }
                        metrics_data["vector_database"] = vector_stats
        except Exception as e:
            logger.warning(f"获取向量数据库统计失败: {e}")
        
        return JsonResponse({
            'success': True,
            'data': metrics_data
        })
        
    except Exception as e:
        logger.error(f"获取指标失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)