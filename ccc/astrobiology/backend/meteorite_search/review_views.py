"""
新的陨石数据审核API视图
支持三层数据流转：待审核 -> 已批准 -> 回收站
"""

from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q  # 添加Q对象导入
import json
import logging
from typing import Dict, Any, Union, List, Optional, cast
from django.conf import settings

from .review_models import PendingMeteorite, ApprovedMeteorite, RejectedMeteorite, MeteoriteReviewLogNew
from .review_system_v2 import NewReviewSystem
from .review_serializers import (
    PendingMeteoriteSerializer, 
    ApprovedMeteoriteSerializer, 
    RejectedMeteoriteSerializer,
    MeteoriteReviewLogSerializer
)
from .user_helpers import get_or_create_system_user

logger = logging.getLogger(__name__)

API_DEFAULT_PERMISSION = AllowAny if getattr(settings, 'API_ALLOW_ANONYMOUS', False) else IsAuthenticated

# 直接创建NewReviewSystem实例以帮助Pyright识别方法签名
review_system = NewReviewSystem()

# 修复User.DoesNotExist问题
UserDoesNotExist = User._default_manager.model.DoesNotExist

# 创建简单的辅助函数来解决Pyright类型检查问题
def call_assign_reviewer(pending_id: int, reviewer: User, assigner: User) -> bool:
    # 使用getattr安全访问方法
    method = getattr(review_system, 'assign_reviewer')
    return method(pending_id=pending_id, reviewer=reviewer, assigner=assigner)

def call_approve_meteorite(pending_id: int, reviewer: User, notes: str) -> Dict[str, Any]:
    # 使用getattr安全访问方法
    method = getattr(review_system, 'approve_meteorite')
    return cast(Dict[str, Any], method(pending_id=pending_id, reviewer=reviewer, notes=notes))

def call_reject_meteorite(pending_id: int, reviewer: User, reason: str, category: str, notes: str) -> Dict[str, Any]:
    # 使用getattr安全访问方法
    method = getattr(review_system, 'reject_meteorite')
    return cast(Dict[str, Any], method(pending_id=pending_id, reviewer=reviewer, reason=reason, category=category, notes=notes))

def call_request_revision(pending_id: int, reviewer: User, notes: str) -> bool:
    # 使用getattr安全访问方法
    method = getattr(review_system, 'request_revision')
    return method(pending_id=pending_id, reviewer=reviewer, notes=notes)


