"""
陨石搜索模型
定义陨石数据的数据库结构
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import json

class Meteorite(models.Model):
    """陨石模型"""
    
    # 基本信息
    name = models.CharField(max_length=200, verbose_name="陨石名称", help_text="陨石的官方名称或编号")
    classification = models.CharField(max_length=100, verbose_name="分类", help_text="陨石的科学分类")
    discovery_location = models.CharField(max_length=300, verbose_name="发现地点", help_text="陨石的发现或收集地点")
    origin = models.CharField(max_length=200, verbose_name="来源", help_text="推测的母体来源")
    
    # 有机化合物信息（JSON字段）
    organic_compounds = models.JSONField(
        default=dict, 
        verbose_name="有机化合物", 
        help_text="检测到的有机化合物详细信息"
    )
    
    # 污染排除方法
    contamination_exclusion_method = models.TextField(
        verbose_name="污染排除方法", 
        help_text="用于排除地球污染的方法和程序"
    )
    
    # 参考文献（JSON字段）
    references = models.JSONField(
        default=list, 
        verbose_name="参考文献", 
        help_text="相关的科学文献引用"
    )
    
    # 系统字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")  # type: ignore
    
    # 人工审核相关字段
    review_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待审核'),
            ('approved', '已批准'),
            ('rejected', '已拒绝'),
            ('needs_revision', '需要修订')
        ],
        default='pending',
        verbose_name="审核状态"
    )
    
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_meteorites',
        verbose_name="审核人"
    )
    
    review_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="审核日期"
    )
    
    review_notes = models.TextField(
        blank=True,
        verbose_name="审核备注",
        help_text="审核人员的备注和建议"
    )
    
    # 数据质量评分
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        default=0.0,  # type: ignore
        verbose_name="置信度分数",
        help_text="数据提取和验证的置信度分数 (0.0-1.0)"
    )
    
    # 数据来源信息
    extraction_source = models.CharField(
        max_length=50,
        choices=[
            ('manual', '手动录入'),
            ('rag_extraction', 'RAG自动提取'),
            ('import', '批量导入')
        ],
        default='manual',
        verbose_name="数据来源"
    )
    
    extraction_metadata = models.JSONField(
        default=dict,
        verbose_name="提取元数据",
        help_text="数据提取过程的详细信息"
    )
    
    class Meta:
        db_table = 'meteorites'
        verbose_name = "陨石"
        verbose_name_plural = "陨石"
        ordering = ['-created_at']
        
        # 索引优化
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['classification']),
            models.Index(fields=['discovery_location']),
            models.Index(fields=['origin']),
            models.Index(fields=['review_status']),
            models.Index(fields=['extraction_source']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
            # 复合索引
            models.Index(fields=['review_status', 'created_at']),
            models.Index(fields=['extraction_source', 'review_status']),
        ]
        
        # 约束
        constraints = [
            models.CheckConstraint(
                check=models.Q(confidence_score__gte=0.0) & models.Q(confidence_score__lte=1.0),
                name='valid_confidence_score'
            )
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.classification})"
    
    def get_organic_compounds_summary(self):
        """获取有机化合物摘要"""
        if not self.organic_compounds:
            return "无有机化合物数据"
        
        # 处理organic_compounds可能是list或dict的情况
        if isinstance(self.organic_compounds, list):
            if self.organic_compounds:
                return f"共{len(self.organic_compounds)}种有机化合物"
            else:
                return "无有机化合物数据"
        
        # 处理dict格式
        if isinstance(self.organic_compounds, dict):
            summary = []
            for category, compounds in self.organic_compounds.items():
                if isinstance(compounds, list) and compounds:
                    summary.append(f"{category}: {len(compounds)}种")
                elif isinstance(compounds, str) and compounds:
                    summary.append(f"{category}: {compounds}")
            
            return "; ".join(summary) if summary else "无有机化合物数据"
        
        return "无有机化合物数据"
    
    def get_references_count(self):
        """获取参考文献数量"""
        if isinstance(self.references, list):
            return len(self.references)
        return 0
    
    def is_pending_review(self):
        """是否待审核"""
        return self.review_status == 'pending'
    
    def is_approved(self):
        """是否已批准"""
        return self.review_status == 'approved'
    
    def needs_review(self):
        """是否需要审核"""
        return self.review_status in ['pending', 'needs_revision']


class MeteoriteReviewLog(models.Model):
    """陨石审核日志"""
    
    meteorite = models.ForeignKey(
        Meteorite,
        on_delete=models.CASCADE,
        related_name='review_logs',
        verbose_name="陨石"
    )
    
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="审核人"
    )
    
    action = models.CharField(
        max_length=20,
        choices=[
            ('submitted', '提交审核'),
            ('approved', '批准'),
            ('rejected', '拒绝'),
            ('revision_requested', '要求修订'),
            ('resubmitted', '重新提交')
        ],
        verbose_name="操作"
    )
    
    previous_status = models.CharField(
        max_length=20,
        verbose_name="之前状态"
    )
    
    new_status = models.CharField(
        max_length=20,
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
        default=dict,
        verbose_name="审核详情",
        help_text="详细的审核信息和建议"
    )
    
    class Meta:
        db_table = 'meteorite_review_logs'
        verbose_name = "陨石审核日志"
        verbose_name_plural = "陨石审核日志"
        ordering = ['-timestamp']
        
        indexes = [
            models.Index(fields=['meteorite', 'timestamp']),
            models.Index(fields=['reviewer', 'timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self) -> str:
        meteorite_name = getattr(self.meteorite, 'name', 'Unknown Meteorite')
        reviewer_username = getattr(self.reviewer, 'username', 'Unknown Reviewer')
        return f"{meteorite_name} - {self.action} by {reviewer_username}"


class DataExtractionTask(models.Model):
    """数据提取任务"""
    
    task_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="任务ID"
    )
    
    task_type = models.CharField(
        max_length=30,
        choices=[
            ('single_document', '单文档提取'),
            ('batch_documents', '批量文档提取'),
            ('query_based', '基于查询的提取')
        ],
        verbose_name="任务类型"
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待处理'),
            ('running', '运行中'),
            ('paused', '已暂停'),
            ('completed', '已完成'),
            ('failed', '失败'),
            ('cancelled', '已取消')
        ],
        default='pending',
        verbose_name="状态"
    )
    
    # 任务参数
    parameters = models.JSONField(
        default=dict,
        verbose_name="任务参数"
    )
    
    # 执行结果
    results = models.JSONField(
        default=dict,
        verbose_name="执行结果"
    )
    
    # 统计信息
    total_documents = models.IntegerField(
        default=0,  # type: ignore
        verbose_name="总文档数"
    )
    
    processed_documents = models.IntegerField(
        default=0,  # type: ignore
        verbose_name="已处理文档数"
    )
    
    successful_extractions = models.IntegerField(
        default=0,  # type: ignore
        verbose_name="成功提取数"
    )
    
    failed_extractions = models.IntegerField(
        default=0,  # type: ignore
        verbose_name="失败提取数"
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="开始时间"
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="完成时间"
    )
    
    # 创建者
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="创建者"
    )
    
    class Meta:
        db_table = 'data_extraction_tasks'
        verbose_name = "数据提取任务"
        verbose_name_plural = "数据提取任务"
        ordering = ['-created_at']
        
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['task_type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        return f"Task {self.task_id} - {self.task_type} ({self.status})"
    
    def get_progress_percentage(self) -> float:
        """获取进度百分比"""
        if self.total_documents == 0:
            return 0.0
        processed = self.processed_documents
        total = self.total_documents
        # 确保转换为Python原生类型
        processed_val = processed if isinstance(processed, (int, float)) else int(processed)  # type: ignore
        total_val = total if isinstance(total, (int, float)) else int(total)  # type: ignore
        return (float(processed_val) / float(total_val)) * 100.0
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.processed_documents == 0:
            return 0.0
        successful = self.successful_extractions
        processed = self.processed_documents
        # 确保转换为Python原生类型
        successful_val = successful if isinstance(successful, (int, float)) else int(successful)  # type: ignore
        processed_val = processed if isinstance(processed, (int, float)) else int(processed)  # type: ignore
        return (float(successful_val) / float(processed_val)) * 100.0
    
    def has_checkpoint(self):
        """检查任务是否有检查点"""
        try:
            from pdf_processor.task_checkpoint_manager import checkpoint_manager
            stats = checkpoint_manager.get_checkpoint_stats(str(self.task_id))
            return stats.get('has_checkpoints', False)
        except Exception:
            return False
    
    def can_resume(self):
        """检查任务是否可以从检查点恢复"""
        return self.status in ['paused', 'failed'] and self.has_checkpoint()
    
    def get_checkpoint_count(self):
        """获取检查点数量"""
        try:
            from pdf_processor.task_checkpoint_manager import checkpoint_manager
            stats = checkpoint_manager.get_checkpoint_stats(str(self.task_id))
            return stats.get('checkpoint_count', 0)
        except Exception:
            return 0


class SingleTaskExtractionSession(models.Model):
    """单任务提取会话模型 - 持久化存储"""
    
    session_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="会话ID"
    )
    
    keywords = models.JSONField(
        default=list,
        verbose_name="搜索关键词"
    )
    
    threshold = models.FloatField(
        default=0.5,  # type: ignore
        verbose_name="相关性阈值"
    )
    
    sort_by = models.CharField(
        max_length=20,
        default='score_desc',
        verbose_name="排序方式"
    )
    
    status = models.CharField(
        max_length=20,
        default='searching',
        verbose_name="状态"
    )
    
    # 所有片段数据（序列化存储）
    segments_data = models.JSONField(
        default=dict,
        verbose_name="片段数据"
    )
    
    segment_order = models.JSONField(
        default=list,
        verbose_name="片段顺序"
    )
    
    # 队列数据
    queue_data = models.JSONField(
        default=dict,
        verbose_name="队列数据"
    )
    
    # 聚合结果
    aggregated_results = models.JSONField(
        default=dict,
        verbose_name="聚合结果"
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )
    
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="最后更新时间"
    )
    
    # 过期时间（用于自动清理）
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="过期时间"
    )
    
    class Meta:
        db_table = 'single_task_extraction_sessions'
        verbose_name = "单任务提取会话"
        verbose_name_plural = "单任务提取会话"
        ordering = ['-last_updated']
        
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['status']),
            models.Index(fields=['last_updated']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self) -> str:
        return f"Session {self.session_id} - {self.status}"
    
    def is_expired(self):
        """检查会话是否过期"""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False