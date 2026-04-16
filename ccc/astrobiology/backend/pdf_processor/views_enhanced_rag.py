"""
增强RAG问答API视图
"""

import logging
import json
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .enhanced_rag_service import EnhancedRAGService

logger = logging.getLogger(__name__)

# 全局服务实例
enhanced_rag_service = None

def get_enhanced_rag_service():
    """获取增强RAG服务实例"""
    global enhanced_rag_service
    if enhanced_rag_service is None:
        enhanced_rag_service = EnhancedRAGService()
        if not enhanced_rag_service.initialize():
            logger.error("Failed to initialize EnhancedRAGService")
            return None
    return enhanced_rag_service


@api_view(['POST'])
@permission_classes([AllowAny])  # 临时改为AllowAny用于测试
def enhanced_ask_question(request):
    """增强的智能问答"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return Response({
                'success': False,
                'error': '问题不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取服务实例
        service = get_enhanced_rag_service()
        if not service:
            return Response({
                'success': False,
                'error': 'RAG服务初始化失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 获取选项
        options = data.get('options', {})
        
        # 执行问答
        result = service.ask_question(question, options)
        
        return Response({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"Enhanced ask question failed: {str(e)}")
        return Response({
            'success': False,
            'error': f'问答失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 临时改为AllowAny用于测试
def batch_enhanced_ask_questions(request):
    """批量增强问答"""
    try:
        data = json.loads(request.body)
        questions = data.get('questions', [])
        
        if not questions or not isinstance(questions, list):
            return Response({
                'success': False,
                'error': '问题列表不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(questions) > 10:  # 限制批量问题数量
            return Response({
                'success': False,
                'error': '批量问题数量不能超过10个'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取服务实例
        service = get_enhanced_rag_service()
        if not service:
            return Response({
                'success': False,
                'error': 'RAG服务初始化失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 获取选项
        options = data.get('options', {})
        
        # 执行批量问答
        results = service.batch_ask_questions(questions, options)
        
        return Response({
            'success': True,
            'data': {
                'results': results,
                'total_questions': len(questions),
                'successful_answers': len([r for r in results if r.get('confidence', 0) > 0])
            }
        })
        
    except Exception as e:
        logger.error(f"Batch enhanced ask questions failed: {str(e)}")
        return Response({
            'success': False,
            'error': f'批量问答失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 临时改为AllowAny用于测试
def analyze_question(request):
    """分析问题类型和意图"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return Response({
                'success': False,
                'error': '问题不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取服务实例
        service = get_enhanced_rag_service()
        if not service:
            return Response({
                'success': False,
                'error': 'RAG服务初始化失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 分析问题
        analysis = service.get_question_analysis(question)
        
        return Response({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        logger.error(f"Question analysis failed: {str(e)}")
        return Response({
            'success': False,
            'error': f'问题分析失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])  # 临时改为AllowAny用于测试
def get_enhanced_rag_statistics(request):
    """获取增强RAG服务统计信息"""
    try:
        # 获取服务实例
        service = get_enhanced_rag_service()
        if not service:
            return Response({
                'success': False,
                'error': 'RAG服务初始化失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 获取统计信息
        statistics = service.get_service_statistics()
        
        return Response({
            'success': True,
            'data': statistics
        })
        
    except Exception as e:
        logger.error(f"Get enhanced RAG statistics failed: {str(e)}")
        return Response({
            'success': False,
            'error': f'获取统计信息失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 临时改为AllowAny用于测试
def test_question_classification(request):
    """测试问题分类功能"""
    try:
        data = json.loads(request.body)
        test_questions = data.get('test_questions', [])
        
        if not test_questions or not isinstance(test_questions, list):
            # 使用默认测试问题
            test_questions = [
                "不同陨石类型分别发现了什么？",
                "Murchison陨石中检测到了哪些有机化合物？",
                "矿物与有机质是如何关联的？",
                "这些发现有什么科学意义？",
                "数据库中有多少陨石记录？",
                "什么是天体生物学？"
            ]
        
        # 获取服务实例
        service = get_enhanced_rag_service()
        if not service:
            return Response({
                'success': False,
                'error': 'RAG服务初始化失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 执行分类测试
        test_results = service.test_classification(test_questions)
        
        return Response({
            'success': True,
            'data': test_results
        })
        
    except Exception as e:
        logger.error(f"Test question classification failed: {str(e)}")
        return Response({
            'success': False,
            'error': f'分类测试失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])  # 临时改为AllowAny用于测试
def compare_rag_methods(request):
    """比较不同RAG方法的答案质量"""
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        
        if not question:
            return Response({
                'success': False,
                'error': '问题不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取服务实例
        service = get_enhanced_rag_service()
        if not service:
            return Response({
                'success': False,
                'error': 'RAG服务初始化失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 获取增强答案
        enhanced_result = service.ask_question(question)
        
        # 获取传统RAG答案
        rag_result = service._get_rag_answer(question)
        
        # 比较结果
        comparison = {
            'question': question,
            'enhanced_answer': {
                'answer': enhanced_result.get('answer', ''),
                'answer_type': enhanced_result.get('answer_type', ''),
                'confidence': enhanced_result.get('confidence', 0.0),
                'method_used': enhanced_result.get('method_used', ''),
                'data_source': enhanced_result.get('data_source', '')
            },
            'traditional_rag_answer': {
                'answer': rag_result.get('answer', ''),
                'answer_type': rag_result.get('answer_type', ''),
                'confidence': rag_result.get('confidence', 0.0),
                'data_source': rag_result.get('data_source', '')
            },
            'comparison': {
                'enhanced_confidence': enhanced_result.get('confidence', 0.0),
                'traditional_confidence': rag_result.get('confidence', 0.0),
                'confidence_improvement': enhanced_result.get('confidence', 0.0) - rag_result.get('confidence', 0.0),
                'method_used': enhanced_result.get('method_used', 'unknown')
            },
            'timestamp': enhanced_result.get('timestamp', '')
        }
        
        return Response({
            'success': True,
            'data': comparison
        })
        
    except Exception as e:
        logger.error(f"Compare RAG methods failed: {str(e)}")
        return Response({
            'success': False,
            'error': f'方法比较失败: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)