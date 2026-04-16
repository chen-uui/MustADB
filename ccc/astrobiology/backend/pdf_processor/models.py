from django.db import models
from django.utils import timezone
from datetime import datetime
import uuid
import os
import sys

# 动态导入PDFUtils（避免Django导入问题）
try:
    from .pdf_utils import PDFUtils
    has_pdf_utils = True
except ImportError:
    has_pdf_utils = False
    PDFUtils = None

class PDFDocument(models.Model):
    """PDF文档模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255, unique=True)
    # `duplicate_of` keeps the current short-term bridge between content and
    # review actions: the child row is a fresh review request, while the
    # pointed-to row owns the canonical file and content hash.
    duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duplicate_children',
    )
    title = models.CharField(max_length=500)
    authors = models.TextField(blank=True, null=True, help_text='作者列表，用逗号分隔')
    year = models.IntegerField(blank=True, null=True, help_text='发表年份')
    journal = models.CharField(max_length=200, blank=True, null=True, help_text='期刊名称')
    doi = models.CharField(max_length=100, blank=True, null=True, help_text='DOI编号')
    file_path = models.CharField(max_length=1000)
    upload_date = models.DateTimeField(default=timezone.now)
    file_size = models.IntegerField(default=0)  # type: ignore
    page_count = models.IntegerField(default=0)  # type: ignore
    category = models.CharField(max_length=100, default='未分类')
    processed = models.BooleanField(default=False)  # type: ignore
    sha1 = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    # 兼容历史数据库中存在的非空字段（向后兼容）
    rag_extracted = models.BooleanField(default=False)  # type: ignore
    
    # 审核相关字段
    REVIEW_STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]
    review_status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='approved',  # 默认已通过（兼容旧数据，管理员上传的直接通过）
        verbose_name="审核状态"
    )
    review_notes = models.TextField(blank=True, null=True, verbose_name="审核备注")
    reviewed_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_pdfs',
        verbose_name="审核人"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")
    uploaded_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_pdfs',
        verbose_name="上传人"
    )
    
    class Meta:
        db_table = 'pdf_documents'
        ordering = ['-upload_date']
        indexes = [
            models.Index(fields=['upload_date'], name='pdf_doc_upload_date_idx'),
            models.Index(fields=['processed'], name='pdf_doc_processed_idx'),
            models.Index(fields=['category'], name='pdf_doc_category_idx'),
            models.Index(fields=['filename'], name='pdf_doc_filename_idx'),
            models.Index(fields=['review_status'], name='pdf_doc_review_status_idx'),
            models.Index(fields=['uploaded_by'], name='pdf_doc_uploaded_by_idx'),
        ]
    
    def __str__(self) -> str:
        return str(self.title) if self.title else 'Unknown Document'
    
    def save(self, *args, **kwargs):
        """保存前清理标题"""
        if self.title:
            self.title = self.clean_title(self.title)
        super().save(*args, **kwargs)
    
    def clean_title(self, title):
        """使用统一的标题清理工具"""
        if not title:
            return '未知文档'
        
        # 使用PDFUtils的清理方法（如果可用）
        if has_pdf_utils and PDFUtils:
            try:
                return PDFUtils.clean_title(title)
            except:
                pass
        
        # 备用清理逻辑
        import re
        
        # 清理UUID前缀
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\s'
        title = re.sub(uuid_pattern, '', title)
        
        # 清理.pdf后缀
        title = re.sub(r'\.pdf$', '', title, flags=re.IGNORECASE)
        
        # 清理文件名中的下划线
        title = title.replace('_', ' ')
        
        return title.strip()

class DocumentChunk(models.Model):
    """文档分块模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    page_number = models.IntegerField()
    chunk_index = models.IntegerField()
    embedding_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'document_chunks'
        ordering = ['document', 'page_number', 'chunk_index']
    
    def __str__(self) -> str:
        document_title = getattr(self.document, 'title', 'Unknown Document')
        return f"{document_title} - Page {self.page_number}, Chunk {self.chunk_index}"


