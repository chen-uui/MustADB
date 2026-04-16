"""
直接处理URL路由
"""

from django.urls import path, include
from ..views.direct_processing_views import (
    process_document_view,
    get_processing_status_view,
    get_processing_result_view,
    delete_processing_result_view,
    batch_process_view,
    get_processing_history_view,
    get_processing_statistics_view
)

urlpatterns = [
    # 核心处理端点
    path('process/', process_document_view, name='process_document'),
    path('status/<str:task_id>/', get_processing_status_view, name='get_processing_status'),
    path('result/<int:result_id>/', get_processing_result_view, name='get_processing_result'),
    path('result/<int:result_id>/delete/', delete_processing_result_view, name='delete_processing_result'),
    
    # 批量处理端点
    path('batch/', batch_process_view, name='batch_process'),
    
    # 历史和统计端点
    path('history/', get_processing_history_view, name='get_processing_history'),
    path('statistics/', get_processing_statistics_view, name='get_processing_statistics'),
]
