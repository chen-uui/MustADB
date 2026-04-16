"""
任务恢复相关的API视图
"""

import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

from .task_recovery_service import task_recovery_service
from .task_checkpoint_manager import checkpoint_manager
from meteorite_search.models import DataExtractionTask

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def system_startup_recovery(request):
    """
    系统启动时的任务恢复
    在系统重启后调用，自动恢复被中断的任务
    """
    try:
        recovery_results = task_recovery_service.check_and_recover_interrupted_tasks()
        
        return JsonResponse({
            'success': True,
            'message': '系统启动恢复完成',
            'data': recovery_results
        })
        
    except Exception as e:
        logger.error(f"系统启动恢复失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'系统启动恢复失败: {str(e)}'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def manual_recover_task(request, task_id):
    """
    手动恢复指定任务
    """
    try:
        recovery_result = task_recovery_service.manual_recover_task(task_id)
        
        if recovery_result['success']:
            return JsonResponse({
                'success': True,
                'message': f'任务 {task_id} 恢复成功',
                'data': recovery_result
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'任务 {task_id} 恢复失败: {recovery_result.get("error", "未知错误")}'
            }, status=400)
            
    except Exception as e:
        logger.error(f"手动恢复任务 {task_id} 失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'手动恢复任务失败: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recovery_status(request):
    """
    获取任务恢复服务状态
    """
    try:
        recovery_status = task_recovery_service.get_recovery_status()
        
        return JsonResponse({
            'success': True,
            'data': recovery_status
        })
        
    except Exception as e:
        logger.error(f"获取恢复状态失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取恢复状态失败: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_task_checkpoints(request, task_id):
    """
    列出任务的所有检查点
    """
    try:
        checkpoints = checkpoint_manager.list_checkpoints(task_id)
        
        return JsonResponse({
            'success': True,
            'data': {
                'task_id': task_id,
                'checkpoints': checkpoints
            }
        })
        
    except Exception as e:
        logger.error(f"列出任务 {task_id} 检查点失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'列出检查点失败: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_checkpoint_details(request, task_id, checkpoint_id):
    """
    获取特定检查点的详细信息
    """
    try:
        checkpoint_data = checkpoint_manager.load_checkpoint_by_id(task_id, checkpoint_id)
        
        if checkpoint_data:
            return JsonResponse({
                'success': True,
                'data': {
                    'task_id': task_id,
                    'checkpoint_id': checkpoint_id,
                    'checkpoint_data': checkpoint_data
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'检查点 {checkpoint_id} 不存在'
            }, status=404)
            
    except Exception as e:
        logger.error(f"获取检查点 {checkpoint_id} 详情失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取检查点详情失败: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_checkpoint_stats(request, task_id):
    """
    获取任务的检查点统计信息
    """
    try:
        stats = checkpoint_manager.get_checkpoint_stats(task_id)
        
        return JsonResponse({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"获取任务 {task_id} 检查点统计失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取检查点统计失败: {str(e)}'
        }, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_task_checkpoints(request, task_id):
    """
    清除任务的所有检查点
    """
    try:
        success = checkpoint_manager.clear_checkpoints(task_id)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': f'任务 {task_id} 的检查点已清除'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': f'清除任务 {task_id} 检查点失败'
            }, status=400)
            
    except Exception as e:
        logger.error(f"清除任务 {task_id} 检查点失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'清除检查点失败: {str(e)}'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recoverable_tasks(request):
    """
    获取可恢复的任务列表
    """
    try:
        # 查找状态为paused或failed的任务
        recoverable_tasks = DataExtractionTask.objects.filter(
            status__in=['paused', 'failed']
        ).order_by('-created_at')
        
        tasks_data = []
        for task in recoverable_tasks:
            # 获取检查点统计
            checkpoint_stats = checkpoint_manager.get_checkpoint_stats(task.task_id)
            
            tasks_data.append({
                'task_id': task.task_id,
                'task_type': task.task_type,
                'status': task.status,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'progress_percentage': task.get_progress_percentage(),
                'processed_documents': task.processed_documents,
                'total_documents': task.total_documents,
                'has_checkpoints': checkpoint_stats.get('has_checkpoints', False),
                'checkpoint_count': checkpoint_stats.get('checkpoint_count', 0),
                'latest_checkpoint_time': checkpoint_stats.get('latest_checkpoint_time'),
                'can_recover': True
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'recoverable_tasks': tasks_data,
                'total_count': len(tasks_data)
            }
        })
        
    except Exception as e:
        logger.error(f"获取可恢复任务列表失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'获取可恢复任务列表失败: {str(e)}'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def configure_checkpoint_settings(request):
    """
    配置检查点设置
    """
    try:
        data = request.data
        
        # 设置检查点间隔
        if 'checkpoint_interval' in data:
            interval = int(data['checkpoint_interval'])
            if interval > 0:
                checkpoint_manager.set_checkpoint_interval(interval)
        
        # 设置最大检查点数量
        if 'max_checkpoints' in data:
            max_count = int(data['max_checkpoints'])
            if max_count > 0:
                checkpoint_manager.set_max_checkpoints(max_count)
        
        return JsonResponse({
            'success': True,
            'message': '检查点设置已更新',
            'data': {
                'checkpoint_interval': checkpoint_manager._checkpoint_interval,
                'max_checkpoints': checkpoint_manager._max_checkpoints
            }
        })
        
    except Exception as e:
        logger.error(f"配置检查点设置失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'配置检查点设置失败: {str(e)}'
        }, status=500)