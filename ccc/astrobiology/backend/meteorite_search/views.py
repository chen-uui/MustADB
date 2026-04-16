"""
陨石搜索视图
提供陨石数据的完整CRUD操作和搜索功能
"""

from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from .models import Meteorite, MeteoriteReviewLog
from .serializers import (
    MeteoriteSerializer, MeteoriteListSerializer, MeteoriteCreateSerializer,
    MeteoriteUpdateSerializer, MeteoriteReviewSerializer,
    MeteoriteBulkOperationSerializer
)
import logging

logger = logging.getLogger(__name__)


API_DEFAULT_PERMISSION = AllowAny if getattr(settings, 'API_ALLOW_ANONYMOUS', False) else IsAuthenticated


class MeteoriteViewSet(viewsets.ModelViewSet):
    """陨石数据ViewSet，提供完整的CRUD操作"""
    
    queryset = None  # 设置为None，在get_queryset中动态返回
    permission_classes = [API_DEFAULT_PERMISSION]
    filter_backends = [
        DjangoFilterBackend, 
        filters.SearchFilter, 
        filters.OrderingFilter
    ]
    filterset_fields = [
        'classification', 
        'origin', 
        'review_status', 
        'extraction_source', 
        'is_active'
    ]
    search_fields = [
        'name', 
        'classification', 
        'discovery_location', 
        'origin'
    ]
    ordering_fields = [
        'name', 
        'created_at', 
        'updated_at', 
        'confidence_score'
    ]
    ordering = ['-created_at']
    
    def get_serializer_class(self):  # type: ignore
        """根据操作类型选择序列化器"""
        if self.action == 'list':
            return MeteoriteListSerializer
        elif self.action == 'create':
            return MeteoriteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MeteoriteUpdateSerializer
        elif self.action == 'review':
            return MeteoriteReviewSerializer
        return MeteoriteSerializer
    
    def get_queryset(self):
        """获取查询集，支持高级筛选"""
        # 基础查询集
        queryset = Meteorite.objects.all()
        
        # 默认只显示活跃的数据（软删除过滤）
        queryset = queryset.filter(is_active=True)
        
        # 基础筛选
        review_status = self.request.query_params.get('review_status')
        extraction_source = self.request.query_params.get('extraction_source')
        is_active = self.request.query_params.get('is_active')
        
        # 如果明确指定了is_active参数，则覆盖默认过滤
        if is_active is not None:
            queryset = Meteorite.objects.all()  # 重新获取完整查询集
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        if review_status:
            queryset = queryset.filter(review_status=review_status)
        if extraction_source:
            queryset = queryset.filter(extraction_source=extraction_source)

        # 多选筛选
        qp = self.request.query_params
        
        def parse_list(key):
            vals = list(
                filter(None, [v.strip() for v in (qp.getlist(key) or [])])
            )
            if not vals:
                single = qp.get(key)
                if single:
                    vals = [
                        v.strip() 
                        for v in str(single).split(',') 
                        if v.strip()
                    ]
            return vals

        names = parse_list('name')
        classifications = parse_list('classification')
        locations = parse_list('discovery_location')
        origins = parse_list('origin')
        organic_names = parse_list('organic_compound_name')

        if names:
            q = Q()
            for n in names:
                q |= Q(name__icontains=n)
            queryset = queryset.filter(q)
        if classifications:
            queryset = queryset.filter(classification__in=classifications)
        if locations:
            queryset = queryset.filter(discovery_location__in=locations)
        if origins:
            queryset = queryset.filter(origin__in=origins)
        if organic_names:
            q_org = Q()
            for on in organic_names:
                q_org |= Q(organic_compounds__icontains=on)
            queryset = queryset.filter(q_org)
        
        # 置信度筛选
        min_confidence = self.request.query_params.get('min_confidence')
        max_confidence = self.request.query_params.get('max_confidence')
        
        if min_confidence:
            try:
                queryset = queryset.filter(
                    confidence_score__gte=float(min_confidence)
                )
            except ValueError:
                pass
        
        if max_confidence:
            try:
                queryset = queryset.filter(
                    confidence_score__lte=float(max_confidence)
                )
            except ValueError:
                pass
        
        # 时间范围筛选
        created_after = self.request.query_params.get('created_after')
        created_before = self.request.query_params.get('created_before')
        
        if created_after:
            try:
                queryset = queryset.filter(created_at__gte=created_after)
            except ValueError:
                pass
        
        if created_before:
            try:
                queryset = queryset.filter(created_at__lte=created_before)
            except ValueError:
                pass
        
        # 有机化合物筛选
        has_organic_compounds = self.request.query_params.get(
            'has_organic_compounds'
        )
        if has_organic_compounds == 'true':
            queryset = queryset.filter(
                organic_compounds__isnull=False
            ).exclude(organic_compounds={})
        elif has_organic_compounds == 'false':
            queryset = queryset.filter(
                Q(organic_compounds__isnull=True) | Q(organic_compounds={})
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """创建陨石数据时设置默认值"""
        serializer.save(
            review_status='pending',
            extraction_source=serializer.validated_data.get(
                'extraction_source', 'manual'
            )
        )
    
    def perform_update(self, serializer):
        """更新陨石数据"""
        serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        """软删除陨石数据"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        
        # 记录审核日志（仅在用户已认证时）
        if request.user.is_authenticated:
            MeteoriteReviewLog.objects.create(
                meteorite=instance,
                reviewer=request.user,
                action='deleted',
                previous_status=instance.review_status,
                new_status='deleted',
                notes=f"陨石数据被用户 {request.user.username} 删除"
            )
        else:
            # 匿名用户删除时的日志记录（可选择创建系统用户或跳过日志）
            logger.warning(f"匿名用户删除了陨石数据: {instance.name} (ID: {instance.id})")
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """审核陨石数据"""
        meteorite = self.get_object()
        serializer = MeteoriteReviewSerializer(
            meteorite, data=request.data, partial=True
        )
        
        if serializer.is_valid():
            previous_status = meteorite.review_status
            serializer.save(
                reviewer=request.user,
                review_date=timezone.now()
            )
            
            # 记录审核日志
            MeteoriteReviewLog.objects.create(
                meteorite=meteorite,
                reviewer=request.user,
                action=serializer.validated_data['review_status'],
                previous_status=previous_status,
                new_status=serializer.validated_data['review_status'],
                notes=serializer.validated_data.get('review_notes', ''),
                review_details={
                    'review_time': timezone.now().isoformat(),
                    'reviewer_id': request.user.id,
                    'reviewer_username': request.user.username
                }
            )
            
            return Response(MeteoriteSerializer(meteorite).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_operation(self, request):
        """批量操作陨石数据"""
        serializer = MeteoriteBulkOperationSerializer(data=request.data)
        
        if serializer.is_valid():
            validated_data = serializer.validated_data
            # 直接使用type: ignore注释忽略Pyright报错
            ids = validated_data.get('ids', []) if validated_data else []  # type: ignore
            action = validated_data.get('action', '') if validated_data else ''  # type: ignore
            notes = validated_data.get('notes', '') if validated_data else ''  # type: ignore
            
            meteorites = Meteorite.objects.filter(id__in=ids)  # type: ignore
            updated_count = 0
            
            with transaction.atomic():
                for meteorite in meteorites:
                    previous_status = meteorite.review_status
                    new_status = meteorite.review_status  # 默认值
                    
                    if action == 'delete':
                        meteorite.is_active = False
                        new_status = 'deleted'
                    elif action == 'activate':
                        meteorite.is_active = True
                        new_status = meteorite.review_status
                    elif action == 'deactivate':
                        meteorite.is_active = False
                        new_status = 'deactivated'
                    elif action == 'approve':
                        meteorite.review_status = 'approved'
                        meteorite.reviewer = request.user
                        meteorite.review_date = timezone.now()
                        new_status = 'approved'
                    elif action == 'reject':
                        meteorite.review_status = 'rejected'
                        meteorite.reviewer = request.user
                        meteorite.review_date = timezone.now()
                        new_status = 'rejected'
                    
                    meteorite.save()
                    updated_count += 1
                    
                    # 记录审核日志
                    MeteoriteReviewLog.objects.create(  # type: ignore
                        meteorite=meteorite,
                        reviewer=request.user,
                        action=action,
                        previous_status=previous_status,
                        new_status=new_status,
                        notes=notes,
                        review_details={
                            'bulk_operation': True,
                            'operation_time': timezone.now().isoformat(),
                            'total_items': len(ids)
                        }
                    )
            
            return Response({
                'message': f'成功{action} {updated_count} 条记录',
                'updated_count': updated_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def options(self, request):
        """获取搜索选项（用于下拉菜单）"""
        try:
            # 获取不重复的选项值
            classifications = list(
                Meteorite.objects.filter(is_active=True)  # type: ignore
                .values_list('classification', flat=True)
                .distinct()
                .exclude(classification__isnull=True)
                .exclude(classification='')
            )
            
            origins = list(
                Meteorite.objects.filter(is_active=True)  # type: ignore
                .values_list('origin', flat=True)
                .distinct()
                .exclude(origin__isnull=True)
                .exclude(origin='')
            )
            
            discovery_locations = list(
                Meteorite.objects.filter(is_active=True)  # type: ignore
                .values_list('discovery_location', flat=True)
                .distinct()
                .exclude(discovery_location__isnull=True)
                .exclude(discovery_location='')
            )
            
            # 获取有机化合物名称
            organic_compound_names = set()
            for meteorite in Meteorite.objects.filter(  # type: ignore
                is_active=True, 
                organic_compounds__isnull=False
            ).exclude(organic_compounds={}):
                if (meteorite.organic_compounds and 
                        isinstance(meteorite.organic_compounds, list)):
                    for compound in meteorite.organic_compounds:
                        if isinstance(compound, dict) and 'name' in compound:
                            organic_compound_names.add(compound['name'])
            
            # 审核相关选项
            review_statuses = [
                {'value': 'pending', 'label': '待审核'},
                {'value': 'under_review', 'label': '审核中'},
                {'value': 'needs_revision', 'label': '需要修订'},
                {'value': 'approved', 'label': '已批准'},
                {'value': 'rejected', 'label': '已拒绝'}
            ]
            
            rejection_categories = [
                {'value': 'data_quality', 'label': '数据质量问题'},
                {'value': 'incomplete_info', 'label': '信息不完整'},
                {'value': 'duplicate', 'label': '重复数据'},
                {'value': 'invalid_classification', 'label': '分类错误'},
                {'value': 'contamination_concern', 'label': '污染问题'},
                {'value': 'reference_issue', 'label': '参考文献问题'},
                {'value': 'other', 'label': '其他原因'}
            ]
            
            return Response({
                'classifications': sorted(classifications),
                'origins': sorted(origins),
                'discovery_locations': sorted(discovery_locations),
                'organic_compounds': sorted(list(organic_compound_names)),
                'review_statuses': review_statuses,
                'rejection_categories': rejection_categories
            })
            
        except Exception as e:
            logger.error(f"获取搜索选项失败: {str(e)}")
            return Response(
                {'error': '获取选项数据失败'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取陨石数据统计信息"""
        # 优化：使用聚合查询一次性获取所有统计信息，避免多次count()查询
        from django.db.models import Count
        
        base_queryset = (
            Meteorite.objects.filter(is_active=True)  # type: ignore
        )
        total_count = base_queryset.count()
        
        # 按审核状态统计 - 使用聚合查询
        review_stats_query = base_queryset.values('review_status').annotate(
            count=Count('id')
        )
        review_stats = {
            item['review_status']: item['count'] 
            for item in review_stats_query
        }
        # 确保所有状态都有值
        for status_choice in [
            'pending', 'approved', 'rejected', 'needs_revision'
        ]:
            if status_choice not in review_stats:
                review_stats[status_choice] = 0
        
        # 按数据来源统计 - 使用聚合查询
        source_stats_query = (
            base_queryset.values('extraction_source').annotate(
                count=Count('id')
            )
        )  # type: ignore
        source_stats = {
            item['extraction_source']: item['count'] 
            for item in source_stats_query
        }
        # 确保所有来源都有值
        for source_choice in ['manual', 'rag_extraction', 'import']:
            if source_choice not in source_stats:
                source_stats[source_choice] = 0
        
        # 按分类统计（前10）
        from django.db import models
        classification_stats = list(
            Meteorite.objects.filter(is_active=True)  # type: ignore
            .values('classification')
            .annotate(count=models.Count('id'))
            .order_by('-count')[:10]
        )
        
        return Response({
            'total_count': total_count,
            'review_status_stats': review_stats,
            'extraction_source_stats': source_stats,
            'classification_stats': classification_stats
        })


# 重复的函数式视图已移除，统一使用MeteoriteViewSet提供搜索功能
