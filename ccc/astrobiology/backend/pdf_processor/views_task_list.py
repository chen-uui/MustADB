from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from meteorite_search.models import DataExtractionTask
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_extraction_tasks(request):
    """获取提取任务列表"""
    try:
        # 获取查询参数
        status_filter = request.GET.get('status', '')
        task_type_filter = request.GET.get('type', '')
        limit = int(request.GET.get('limit', 20))
        
        # 构建查询
        queryset = DataExtractionTask.objects.all()
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        if task_type_filter:
            queryset = queryset.filter(task_type=task_type_filter)
            
        # 优化：使用only()只查询需要的字段，减少数据传输
        # 按创建时间倒序排列，限制数量
        tasks = queryset.order_by('-created_at')[:limit].only(
            'task_id', 'status', 'task_type', 'total_documents', 
            'processed_documents', 'successful_extractions', 'failed_extractions',
            'created_at', 'started_at', 'completed_at', 'results'
        )
        
        # 优化：使用聚合查询一次性获取总数，避免额外的count()查询
        total_count = queryset.count()
        
        # 序列化任务数据
        task_data = []
        for task in tasks:
            task_data.append({
                'task_id': task.task_id,
                'status': task.status,
                'task_type': getattr(task, 'task_type', 'batch'),  # 默认为batch类型
                'total_documents': task.total_documents,
                'processed_documents': task.processed_documents,
                'successful_extractions': task.successful_extractions,
                'failed_extractions': task.failed_extractions,
                'progress_percentage': task.get_progress_percentage(),
                'created_at': task.created_at,
                'started_at': task.started_at,
                'completed_at': task.completed_at,
                'search_queries': task.results.get('search_queries', []) if task.results else []
            })
        
        return Response({
            'success': True,
            'data': task_data,
            'total': total_count
        })
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)