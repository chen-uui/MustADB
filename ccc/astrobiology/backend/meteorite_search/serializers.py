"""
陨石搜索序列化器
定义陨石数据的序列化和反序列化逻辑
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Meteorite, MeteoriteReviewLog, DataExtractionTask
import json


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class MeteoriteSerializer(serializers.ModelSerializer):
    """陨石详细序列化器"""
    
    organic_compound_names = serializers.SerializerMethodField()
    reviewer_info = UserSerializer(source='reviewer', read_only=True)
    organic_compounds_summary = serializers.CharField(source='get_organic_compounds_summary', read_only=True)
    references_count = serializers.IntegerField(source='get_references_count', read_only=True)
    is_pending_review = serializers.BooleanField(read_only=True)
    is_approved = serializers.BooleanField(read_only=True)
    needs_review = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Meteorite
        fields = [
            'id', 'name', 'classification', 'discovery_location', 'origin',
            'organic_compounds', 'organic_compound_names', 'contamination_exclusion_method', 
            'references', 'created_at', 'updated_at', 'is_active', 'review_status',
            'reviewer', 'reviewer_info', 'review_date', 'review_notes',
            'confidence_score', 'extraction_source', 'extraction_metadata',
            'organic_compounds_summary', 'references_count', 'is_pending_review',
            'is_approved', 'needs_review'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_organic_compound_names(self, obj):
        """返回有机化合物名称列表"""
        if obj.organic_compounds:
            try:
                if isinstance(obj.organic_compounds, str):
                    # 如果是字符串，尝试解析JSON
                    compounds = json.loads(obj.organic_compounds)
                else:
                    # 已经是Python对象（列表）
                    compounds = obj.organic_compounds
                
                if isinstance(compounds, list):
                    return [compound.get('name', '') for compound in compounds if isinstance(compound, dict) and compound.get('name')]
                else:
                    return []
            except (json.JSONDecodeError, AttributeError):
                return []
        return []
    
    def validate_confidence_score(self, value):
        """验证置信度分数"""
        if not (0.0 <= value <= 1.0):
            raise serializers.ValidationError("置信度分数必须在0.0到1.0之间")
        return value
    
    def validate_organic_compounds(self, value):
        """验证有机化合物数据格式"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("有机化合物数据必须是字典格式")
        return value
    
    def validate_references(self, value):
        """验证参考文献数据格式"""
        if not isinstance(value, list):
            raise serializers.ValidationError("参考文献数据必须是列表格式")
        return value


class MeteoriteListSerializer(serializers.ModelSerializer):
    """陨石列表序列化器（简化版）"""
    
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    organic_compounds_summary = serializers.CharField(source='get_organic_compounds_summary', read_only=True)
    references_count = serializers.IntegerField(source='get_references_count', read_only=True)
    
    class Meta:
        model = Meteorite
        fields = [
            'id', 'name', 'classification', 'discovery_location', 'origin',
            'review_status', 'reviewer_name', 'confidence_score', 'extraction_source',
            'created_at', 'updated_at', 'is_active', 'organic_compounds_summary',
            'references_count'
        ]


class MeteoriteCreateSerializer(serializers.ModelSerializer):
    """陨石创建序列化器"""
    
    class Meta:
        model = Meteorite
        fields = [
            'name', 'classification', 'discovery_location', 'origin',
            'organic_compounds', 'contamination_exclusion_method', 'references',
            'confidence_score', 'extraction_source', 'extraction_metadata'
        ]
    
    def validate_name(self, value):
        """验证陨石名称唯一性"""
        if Meteorite.objects.filter(name=value, is_active=True).exists():
            raise serializers.ValidationError("该陨石名称已存在")
        return value


