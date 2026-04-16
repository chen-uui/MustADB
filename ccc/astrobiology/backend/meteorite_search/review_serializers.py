"""
新的陨石数据序列化器
支持三层数据流转的序列化
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .review_models import PendingMeteorite, ApprovedMeteorite, RejectedMeteorite, MeteoriteReviewLogNew


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class PendingMeteoriteSerializer(serializers.ModelSerializer):
    """待审核陨石数据序列化器"""
    
    assigned_reviewer_info = UserSerializer(source='assigned_reviewer', read_only=True)
    submitter_info = UserSerializer(source='submitter', read_only=True)
    
    class Meta:
        model = PendingMeteorite
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'submitter']
    
    def create(self, validated_data):
        # 设置提交者为当前用户
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['submitter'] = request.user
        return super().create(validated_data)


class ApprovedMeteoriteSerializer(serializers.ModelSerializer):
    """已批准陨石数据序列化器"""
    
    reviewer_info = UserSerializer(source='reviewer', read_only=True)
    
    class Meta:
        model = ApprovedMeteorite
        fields = '__all__'
        read_only_fields = [
            'id', 'approved_at', 'reviewer', 'review_notes', 
            'original_pending_id', 'is_active'
        ]


class RejectedMeteoriteSerializer(serializers.ModelSerializer):
    """回收站陨石数据序列化器"""
    
    reviewer_info = UserSerializer(source='reviewer', read_only=True)
    
    class Meta:
        model = RejectedMeteorite
        fields = '__all__'
        read_only_fields = [
            'id', 'rejected_at', 'reviewer', 'rejection_reason', 
            'rejection_category', 'rejection_notes', 'original_pending_id',
            'can_restore'
        ]


class MeteoriteReviewLogSerializer(serializers.ModelSerializer):
    """陨石审核日志序列化器"""
    
    reviewer_info = UserSerializer(source='reviewer', read_only=True)
    
    class Meta:
        model = MeteoriteReviewLogNew
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class ReviewActionSerializer(serializers.Serializer):
    """审核操作序列化器"""
    
    action = serializers.ChoiceField(choices=[
        ('approve', '批准'),
        ('reject', '拒绝'),
        ('request_revision', '要求修订')
    ])
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    category = serializers.ChoiceField(
        choices=[
            ('data_quality', '数据质量问题'),
            ('incomplete_info', '信息不完整'),
            ('duplicate', '重复数据'),
            ('invalid_classification', '分类错误'),
            ('contamination_concern', '污染问题'),
            ('reference_issue', '参考文献问题'),
            ('other', '其他原因')
        ],
        required=False
    )
    
    def validate(self, attrs):  # 修复参数名称为attrs以匹配基类方法
        action = attrs.get('action')
        
        if action == 'reject':
            if not attrs.get('reason'):
                raise serializers.ValidationError('拒绝操作必须提供拒绝原因')
            if not attrs.get('category'):
                attrs['category'] = 'other'
        
        return attrs


class AssignReviewerSerializer(serializers.Serializer):
    """分配审核人员序列化器"""
    
    reviewer_id = serializers.IntegerField()
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_reviewer_id(self, value):
        try:
            User.objects.get(id=value)
            return value
        except User.DoesNotExist:  # type: ignore
            raise serializers.ValidationError('指定的审核人员不存在')


class RestoreSerializer(serializers.Serializer):
    """恢复数据序列化器"""
    
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class PermanentDeleteSerializer(serializers.Serializer):
    """永久删除序列化器"""
    
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    confirm = serializers.BooleanField(default=False)
    
    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError('必须确认永久删除操作')
        return value


class ReviewStatisticsSerializer(serializers.Serializer):
    """审核统计序列化器"""
    
    pending_count = serializers.IntegerField()
    approved_count = serializers.IntegerField()
    rejected_count = serializers.IntegerField()
    under_review_count = serializers.IntegerField()
    needs_revision_count = serializers.IntegerField()
    
    # 按分类统计
    classification_stats = serializers.DictField()
    
    # 按来源统计
    origin_stats = serializers.DictField()
    
    # 按审核人员统计
    reviewer_stats = serializers.DictField()
    
    # 时间统计
    daily_stats = serializers.ListField()
    weekly_stats = serializers.ListField()
    monthly_stats = serializers.ListField()


class MeteoriteSearchSerializer(serializers.Serializer):
    """陨石搜索序列化器"""
    
    query = serializers.CharField(max_length=200, required=False, allow_blank=True)
    classification = serializers.CharField(max_length=100, required=False, allow_blank=True)
    origin = serializers.CharField(max_length=100, required=False, allow_blank=True)
    discovery_location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    
    # 置信度范围
    min_confidence = serializers.FloatField(min_value=0.0, max_value=1.0, required=False)
    max_confidence = serializers.FloatField(min_value=0.0, max_value=1.0, required=False)
    
    # 日期范围
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    
    # 排序
    ordering = serializers.CharField(max_length=50, required=False)
    
    # 分页
    page = serializers.IntegerField(min_value=1, required=False, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False, default=20)
    
    def validate(self, attrs):  # 修复参数名称为attrs以匹配基类方法
        # 验证置信度范围
        min_conf = attrs.get('min_confidence')
        max_conf = attrs.get('max_confidence')
        
        if min_conf is not None and max_conf is not None:
            if min_conf > max_conf:
                raise serializers.ValidationError('最小置信度不能大于最大置信度')
        
        # 验证日期范围
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError('开始日期不能晚于结束日期')
        
        return attrs