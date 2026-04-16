"""
PDF问答和数据提取API视图
包含RAG问答系统和数据提取功能
"""

import logging
import re
import json
import time
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from .rag_service import RAGService
from meteorite_search.models import DataExtractionTask

logger = logging.getLogger(__name__)

# ==================== RAG问答服务 ====================

from .rag_service import get_qa_service

class PDFQAViewSet(viewsets.ViewSet):
    """PDF问答API视图集"""
    permission_classes = [AllowAny]
    
    def _stream_response(self, question: str, use_multi_pass: bool = False):
        """流式输出答案"""
        
        def generate_stream():
            try:
                # 获取问答服务
                qa_service = get_qa_service()
                
                # 发送开始信号
                yield f"data: {json.dumps({'type': 'start', 'message': '开始处理...'})}\n\n"
                
                # 1. 向量搜索阶段
                yield f"data: {json.dumps({'type': 'search', 'message': '正在搜索相关文档...'})}\n\n"
                
                # 获取搜索结果
                search_results = qa_service.vector_search(question, limit=None)
                
                if not search_results:
                    yield f"data: {json.dumps({'type': 'error', 'message': '未找到相关文档'})}\n\n"
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    return
                
                yield f"data: {json.dumps({'type': 'search_complete', 'count': len(search_results)})}\n\n"
                
                # 2. 重排序阶段
                yield f"data: {json.dumps({'type': 'rerank', 'message': '正在优化搜索结果...'})}\n\n"
                reranked_results = qa_service.rerank_contexts(question, search_results, top_k=None)
                
                # 3. 计算置信度
                confidence_result = qa_service.calculate_confidence(reranked_results, question)
                confidence = confidence_result['confidence']
                yield f"data: {json.dumps({'type': 'confidence', 'confidence': confidence, 'factors': confidence_result['factors']})}\n\n"
                
                # 4. 生成答案（流式）
                yield f"data: {json.dumps({'type': 'generating', 'message': '正在生成答案...'})}\n\n"
                
                # 生成答案并流式输出
                full_answer = qa_service.generate_answer(question, reranked_results)
                
                # 智能分割：按句子、短语和单词混合分割
                logger.info(f"views_qa_extraction - full_answer类型: {type(full_answer)}")
                logger.info(f"views_qa_extraction - full_answer内容: {repr(full_answer)}")
                sentences = re.split(r'(?<=[.!?。！？])\s*', str(full_answer))
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if sentence:
                        # 按单词分割
                        words = sentence.split(' ')
                        for i, word in enumerate(words):
                            word = word.strip()
                            if word:
                                # 添加空格，除了最后一个单词
                                content = word + (' ' if i < len(words) - 1 else '')
                                yield f"data: {json.dumps({'type': 'answer_chunk', 'content': content})}\n\n"
                                time.sleep(0.05)  # 更快的输出速度
                        
                        # 句子结束后的停顿
                        if sentence and sentence[-1] in '.!?。！？':
                            yield f"data: {json.dumps({'type': 'answer_chunk', 'content': ' '})}\n\n"
                            time.sleep(0.2)  # 句子间停顿
                
                # 5. 发送最终结果
                result = {
                    'type': 'complete',
                    'answer': full_answer,
                    'confidence': confidence,
                    'sources': [
                        {
                            "content": source.content,
                            "title": source.title,
                            "page": source.page,
                            "score": source.score,
                            "document_id": source.document_id
                        }
                        for source in reranked_results
                    ],
                    'total_contexts': len(reranked_results),
                    'strategy': 'multi-pass' if use_multi_pass else 'standard'
                }
                
                yield f"data: {json.dumps(result)}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                logger.error(f"流式响应失败: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
        response = StreamingHttpResponse(
            generate_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    def __del__(self):
        """确保RAG服务正确关闭"""
        try:
            qa_service = get_qa_service()
            if hasattr(qa_service, 'close'):
                qa_service.close()
        except Exception as e:
            logger.warning(f"关闭RAG服务时出错: {e}")
    
    @action(detail=False, methods=['post'])
    def ask(self, request):
        """处理用户提问，支持优化策略"""
        try:
            question = request.data.get('question', '').strip()
            use_multi_pass = request.data.get('use_multi_pass')  # 可选参数
            stream = request.data.get('stream', False)  # 新增流式输出参数
            
            if not question:
                return Response({
                    'success': False,
                    'error': '问题不能为空'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取问答服务
            qa_service = get_qa_service()
            
            # 确保服务已初始化
            if not qa_service.is_initialized:
                qa_service.initialize()
            
            # 如果启用流式输出
            if stream:
                return self._stream_response(question, use_multi_pass)
            
            # 使用优化后的RAG服务
            rag_answer = qa_service.ask_question(question, use_multi_pass=use_multi_pass)
            
            # 转换结果为API格式
            result = {
                "answer": rag_answer.answer,
                "confidence": rag_answer.confidence,
                "sources": rag_answer.sources,
                "total_contexts": rag_answer.total_contexts
            }
            
            return Response({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            logger.error(f"问答处理失败: {str(e)}")
            return Response({
                'success': False,
                'error': f'处理问题时出现错误: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def ask_optimized(self, request):
        """使用优化策略处理复杂问题"""
        try:
            question = request.data.get('question', '').strip()
            stream = request.data.get('stream', False)  # 新增流式输出参数
            
            if not question:
                return Response({
                    'success': False,
                    'error': '问题不能为空'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取问答服务
            qa_service = get_qa_service()
            
            # 确保服务已初始化
            if not qa_service.is_initialized:
                qa_service.initialize()
            
            # 如果启用流式输出
            if stream:
                return self._stream_response(question, use_multi_pass=True)
            
            # 使用多轮优化策略
            rag_answer = qa_service.ask_question(question, use_multi_pass=True)
            
            # 转换结果为API格式
            result = {
                "answer": rag_answer.answer,
                "confidence": rag_answer.confidence,
                "sources": rag_answer.sources,
                "total_contexts": rag_answer.total_contexts,
                "strategy": "multi-pass"
            }
            
            return Response({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            logger.error(f"优化问答处理失败: {str(e)}")
            return Response({
                'success': False,
                'error': f'处理问题时出现错误: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def status(self, request):
        """获取问答服务状态"""
        try:
            qa_service = get_qa_service()
            
            status_info = {
                'initialized': qa_service.is_initialized,
                'service_type': 'RAG',
                'components': {}
            }
            
            # 检查各组件状态
            if hasattr(qa_service, 'weaviate_client'):
                status_info['components']['weaviate'] = 'connected' if qa_service.weaviate_client else 'disconnected'
            
            if hasattr(qa_service, 'llm_client'):
                status_info['components']['llm'] = 'connected' if qa_service.llm_client else 'disconnected'
            
            return Response({
                'success': True,
                'data': status_info
            })
            
        except Exception as e:
            logger.error(f"获取服务状态失败: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==================== 独立问答API ====================

@csrf_exempt
@require_http_methods(["POST"])
def ask_question_api(request):
    """直接问答API端点"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return JsonResponse({
                'success': False,
                'error': '问题不能为空'
            }, status=400)
        
        # 获取问答服务
        qa_service = get_qa_service()
        
        # 确保服务已初始化
        if not qa_service.is_initialized:
            qa_service.initialize()
        
        # 处理问题
        rag_answer = qa_service.ask_question(question)
        
        # 转换结果为API格式
        result = {
            "answer": rag_answer.answer,
            "confidence": rag_answer.confidence,
            "sources": rag_answer.sources,
            "total_contexts": rag_answer.total_contexts
        }
        
        return JsonResponse({
            'success': True,
            'data': result
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"直接问答API失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'处理问题时出现错误: {str(e)}'
        }, status=500)

def qa_demo(request):
    """问答演示页面"""
    return TemplateView.as_view(template_name='qa_demo.html')(request)

# ==================== 数据提取相关视图 ====================

# preview_search function moved to views_extraction.py to avoid duplication

# reset_batch_extraction_state function moved to views_extraction.py to avoid duplication

# ==================== 其他提取相关API ====================
# 注意：这里只包含简单的提取相关视图，复杂的提取逻辑应该在专门的提取模块中实现

# get_extraction_progress function moved to views_extraction.py to avoid duplication