class MeteoriteUpdateSerializer(serializers.ModelSerializer):
    """陨石更新序列化器"""
    
    class Meta:
        model = Meteorite
        fields = [
            'name', 'classification', 'discovery_location', 'origin',
            'organic_compounds', 'contamination_exclusion_method', 'references',
            'confidence_score', 'extraction_source', 'extraction_metadata',
            'is_active'
        ]
    
    def validate_name(self, value):
        """验证陨石名称唯一性（排除当前实例）"""
        instance = self.instance
        if Meteorite.objects.filter(name=value, is_active=True).exclude(id=instance.id).exists():
            raise serializers.ValidationError("该陨石名称已存在")
        return value


class MeteoriteReviewSerializer(serializers.ModelSerializer):
    """陨石审核序列化器"""
    
    class Meta:
        model = Meteorite
        fields = ['review_status', 'review_notes']
    
    def validate_review_status(self, value):
        """验证审核状态"""
        valid_statuses = ['pending', 'approved', 'rejected', 'needs_revision']
        if value not in valid_statuses:
            raise serializers.ValidationError(f"无效的审核状态，必须是: {', '.join(valid_statuses)}")
        return value


class MeteoriteSearchSerializer(serializers.Serializer):
    """陨石搜索序列化器"""
    
    name = serializers.CharField(required=False, allow_blank=True)
    classification = serializers.CharField(required=False, allow_blank=True)
    discovery_location = serializers.CharField(required=False, allow_blank=True)
    origin = serializers.CharField(required=False, allow_blank=True)
    organic_compound = serializers.CharField(required=False, allow_blank=True)
    review_status = serializers.ChoiceField(
        choices=['pending', 'approved', 'rejected', 'needs_revision'],
        required=False,
        help_text="审核状态筛选"
    )
    extraction_source = serializers.ChoiceField(
        choices=['manual', 'rag_extraction', 'import'],
        required=False,
        help_text="数据来源筛选"
    )
    min_confidence = serializers.FloatField(
        min_value=0.0, max_value=1.0,
        required=False,
        help_text="最小置信度"
    )
    max_confidence = serializers.FloatField(
        min_value=0.0, max_value=1.0,
        required=False,
        help_text="最大置信度"
    )
    created_after = serializers.DateTimeField(required=False, help_text="创建时间起始")
    created_before = serializers.DateTimeField(required=False, help_text="创建时间结束")
    is_active = serializers.BooleanField(required=False, help_text="是否激活")
    page = serializers.IntegerField(required=False, default=1, min_value=1)
    page_size = serializers.IntegerField(required=False, default=10, min_value=1, max_value=100)
    
    def validate(self, data):
        """验证搜索参数"""
        min_confidence = data.get('min_confidence')
        max_confidence = data.get('max_confidence')
        
        if min_confidence is not None and max_confidence is not None:
            if min_confidence > max_confidence:
                raise serializers.ValidationError("最小置信度不能大于最大置信度")
        
        created_after = data.get('created_after')
        created_before = data.get('created_before')
        
        if created_after is not None and created_before is not None:
            if created_after > created_before:
                raise serializers.ValidationError("开始时间不能晚于结束时间")
        
        return data


class MeteoriteBulkOperationSerializer(serializers.Serializer):
    """陨石批量操作序列化器"""
    
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="要操作的陨石ID列表"
    )
    action = serializers.ChoiceField(
        choices=['delete', 'activate', 'deactivate', 'approve', 'reject'],
        help_text="批量操作类型"
    )
    notes = serializers.CharField(
        required=False,
        max_length=1000,
        help_text="操作备注"
    )
    
    def validate_ids(self, value):
        """验证ID列表"""
        if len(value) > 100:
            raise serializers.ValidationError("单次批量操作最多支持100条记录")
        
        # 验证所有ID都存在
        existing_ids = set(Meteorite.objects.filter(id__in=value).values_list('id', flat=True))
        invalid_ids = set(value) - existing_ids
        
        if invalid_ids:
            raise serializers.ValidationError(f"以下ID不存在: {list(invalid_ids)}")
        
        return value