class PendingMeteoriteViewSet(viewsets.ModelViewSet):
    """待审核陨石数据ViewSet"""
    
    queryset = PendingMeteorite._default_manager.all()
    serializer_class = PendingMeteoriteSerializer
    permission_classes = [API_DEFAULT_PERMISSION]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['review_status', 'priority', 'extraction_source', 'assigned_reviewer']
    search_fields = ['name', 'classification', 'discovery_location', 'origin']
    ordering_fields = ['name', 'created_at', 'updated_at', 'confidence_score', 'priority']
    ordering = ['-priority', '-created_at']
    
    @action(detail=True, methods=['post'])
    def assign_reviewer(self, request, pk=None):
        """分配审核人员"""
        try:
            pending_meteorite = self.get_object()
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            reviewer_id = request_data.get('reviewer_id')
            
            if not reviewer_id:
                return Response({'error': '请提供审核人员ID'}, status=status.HTTP_400_BAD_REQUEST)
            
            reviewer = User._default_manager.get(id=reviewer_id)
            
            # 使用辅助函数调用方法
            success = call_assign_reviewer(
                pending_meteorite.id,
                reviewer,
                request.user
            )
            
            if success:
                return Response({'message': '审核人员分配成功'})
            else:
                return Response({'error': '分配失败'}, status=status.HTTP_400_BAD_REQUEST)
                
        except UserDoesNotExist:  # type: ignore
            return Response({'error': '审核人员不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """批准陨石数据"""
        try:
            pending_meteorite = self.get_object()
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            notes = request_data.get('notes', '')
            
            # 优化：使用统一的辅助函数获取系统用户
            system_user, created = get_or_create_system_user()
            
            # 使用辅助函数调用方法
            result = call_approve_meteorite(
                pending_meteorite.id,
                system_user,
                notes
            )
            
            # 添加类型注释解决Pyright错误
            result_dict: Dict[str, Any] = cast(Dict[str, Any], result)
            if result_dict.get('success', False):
                return Response({
                    'message': result_dict.get('message', ''),
                    'approved_id': result_dict.get('approved_id')
                })
            else:
                return Response({'error': result_dict.get('error', '未知错误')}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """拒绝陨石数据"""
        try:
            pending_meteorite = self.get_object()
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            reason = request_data.get('reason', '')
            category = request_data.get('category', 'data_quality')
            notes = request_data.get('notes', '')
            
            if not reason:
                return Response({'error': '请提供拒绝原因'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 优化：使用统一的辅助函数获取系统用户
            system_user, created = get_or_create_system_user()
            
            # 使用辅助函数调用方法
            result = call_reject_meteorite(
                pending_meteorite.id,
                system_user,
                reason,
                category,
                notes
            )
            
            # 添加类型注释解决Pyright错误
            result_dict: Dict[str, Any] = cast(Dict[str, Any], result)
            if result_dict.get('success', False):
                return Response({
                    'message': result_dict.get('message', ''),
                    'rejected_id': result_dict.get('rejected_id')
                })
            else:
                return Response({'error': result_dict.get('error', '未知错误')}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def request_revision(self, request, pk=None):
        """要求修订"""
        try:
            pending_meteorite = self.get_object()
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            notes = request_data.get('notes', '')
            
            if not notes:
                return Response({'error': '请提供修订要求'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 使用辅助函数调用方法
            success = call_request_revision(
                pending_meteorite.id,
                request.user,
                notes
            )
            
            if success:
                return Response({'message': '修订要求已提交'})
            else:
                return Response({'error': '提交失败'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _process_batch_approve(self, meteorite_ids: List[int], notes: str) -> Dict[str, Any]:
        """统一的批量通过处理，使用事务保证一致性"""
        system_user, created = get_or_create_system_user()
        success_count = 0
        failed_count = 0
        errors: List[str] = []
        approved_ids: List[int] = []
        
        with transaction.atomic():
            for meteorite_id in meteorite_ids:
                try:
                    result = call_approve_meteorite(
                        meteorite_id,
                        system_user,
                        notes
                    )
                    
                    result_dict: Dict[str, Any] = cast(Dict[str, Any], result)
                    if result_dict.get('success', False):
                        success_count += 1
                        approved_id = result_dict.get('approved_id')
                        if approved_id is not None:
                            approved_ids.append(approved_id)
                    else:
                        failed_count += 1
                        errors.append(f"ID {meteorite_id}: {result_dict.get('error', '未知错误')}")
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"ID {meteorite_id}: {str(e)}")
        
        return {
            'message': f'批量操作完成：成功 {success_count} 条，失败 {failed_count} 条',
            'success_count': success_count,
            'failed_count': failed_count,
            'approved_ids': approved_ids,
            'errors': errors
        }
    
    def _process_batch_reject(self, meteorite_ids: List[int], reason: str, category: str, notes: str) -> Dict[str, Any]:
        """统一的批量拒绝处理，使用事务保证一致性"""
        system_user, created = get_or_create_system_user()
        success_count = 0
        failed_count = 0
        errors: List[str] = []
        rejected_ids: List[int] = []
        
        with transaction.atomic():
            for meteorite_id in meteorite_ids:
                try:
                    result = call_reject_meteorite(
                        meteorite_id,
                        system_user,
                        reason,
                        category,
                        notes
                    )
                    
                    result_dict: Dict[str, Any] = cast(Dict[str, Any], result)
                    if result_dict.get('success', False):
                        success_count += 1
                        rejected_id = result_dict.get('rejected_id')
                        if rejected_id is not None:
                            rejected_ids.append(rejected_id)
                    else:
                        failed_count += 1
                        errors.append(f"ID {meteorite_id}: {result_dict.get('error', '未知错误')}")
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"ID {meteorite_id}: {str(e)}")
        
        return {
            'message': f'批量操作完成：成功 {success_count} 条，失败 {failed_count} 条',
            'success_count': success_count,
            'failed_count': failed_count,
            'rejected_ids': rejected_ids,
            'errors': errors
        }
    
    @action(detail=False, methods=['post'])
    def batch_approve(self, request):
        """批量通过陨石数据"""
        try:
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            meteorite_ids = request_data.get('meteorite_ids', [])
            notes = request_data.get('notes', '批量通过审核')
            
            if not meteorite_ids:
                return Response({'error': '请提供要批量通过的陨石ID列表'}, status=status.HTTP_400_BAD_REQUEST)
            
            result = self._process_batch_approve(meteorite_ids, notes)
            return Response(result)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def batch_reject(self, request):
        """批量拒绝陨石数据"""
        try:
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            meteorite_ids = request_data.get('meteorite_ids', [])
            reason = request_data.get('reason', '批量拒绝审核')
            category = request_data.get('category', 'data_quality')
            notes = request_data.get('notes', '批量拒绝审核')
            
            if not meteorite_ids:
                return Response({'error': '请提供要批量拒绝的陨石ID列表'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not reason:
                return Response({'error': '请提供拒绝原因'}, status=status.HTTP_400_BAD_REQUEST)
            
            result = self._process_batch_reject(meteorite_ids, reason, category, notes)
            return Response(result)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def approve_all(self, request):
        """一键通过全部待审核陨石数据"""
        try:
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            notes = request_data.get('notes', '一键通过全部审核')
            
            # 获取所有待审核的陨石
            pending_meteorites = PendingMeteorite._default_manager.all()
            meteorite_ids = list(pending_meteorites.values_list('id', flat=True))
            
            if not meteorite_ids:
                return Response({'message': '暂无待审核数据'})
            
            result = self._process_batch_approve(meteorite_ids, notes)
            return Response(result)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def reject_all(self, request):
        """一键拒绝全部待审核陨石数据"""
        try:
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            reason = request_data.get('reason', '一键拒绝全部审核')
            category = request_data.get('category', 'data_quality')
            notes = request_data.get('notes', '一键拒绝全部审核')
            
            if not reason:
                return Response({'error': '请提供拒绝原因'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取所有待审核的陨石
            pending_meteorites = PendingMeteorite._default_manager.all()
            meteorite_ids = list(pending_meteorites.values_list('id', flat=True))
            
            if not meteorite_ids:
                return Response({'message': '暂无待审核数据'})
            
            result = self._process_batch_reject(meteorite_ids, reason, category, notes)
            return Response(result)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApprovedMeteoriteViewSet(viewsets.ModelViewSet):
    """已批准陨石数据ViewSet"""
    
    queryset = ApprovedMeteorite._default_manager.filter(is_active=True)
    serializer_class = ApprovedMeteoriteSerializer
    permission_classes = [API_DEFAULT_PERMISSION]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['classification', 'origin', 'extraction_source', 'reviewer']
    search_fields = ['name', 'classification', 'discovery_location', 'origin']
    ordering_fields = ['name', 'approved_at', 'confidence_score']
    ordering = ['-approved_at']
    
    def get_queryset(self):
        """获取查询集，支持大小写不敏感搜索"""
        queryset = super().get_queryset()
        
        # 获取搜索参数
        search_param = self.request.query_params.get('search', None)
        
        # 如果有搜索参数，执行大小写不敏感搜索
        if search_param:
            queryset = queryset.filter(
                Q(name__icontains=search_param) |
                Q(classification__icontains=search_param) |
                Q(discovery_location__icontains=search_param) |
                Q(origin__icontains=search_param)
            )
        
        return queryset
    
    def destroy(self, request, *args, **kwargs):
        """重写删除方法，实现软删除到回收站"""
        try:
            approved_meteorite = self.get_object()
            
            # 优化：使用统一的辅助函数获取系统用户
            system_user, created = get_or_create_system_user()
            
            # 使用关键字参数调用方法
            kwargs = {
                'approved_id': approved_meteorite.id,
                'deleter': system_user,
                'reason': "用户删除操作"
            }
            result = cast(Dict[str, Any], review_system.move_approved_to_recycle_bin(**kwargs))
            
            if result.get('success', False):
                return Response(
                    {'message': '数据已移动到回收站'}, 
                    status=status.HTTP_204_NO_CONTENT
                )
            else:
                return Response(
                    {'error': result.get('message', '操作失败')}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"删除已批准陨石失败: {str(e)}")
            return Response(
                {'error': f'删除失败: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取已批准数据统计"""
        try:
            stats = cast(Dict[str, Any], review_system.get_review_statistics())
            return Response(stats)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RejectedMeteoriteViewSet(viewsets.ModelViewSet):
    """回收站陨石数据ViewSet"""
    
    queryset = RejectedMeteorite._default_manager.all()
    serializer_class = RejectedMeteoriteSerializer
    permission_classes = [API_DEFAULT_PERMISSION]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['rejection_category', 'reviewer', 'can_restore']
    search_fields = ['name', 'classification', 'discovery_location', 'origin', 'rejection_reason']
    ordering_fields = ['name', 'rejected_at', 'confidence_score']
    ordering = ['-rejected_at']
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """从回收站恢复数据"""
        try:
            rejected_meteorite = self.get_object()
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            notes = request_data.get('notes', '')
            
            # 创建一个默认用户用于测试
            from django.contrib.auth.models import User
            # 优化：使用统一的辅助函数获取系统用户
            default_user, created = get_or_create_system_user()
            
            # 使用关键字参数调用方法
            kwargs = {
                'rejected_id': rejected_meteorite.id,
                'restorer': default_user,
                'notes': notes
            }
            result = cast(Dict[str, Any], review_system.restore_from_recycle_bin(**kwargs))
            
            # 添加类型注释解决Pyright错误
            result_dict: Dict[str, Any] = cast(Dict[str, Any], result)
            if result_dict.get('success', False):
                return Response({
                    'message': result_dict.get('message', ''),
                    'pending_id': result_dict.get('pending_id')
                })
            else:
                return Response({'error': result_dict.get('error', '操作失败')}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['delete'])
    def permanent_delete(self, request, pk=None):
        """永久删除数据"""
        try:
            rejected_meteorite = self.get_object()
            # 添加类型注释解决Pyright错误
            request_data: Dict[str, Any] = cast(Dict[str, Any], request.data)
            notes = request_data.get('notes', '')
            
            # 创建一个默认用户用于测试
            from django.contrib.auth.models import User
            # 优化：使用统一的辅助函数获取系统用户
            default_user, created = get_or_create_system_user()
            
            success = review_system.permanently_delete(
                rejected_id=rejected_meteorite.id,
                deleter=default_user,  # 使用默认用户
                notes=notes
            )
            
            if success:
                return Response({'message': '数据已永久删除'})
            else:
                return Response({'error': '删除失败'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ==================== 传统API视图 ====================

@api_view(['POST'])
@permission_classes([API_DEFAULT_PERMISSION])
def submit_meteorite_data(request):
    """提交陨石数据到待审核表"""
    try:
        data = request.data
        
        # 验证必需字段
        required_fields = ['name', 'classification', 'discovery_location', 'origin']
        for field in required_fields:
            # 添加类型注释解决Pyright错误
            data_dict: Dict[str, Any] = cast(Dict[str, Any], data)
            if not data_dict.get(field):
                return Response(
                    {'error': f'缺少必需字段: {field}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 使用关键字参数调用方法
        kwargs = {
            'data': data,
            'submitter': request.user
        }
        result = cast(Dict[str, Any], review_system.submit_for_review(**kwargs))
        
        # 添加类型注释解决Pyright错误
        result_dict: Dict[str, Any] = cast(Dict[str, Any], result)
        if result_dict.get('success', False):
            return Response({
                'message': result_dict.get('message', ''),
                'pending_id': result_dict.get('pending_id')
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': result_dict.get('error', '提交失败')}, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"提交陨石数据失败: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([API_DEFAULT_PERMISSION])
def get_review_queue(request):
    """获取审核队列"""
    try:
        # 添加类型注释解决Pyright错误
        request_get: Dict[str, Any] = cast(Dict[str, Any], request.GET)
        status_filter = request_get.get('status')
        reviewer_id = request_get.get('reviewer_id')
        page_raw = request_get.get('page', 1)
        page_size_raw = request_get.get('page_size', 20)
        
        reviewer = None
        if reviewer_id:
            from django.contrib.auth.models import User
            reviewer = User._default_manager.get(id=reviewer_id)
        
        def _safe_int(val, default, min_val=1, max_val=100):
            try:
                num = int(val)
                return max(min_val, min(max_val, num))
            except Exception:
                return default
        
        page = _safe_int(page_raw, 1)
        page_size = _safe_int(page_size_raw, 20, 1, 200)
        
        kwargs = {
            'reviewer': reviewer,
            'status': status_filter
        }
        pending_items = cast(List[Dict[str, Any]], review_system.get_pending_reviews(**kwargs))
        total = len(pending_items)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = pending_items[start:end]
        
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': paged_items
        })
        
    except Exception as e:
        logger.error(f"获取审核队列失败: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([API_DEFAULT_PERMISSION])
def get_recycle_bin(request):
    """获取回收站数据"""
    try:
        # 添加类型注释解决Pyright错误
        request_get: Dict[str, Any] = cast(Dict[str, Any], request.GET)
        reviewer_id = request_get.get('reviewer_id')
        page_raw = request_get.get('page', 1)
        page_size_raw = request_get.get('page_size', 20)
        
        reviewer = None
        if reviewer_id:
            from django.contrib.auth.models import User
            reviewer = User._default_manager.get(id=reviewer_id)
        
        def _safe_int(val, default, min_val=1, max_val=100):
            try:
                num = int(val)
                return max(min_val, min(max_val, num))
            except Exception:
                return default
        
        page = _safe_int(page_raw, 1)
        page_size = _safe_int(page_size_raw, 20, 1, 200)
        
        kwargs = {
            'reviewer': reviewer
        }
        rejected_items = cast(List[Dict[str, Any]], review_system.get_rejected_meteorites(**kwargs))
        total = len(rejected_items)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = rejected_items[start:end]
        
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': paged_items
        })
        
    except Exception as e:
        logger.error(f"获取回收站数据失败: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([API_DEFAULT_PERMISSION])
def get_review_statistics(request):
    """获取审核统计信息"""
    try:
        stats = cast(Dict[str, Any], review_system.get_review_statistics())
        return Response(stats)
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 重复的选项API已移除，统一使用MeteoriteViewSet的options action