class DirectProcessingResult(models.Model):
    """直接处理结果数据库模型"""
    
    # 基础信息
    document_path = models.CharField(max_length=500, verbose_name="文档路径")
    document_title = models.CharField(max_length=300, blank=True, verbose_name="文档标题")
    processing_time = models.FloatField(verbose_name="处理时间(秒)")
    confidence_score = models.FloatField(verbose_name="置信度分数")
    
    # 处理结果
    meteorite_data = models.JSONField(default=dict, verbose_name="陨石数据")
    organic_compounds = models.JSONField(default=dict, verbose_name="有机化合物数据")
    mineral_relationships = models.JSONField(default=dict, verbose_name="矿物关系数据")
    scientific_insights = models.JSONField(default=dict, verbose_name="科学洞察数据")
    
    # 验证信息
    validation_checks = models.JSONField(default=list, verbose_name="验证检查结果")
    validation_notes = models.TextField(blank=True, verbose_name="验证说明")
    
    # 系统信息
    task_id = models.UUIDField(default=uuid.uuid4, editable=False, verbose_name="任务ID")
    status = models.CharField(max_length=20, default='completed', verbose_name="处理状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = 'direct_processing_results'
        ordering = ['-created_at']
        verbose_name = "直接处理结果"
        verbose_name_plural = "直接处理结果"
    
    def __str__(self) -> str:
        created_at_str = self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else 'Unknown'  # type: ignore
        return f"DirectProcessing: {self.document_title} ({created_at_str})"
    
    def get_meteorite_name(self):
        """获取陨石名称"""
        if self.meteorite_data and isinstance(self.meteorite_data, dict):
            return self.meteorite_data.get('name', 'Unknown')
        return 'Unknown'
    
    def get_processing_summary(self):
        """获取处理摘要"""
        summary = {
            'document_title': self.document_title,
            'processing_time': self.processing_time,
            'confidence_score': self.confidence_score,
            'status': self.status,
            'meteorite_name': self.get_meteorite_name(),
            'has_organic_compounds': bool(self.organic_compounds),
            'has_scientific_insights': bool(self.scientific_insights),
            'validation_passed': len([check for check in (self.validation_checks or []) if isinstance(check, dict) and check.get('passed', False)])  # type: ignore
        }
        return summary


class ProcessingTask(models.Model):
    """直接处理任务模型"""
    
    # 基础信息
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name="任务ID")
    document_path = models.CharField(max_length=500, verbose_name="文档路径")
    document_title = models.CharField(max_length=300, blank=True, verbose_name="文档标题")
    
    # 处理选项
    options = models.JSONField(default=dict, verbose_name="处理选项")
    
    # 状态信息
    status = models.CharField(max_length=20, default='pending', verbose_name="处理状态")
    progress = models.FloatField(default=0.0, verbose_name="处理进度")  # type: ignore
    current_step = models.CharField(max_length=200, blank=True, verbose_name="当前步骤")
    
    # 错误信息
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    
    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    
    # 用户信息
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="创建者")
    
    class Meta:
        db_table = 'processing_tasks'
        ordering = ['-created_at']
        verbose_name = "处理任务"
        verbose_name_plural = "处理任务"
    
    def __str__(self) -> str:
        return f"Task: {self.task_id} - {self.document_title}"
    
    def start_processing(self):
        """开始处理"""
        self.status = 'processing'
        self.started_at = datetime.now()
        self.save()
    
    def complete_processing(self, result):
        """完成处理"""
        self.status = 'completed'
        self.progress = 100.0
        self.completed_at = datetime.now()
        self.save()
    
    def fail_processing(self, error_message):
        """处理失败"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = datetime.now()
        self.save()


class ProcessingLog(models.Model):
    """处理日志模型"""
    
    task = models.ForeignKey(ProcessingTask, on_delete=models.CASCADE, related_name='logs', verbose_name="处理任务")
    level = models.CharField(max_length=20, choices=[
        ('DEBUG', '调试'),
        ('INFO', '信息'),
        ('WARNING', '警告'),
        ('ERROR', '错误'),
    ], default='INFO', verbose_name="日志级别")
    message = models.TextField(verbose_name="日志消息")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="时间戳")
    
    class Meta:
        db_table = 'processing_logs'
        ordering = ['-timestamp']
        verbose_name = "处理日志"
        verbose_name_plural = "处理日志"
    
    def __str__(self) -> str:
        task_id = getattr(self.task, 'task_id', 'Unknown')
        message_preview = str(self.message)[:50] if self.message else ''
        return f"Log: {task_id} - {self.level} - {message_preview}"


class ProcessingStatistics(models.Model):
    """处理统计模型"""
    
    date = models.DateField(unique=True, help_text="统计日期")
    total_documents = models.IntegerField(default=0, help_text="总文档数")  # type: ignore
    successful_documents = models.IntegerField(default=0, help_text="成功处理文档数")  # type: ignore
    failed_documents = models.IntegerField(default=0, help_text="失败处理文档数")  # type: ignore
    avg_processing_time = models.FloatField(default=0.0, help_text="平均处理时间（秒）")  # type: ignore
    avg_confidence_score = models.FloatField(default=0.0, help_text="平均置信度分数")  # type: ignore
    total_meteorites = models.IntegerField(default=0, help_text="总陨石数")  # type: ignore
    total_organic_compounds = models.IntegerField(default=0, help_text="总有机化合物数")  # type: ignore
    total_insights = models.IntegerField(default=0, help_text="总科学洞察数")  # type: ignore
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pdf_processor_processingstatistics'
        verbose_name = '处理统计'
        verbose_name_plural = '处理统计'
        ordering = ['-date']
    
    def __str__(self) -> str:
        return f"ProcessingStatistics for {self.date} - {self.total_documents} documents"
