"""
任务恢复相关的URL配置
"""

from django.urls import path
from . import views_task_recovery

urlpatterns = [
    # 系统启动恢复
    path('recovery/system-startup/', views_task_recovery.system_startup_recovery, name='system_startup_recovery'),
    
    # 手动恢复任务
    path('recovery/manual/<str:task_id>/', views_task_recovery.manual_recover_task, name='manual_recover_task'),
    
    # 获取恢复状态
    path('recovery/status/', views_task_recovery.get_recovery_status, name='get_recovery_status'),
    
    # 获取可恢复的任务列表
    path('recovery/recoverable-tasks/', views_task_recovery.get_recoverable_tasks, name='get_recoverable_tasks'),
    
    # 检查点相关API
    path('checkpoints/<str:task_id>/', views_task_recovery.list_task_checkpoints, name='list_task_checkpoints'),
    path('checkpoints/<str:task_id>/<str:checkpoint_id>/', views_task_recovery.get_checkpoint_details, name='get_checkpoint_details'),
    path('checkpoints/<str:task_id>/stats/', views_task_recovery.get_checkpoint_stats, name='get_checkpoint_stats'),
    path('checkpoints/<str:task_id>/clear/', views_task_recovery.clear_task_checkpoints, name='clear_task_checkpoints'),
    
    # 检查点配置
    path('checkpoints/configure/', views_task_recovery.configure_checkpoint_settings, name='configure_checkpoint_settings'),
]