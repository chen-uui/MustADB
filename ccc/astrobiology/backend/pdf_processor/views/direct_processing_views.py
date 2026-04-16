"""
直接处理API视图
"""

import logging
import uuid
import os
import threading
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import json

from ..direct_processing.document_processor import DirectDocumentProcessor
from ..models import DirectProcessingResult, ProcessingTask, ProcessingLog, ProcessingStatistics
from ..direct_processing.utils import validate_pdf_file, generate_file_hash
from ..services.upload_storage_service import MEDIA_UPLOADS, UploadStorageService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class DirectProcessingViewSet(ViewSet):
    """直接处理API视图集"""
    
    def __init__(self):
        """初始化视图集"""
        self.processor = DirectDocumentProcessor()
        
        # 初始化智能提取系统
        try:
            from ..intelligent_meteorite_extraction_system import IntelligentMeteoriteExtractionSystem
            self.intelligent_system = IntelligentMeteoriteExtractionSystem()
        except Exception as e:
            logger.warning(f"IntelligentMeteoriteExtractionSystem unavailable: {e}")
            self.intelligent_system = None
        
        super().__init__()
    
    def process_document(self, request):
        """
        处理单个文档
        
        POST /api/direct-processing/process/
        """
        try:
            # 添加CORS头部
            response_headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
                'Access-Control-Allow-Credentials': 'true',
            }
            
            # 处理OPTIONS预检请求
            if request.method == 'OPTIONS':
                response = HttpResponse()
                for key, value in response_headers.items():
                    response[key] = value
                return response
            
            if request.method != 'POST':
                response = JsonResponse({'error': 'Method not allowed'}, status=405)
                for key, value in response_headers.items():
                    response[key] = value
                return response
            
            # 检查是否有文件上传
            if 'file' not in request.FILES:
                return JsonResponse({'error': 'No file uploaded'}, status=400)
            
            uploaded_file = request.FILES['file']
            
            # 验证文件类型
            if not uploaded_file.name.lower().endswith('.pdf'):
                return JsonResponse({'error': 'Only PDF files are allowed'}, status=400)
            
            # 获取处理选项
            options = {}
            if 'options' in request.POST:
                try:
                    options = json.loads(request.POST['options'])
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Invalid options JSON'}, status=400)

            duplicate_inspection = UploadStorageService.inspect_uploaded_file(uploaded_file)
            UploadStorageService.log_duplicate_inspection(logger, 'direct_processing', duplicate_inspection)
            
            # 保存上传的文件
            file_path = self._save_uploaded_file(uploaded_file, duplicate_inspection=duplicate_inspection)
            
            # 验证PDF文件
            validation_result = validate_pdf_file(file_path)
            if not validation_result['valid']:
                return JsonResponse({
                    'error': 'Invalid PDF file',
                    'details': validation_result['error_message']
                }, status=400)
            
            # 创建处理任务（处理匿名用户情况）
            user = request.user if request.user.is_authenticated else None
            task = self._create_processing_task(file_path, options, user)
            
            # 异步处理文档
            self._process_document_async(task)
            
            response = JsonResponse({
                'task_id': task.task_id,
                'status': task.status,
                'message': 'Document processing started'
            })
            
            # 添加CORS头部
            for key, value in response_headers.items():
                response[key] = value
            return response
            
        except Exception as e:
            logger.error(f"Error in process_document: {str(e)}")
            response = JsonResponse({'error': str(e)}, status=500)
            # 添加CORS头部
            for key, value in response_headers.items():
                response[key] = value
            return response
    
    def get_processing_status(self, request, task_id):
        """
        获取处理状态
        
        GET /api/direct-processing/status/{task_id}/
        """
        try:
            task = ProcessingTask.objects.get(task_id=task_id)
            
            status_info = {
                'task_id': task.task_id,
                'status': task.status,
                'progress': task.progress,
                'current_step': task.current_step,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'error_message': task.error_message if task.status == 'failed' else None
            }
            
            # 如果任务完成，添加结果ID
            if task.status == 'completed':
                try:
                    result = DirectProcessingResult.objects.filter(task_id=task.task_id).first()
                    if result:
                        status_info['result_id'] = result.id
                except Exception as e:
                    logger.error(f"Error getting result ID for task {task.task_id}: {str(e)}")
            
            return JsonResponse(status_info)
            
        except ProcessingTask.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)
        except Exception as e:
            logger.error(f"Error getting processing status: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_processing_result(self, request, result_id):
        """
        获取处理结果
        
        GET /api/direct-processing/result/{result_id}/
        """
        try:
            result = DirectProcessingResult.objects.get(id=result_id)
            
            result_data = {
                'id': result.id,
                'document_path': result.document_path,
                'document_title': result.document_title,
                'processing_time': result.processing_time,
                'confidence_score': result.confidence_score,
                'status': result.status,
                'created_at': result.created_at.isoformat(),
                'meteorite_data': result.meteorite_data,
                'organic_compounds': result.organic_compounds,
                'mineral_relationships': result.mineral_relationships,
                'scientific_insights': result.scientific_insights,
                'validation_checks': result.validation_checks,
                'validation_notes': result.validation_notes,
                'processing_summary': result.get_processing_summary()
            }
            
            return JsonResponse(result_data)
            
        except DirectProcessingResult.DoesNotExist:
            return JsonResponse({'error': 'Result not found'}, status=404)
        except Exception as e:
            logger.error(f"Error getting processing result: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def batch_process(self, request):
        """
        批量处理文档
        
        POST /api/direct-processing/batch/
        """
        try:
            if request.method != 'POST':
                return JsonResponse({'error': 'Method not allowed'}, status=405)
            
            # 检查是否有文件上传
            if 'files' not in request.FILES:
                return JsonResponse({'error': 'No files uploaded'}, status=400)
            
            uploaded_files = request.FILES.getlist('files')
            
            # 验证文件数量
            if len(uploaded_files) > 10:  # 限制批量处理数量
                return JsonResponse({'error': 'Too many files (max 10)'}, status=400)
            
            # 获取处理选项
            options = {}
            if 'options' in request.POST:
                try:
                    options = json.loads(request.POST['options'])
                except json.JSONDecodeError:
                    return JsonResponse({'error': 'Invalid options JSON'}, status=400)
            
            # 创建批量处理任务
            task_ids = []
            skipped_files = []
            user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
            for uploaded_file in uploaded_files:
                if uploaded_file.name.lower().endswith('.pdf'):
                    duplicate_inspection = UploadStorageService.inspect_uploaded_file(uploaded_file)
                    UploadStorageService.log_duplicate_inspection(logger, 'direct_processing_batch', duplicate_inspection)
                    file_path = self._save_uploaded_file(uploaded_file, duplicate_inspection=duplicate_inspection)
                    task = self._create_processing_task(file_path, options, user)
                    task_ids.append(task.task_id)
                    self._process_document_async(task)
                else:
                    skipped_files.append(uploaded_file.name)
            
            return JsonResponse({
                'task_ids': task_ids,
                'message': f'Batch processing started for {len(task_ids)} documents',
                'skipped_files': skipped_files
            })
            
        except Exception as e:
            logger.error(f"Error in batch_process: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_processing_history(self, request):
        """
        获取处理历史
        
        GET /api/direct-processing/history/
        """
        try:
            # 获取查询参数
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            status = request.GET.get('status', '')
            
            # 构建查询
            queryset = DirectProcessingResult.objects.all()
            if status:
                queryset = queryset.filter(status=status)
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            
            results = queryset[start:end]
            
            # 构建响应数据
            history_data = []
            for result in results:
                history_data.append({
                    'id': result.id,
                    'document_title': result.document_title,
                    'status': result.status,
                    'confidence_score': result.confidence_score,
                    'processing_time': result.processing_time,
                    'created_at': result.created_at.isoformat(),
                    'meteorite_name': result.get_meteorite_name()
                })
            
            return JsonResponse({
                'results': history_data,
                'page': page,
                'page_size': page_size,
                'total': queryset.count()
            })
            
        except Exception as e:
            logger.error(f"Error getting processing history: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def delete_processing_result(self, request, result_id):
        """
        删除处理结果
        
        DELETE /api/direct-processing/result/{result_id}/
        """
        try:
            if request.method not in ('DELETE', 'POST'):
                return JsonResponse({'error': 'Method not allowed'}, status=405)
            result = DirectProcessingResult.objects.get(id=result_id)
            result.delete()
            
            return JsonResponse({'message': 'Result deleted successfully'})
            
        except DirectProcessingResult.DoesNotExist:
            return JsonResponse({'error': 'Result not found'}, status=404)
        except Exception as e:
            logger.error(f"Error deleting processing result: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_processing_statistics(self, request):
        """
        获取处理统计
        
        GET /api/direct-processing/statistics/
        """
        try:
            # 获取统计参数
            days = int(request.GET.get('days', 30))
            
            # 计算统计日期范围
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # 获取统计数据
            stats = ProcessingStatistics.objects.filter(
                date__range=[start_date, end_date]
            ).order_by('-date')
            
            # 构建统计数据
            statistics_data = []
            for stat in stats:
                statistics_data.append({
                    'date': stat.date.isoformat(),
                    'total_documents': stat.total_documents,
                    'successful_documents': stat.successful_documents,
                    'failed_documents': stat.failed_documents,
                    'avg_processing_time': stat.avg_processing_time,
                    'avg_confidence_score': stat.avg_confidence_score,
                    'total_meteorites': stat.total_meteorites,
                    'total_organic_compounds': stat.total_organic_compounds,
                    'total_insights': stat.total_insights
                })
            
            return JsonResponse({
                'statistics': statistics_data,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting processing statistics: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    # Legacy administrative handlers retained for manual invocation only.
    # These methods are not exposed by direct_processing_urls.py.
    def legacy_submit_feedback(self, request):
        """提交用户反馈"""
        if self.intelligent_system is None:
            return Response({'success': False, 'error': 'Intelligent system is unavailable'}, status=503)
        try:
            feedback_data = request.data
            
            # 验证必需字段
            required_fields = ['extraction_id', 'feedback_type', 'field_name']
            for field in required_fields:
                if field not in feedback_data:
                    return Response({
                        'success': False,
                        'error': f'缺少必需字段: {field}'
                    }, status=400)
            
            # 提交反馈
            success = self.intelligent_system.submit_user_feedback(
                extraction_id=feedback_data.get('extraction_id'),
                feedback_data=feedback_data,
                user_id=request.user.id if request.user.is_authenticated else 'anonymous'
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': '反馈提交成功'
                })
            else:
                return Response({
                    'success': False,
                    'error': '反馈提交失败'
                }, status=500)
                
        except Exception as e:
            logger.error(f"提交反馈失败: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

    def legacy_get_optimization_suggestions(self, request):
        """获取优化建议"""
        if self.intelligent_system is None:
            return Response({'success': False, 'error': 'Intelligent system is unavailable'}, status=503)
        try:
            suggestions = self.intelligent_system.feedback_manager.generate_optimization_suggestions()
            
            suggestions_data = []
            for suggestion in suggestions:
                suggestions_data.append({
                    'id': suggestion.suggestion_id,
                    'category': suggestion.category,
                    'priority': suggestion.priority,
                    'description': suggestion.description,
                    'implementation_details': suggestion.implementation_details,
                    'expected_improvement': suggestion.expected_improvement,
                    'confidence': suggestion.confidence,
                    'created_at': suggestion.created_at
                })
            
            return Response({
                'success': True,
                'suggestions': suggestions_data
            })
            
        except Exception as e:
            logger.error(f"获取优化建议失败: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

    def legacy_optimize_system(self, request):
        """执行系统优化"""
        if self.intelligent_system is None:
            return Response({'success': False, 'error': 'Intelligent system is unavailable'}, status=503)
        try:
            optimization_result = self.intelligent_system.optimize_system()
            
            return Response({
                'success': True,
                'optimization_result': optimization_result
            })
            
        except Exception as e:
            logger.error(f"系统优化失败: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

    def legacy_get_system_performance(self, request):
        """获取系统性能指标"""
        if self.intelligent_system is None:
            return Response({'success': False, 'error': 'Intelligent system is unavailable'}, status=503)
        try:
            performance = self.intelligent_system.get_system_performance()
            
            return Response({
                'success': True,
                'performance': {
                    'total_extractions': performance.total_extractions,
                    'successful_extractions': performance.successful_extractions,
                    'success_rate': performance.successful_extractions / performance.total_extractions if performance.total_extractions > 0 else 0,
                    'average_confidence': performance.average_confidence,
                    'average_processing_time': performance.average_processing_time,
                    'user_satisfaction': performance.user_satisfaction,
                    'common_issues': performance.common_issues,
                    'optimization_opportunities': performance.optimization_opportunities
                }
            })
            
        except Exception as e:
            logger.error(f"获取系统性能失败: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _save_uploaded_file(self, uploaded_file, duplicate_inspection=None):
        """保存上传的文件"""
        try:
            stored_upload = UploadStorageService.save_uploaded_file(
                uploaded_file,
                storage_key=MEDIA_UPLOADS,
                naming_strategy='uuid',
                precomputed_inspection=duplicate_inspection,
            )
            return stored_upload.file_path
            
        except Exception as e:
            logger.error(f"Error saving uploaded file: {str(e)}")
            raise
    
    def _create_processing_task(self, file_path, options, user):
        """创建处理任务"""
        try:
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 创建任务
            task = ProcessingTask.objects.create(
                task_id=task_id,
                document_path=file_path,
                options=options,
                created_by=user
            )
            
            # 记录日志
            ProcessingLog.objects.create(
                task=task,
                level='INFO',
                message=f'Processing task created for {file_path}'
            )
            
            return task
            
        except Exception as e:
            logger.error(f"Error creating processing task: {str(e)}")
            raise
    
    def _process_document_async(self, task):
        """异步处理文档"""
        threading.Thread(
            target=self._run_processing_task,
            args=(str(task.task_id),),
            daemon=True
        ).start()

    def _run_processing_task(self, task_id: str):
        """在后台线程中执行实际的处理逻辑"""
        try:
            task = ProcessingTask.objects.get(task_id=task_id)
        except ProcessingTask.DoesNotExist:
            logger.error(f"处理任务不存在，无法执行: {task_id}")
            return

        try:
            task.start_processing()
            ProcessingLog.objects.create(
                task=task,
                level='INFO',
                message='Document processing started'
            )

            result = self.processor.process_document(task.document_path, task.options)

            processing_result = DirectProcessingResult.objects.create(
                task_id=task.task_id,
                document_path=result.document_path,
                document_title=os.path.basename(result.document_path),
                processing_time=result.processing_time,
                confidence_score=result.confidence_score,
                meteorite_data=result.results.data.meteorite_data,
                organic_compounds=result.results.data.organic_compounds,
                mineral_relationships=result.results.data.mineral_relationships,
                scientific_insights=result.results.data.scientific_insights,
                validation_checks=[{
                    'check_name': check.check_name,
                    'passed': check.passed,
                    'message': check.message,
                    'confidence': check.confidence
                } for check in result.results.validation_checks],
                validation_notes=result.results.validation_notes,
                status='completed'
            )

            task.complete_processing(processing_result)
            ProcessingLog.objects.create(
                task=task,
                level='INFO',
                message=f'Document processing completed successfully. Result ID: {processing_result.id}'
            )

        except Exception as e:
            task.fail_processing(str(e))
            ProcessingLog.objects.create(
                task=task,
                level='ERROR',
                message=f'Document processing failed: {str(e)}'
            )
            logger.error(f"Error processing document {task.document_path}: {str(e)}")


# 视图函数包装器
@csrf_exempt
def process_document_view(request):
    """处理文档视图"""
    viewset = DirectProcessingViewSet()
    return viewset.process_document(request)


@csrf_exempt
def get_processing_status_view(request, task_id):
    """获取处理状态视图"""
    viewset = DirectProcessingViewSet()
    return viewset.get_processing_status(request, task_id)


@csrf_exempt
def get_processing_result_view(request, result_id):
    """获取处理结果视图"""
    viewset = DirectProcessingViewSet()
    return viewset.get_processing_result(request, result_id)


@csrf_exempt
def batch_process_view(request):
    """批量处理视图"""
    viewset = DirectProcessingViewSet()
    return viewset.batch_process(request)


def get_processing_history_view(request):
    """获取处理历史视图"""
    viewset = DirectProcessingViewSet()
    return viewset.get_processing_history(request)


@csrf_exempt
def delete_processing_result_view(request, result_id):
    """删除处理结果视图"""
    viewset = DirectProcessingViewSet()
    return viewset.delete_processing_result(request, result_id)


def get_processing_statistics_view(request):
    """获取处理统计视图"""
    viewset = DirectProcessingViewSet()
    return viewset.get_processing_statistics(request)
