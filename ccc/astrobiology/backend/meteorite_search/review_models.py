"""
新的陨石审核流程数据库模型
实现三层数据存储：待审核 -> 已批准 -> 回收站
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from typing import Dict, Any, List, Union, Optional
import json


class BaseMeteoriteModel(models.Model):
    """陨石数据基础模型（抽象类）"""
    
    # 基本信息
    name = models.CharField(max_length=200, verbose_name="陨石名称", help_text="陨石的官方名称或编号", blank=True, default="Unknown")
    classification = models.CharField(max_length=100, verbose_name="分类", help_text="陨石的科学分类", blank=True, default="Unknown")
    discovery_location = models.CharField(max_length=300, verbose_name="发现地点", help_text="陨石的发现或收集地点", blank=True, default="Unknown")
    origin = models.CharField(max_length=200, verbose_name="来源", help_text="推测的母体来源", blank=True, default="Unknown")
    
    # 有机化合物信息（JSON字段）
    organic_compounds = models.JSONField(
        default=list,  # type: ignore
        blank=True,
        verbose_name="有机化合物", 
        help_text="检测到的有机化合物详细信息"
    )
    
    # 污染排除方法
    contamination_exclusion_method = models.TextField(
        verbose_name="污染排除方法", 
        help_text="用于排除地球污染的方法和程序",
        blank=True,
        default="Not specified"
    )
    
    # 参考文献（JSON字段）
    references = models.JSONField(
        default=list,  # type: ignore
        verbose_name="参考文献", 
        help_text="相关的科学文献引用",
        blank=True
    )
    
    # 数据提取相关字段
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="置信度分数",
        help_text="AI提取数据的置信度评分 (0.0-1.0)"
    )
    
    extraction_source = models.CharField(
        max_length=20,
        choices=[
            ('pdf', 'PDF文档'),
            ('manual', '手动输入'),
            ('api', 'API导入'),
            ('batch', '批量导入')
        ],
        default='pdf',
        verbose_name="数据来源"
    )
    
    extraction_metadata = models.JSONField(
        default=dict,  # type: ignore
        blank=True,
        verbose_name="提取元数据",
        help_text="数据提取过程的详细信息"
    )
    
    # 系统字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        abstract = True
    
    def get_organic_compounds_summary(self) -> str:
        """获取有机化合物摘要"""
        if not self.organic_compounds:
            return "无有机化合物信息"
        
        # 明确类型转换以避免Pyright错误
        compounds = self.organic_compounds
        if isinstance(compounds, dict):
            compound_types: List[str] = list(compounds.keys())
        elif isinstance(compounds, list):
            compound_types = [str(item) for item in compounds]
        else:
            compound_types = []
            
        if len(compound_types) == 0:
            return "无有机化合物"
        elif len(compound_types) <= 3:
            return f"包含: {', '.join(compound_types)}"
        else:
            return f"包含: {', '.join(compound_types[:3])} 等 {len(compound_types)} 种化合物"
    
    def get_references_count(self) -> int:
        """获取参考文献数量"""
        if isinstance(self.references, list):
            return len(self.references)
        return 0


class PendingMeteorite(BaseMeteoriteModel):
    """待审核陨石数据表"""
    
    REVIEW_STATUS_CHOICES = [
        ('pending', '待审核'),
        ('under_review', '审核中'),
        ('needs_revision', '需要修订'),
    ]
    
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='pending',
        verbose_name="审核状态"
    )
    
    # 审核相关字段
    assigned_reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_pending_meteorites',
        verbose_name="指定审核人"
    )
    
    review_notes = models.TextField(
        blank=True,
        verbose_name="审核备注",
        help_text="审核人员的备注和建议"
    )
    
    priority = models.IntegerField(
        default=1,  # type: ignore
        choices=[
            (1, '低优先级'),
            (2, '中优先级'),
            (3, '高优先级'),
            (4, '紧急')
        ],
        verbose_name="审核优先级"
    )
    
    class Meta(BaseMeteoriteModel.Meta):  # 明确继承父类Meta
        db_table = 'pending_meteorites'
        verbose_name = "待审核陨石"
        verbose_name_plural = "待审核陨石"
        ordering = ['-priority', '-created_at']
        
        indexes = [
            models.Index(fields=['review_status']),
            models.Index(fields=['assigned_reviewer']),
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['extraction_source']),
        ]
    
    def __str__(self) -> str:
        # 使用类型注释避免Pyright错误
        status_display = getattr(self, 'get_review_status_display', lambda: self.review_status)()
        return f"{self.name} ({status_display})"


class ApprovedMeteorite(BaseMeteoriteModel):
    """已批准陨石数据表（正式数据库）"""
    
    # 审核相关字段
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_meteorites',
        verbose_name="审核人"
    )
    
    approved_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="批准时间"
    )
    
    # 原始待审核记录ID（用于追溯）
    original_pending_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="原始待审核ID"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="是否激活")  # type: ignore
    
    class Meta(BaseMeteoriteModel.Meta):  # 明确继承父类Meta
        db_table = 'approved_meteorites'
        verbose_name = "已批准陨石"
        verbose_name_plural = "已批准陨石"
        ordering = ['-approved_at']
        
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['classification']),
            models.Index(fields=['discovery_location']),
            models.Index(fields=['origin']),
            models.Index(fields=['reviewer']),
            models.Index(fields=['approved_at']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} (已批准)"


class RejectedMeteorite(BaseMeteoriteModel):
    """回收站陨石数据表"""
    
    # 拒绝相关字段
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rejected_meteorites',
        verbose_name="审核人"
    )
    
    rejected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="拒绝时间"
    )
    
    rejection_reason = models.TextField(
        verbose_name="拒绝原因",
        help_text="详细说明拒绝的原因"
    )
    
    rejection_category = models.CharField(
        max_length=50,
        choices=[
            ('data_quality', '数据质量问题'),
            ('incomplete_info', '信息不完整'),
            ('duplicate', '重复数据'),
            ('invalid_classification', '分类错误'),
            ('contamination_concern', '污染问题'),
            ('reference_issue', '参考文献问题'),
            ('user_deleted', '用户删除'),
            ('other', '其他原因')
        ],
        default='data_quality',
        verbose_name="拒绝类别"
    )
    
    # 原始待审核记录ID（用于追溯）
    original_pending_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="原始待审核ID"
    )
    
    # 是否可恢复
    can_restore = models.BooleanField(
        default=True,  # type: ignore
        verbose_name="可恢复",
        help_text="是否允许从回收站恢复此数据"
    )
    
    class Meta(BaseMeteoriteModel.Meta):  # 明确继承父类Meta
        db_table = 'rejected_meteorites'
        verbose_name = "回收站陨石"
        verbose_name_plural = "回收站陨石"
        ordering = ['-rejected_at']
        
        indexes = [
            models.Index(fields=['reviewer']),
            models.Index(fields=['rejected_at']),
            models.Index(fields=['rejection_category']),
            models.Index(fields=['can_restore']),
        ]
    
    def __str__(self) -> str:
        # 使用类型注释避免Pyright错误
        category_display = getattr(self, 'get_rejection_category_display', lambda: self.rejection_category)()
        return f"{self.name} (已拒绝 - {category_display})"


class MeteoriteReviewLogNew(models.Model):
    """陨石审核日志 - 新版本（支持三层数据流转）"""
    
    # 关联字段（支持三种类型的陨石记录）
    pending_meteorite = models.ForeignKey(
        PendingMeteorite,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='review_logs',
        verbose_name="待审核陨石"
    )
    
    approved_meteorite = models.ForeignKey(
        ApprovedMeteorite,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='review_logs',
        verbose_name="已批准陨石"
    )
    
    rejected_meteorite = models.ForeignKey(
        RejectedMeteorite,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='review_logs',
        verbose_name="回收站陨石"
    )
    
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="审核人"
    )
    
    action = models.CharField(
        max_length=30,
        choices=[
            ('submitted', '提交审核'),
            ('assigned', '分配审核人'),
            ('started_review', '开始审核'),
            ('approved', '批准'),
            ('rejected', '拒绝'),
            ('revision_requested', '要求修订'),
            ('resubmitted', '重新提交'),
            ('restored', '从回收站恢复'),
            ('permanently_deleted', '永久删除')
        ],
        verbose_name="操作"
    )
    
    previous_status = models.CharField(
        max_length=30,
        verbose_name="之前状态"
    )
    
    new_status = models.CharField(
        max_length=30,
        verbose_name="新状态"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="备注"
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="时间戳"
    )
    
    # 审核详情
    review_details = models.JSONField(
        default=dict,  # type: ignore
        verbose_name="审核详情",
        help_text="详细的审核信息和建议"
    )
    
    class Meta:
        db_table = 'meteorite_review_logs_new'
        verbose_name = "陨石审核日志"
        verbose_name_plural = "陨石审核日志"
        ordering = ['-timestamp']
        
        indexes = [
            models.Index(fields=['pending_meteorite', 'timestamp']),
            models.Index(fields=['approved_meteorite', 'timestamp']),
            models.Index(fields=['rejected_meteorite', 'timestamp']),
            models.Index(fields=['reviewer', 'timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self) -> str:
        meteorite_name = "Unknown"
        if self.pending_meteorite:
            meteorite_name = getattr(self.pending_meteorite, 'name', 'Unknown')
        elif self.approved_meteorite:
            meteorite_name = getattr(self.approved_meteorite, 'name', 'Unknown')
        elif self.rejected_meteorite:
            meteorite_name = getattr(self.rejected_meteorite, 'name', 'Unknown')
        
        # 使用类型注释避免Pyright错误
        # 通过getattr安全访问ForeignKey关联对象的属性
        reviewer_username = getattr(self.reviewer, 'username', 'Unknown') if self.reviewer else 'Unknown'
        return f"{meteorite_name} - {self.action} by {reviewer_username}"