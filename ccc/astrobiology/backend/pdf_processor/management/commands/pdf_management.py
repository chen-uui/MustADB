"""
PDF文件管理综合命令
整合了多个PDF管理相关的功能：
- PDF文件同步
- PDF文件验证
- 清理无效PDF
- 刷新PDF元数据
- UUID同步
- 向量状态检查
"""

import os
import time
import logging
from pathlib import Path
from typing import List
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateDocumentProcessor
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'PDF文件管理综合命令'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['sync', 'validate', 'clean', 'refresh', 'uuid-sync', 'vector-status', 'all'],
            default='all',
            help='选择要执行的操作'
        )
        parser.add_argument(
            '--watch',
            action='store_true',
            help='持续监控文件夹变化（仅用于sync）'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=30,
            help='监控间隔时间(秒)，默认30秒'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='只执行一次同步（仅用于sync）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅检查而不执行修改操作',
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='执行删除操作（用于clean）'
        )
        parser.add_argument(
            '--min-pages',
            type=int,
            default=1,
            help='最小页数阈值'
        )
        parser.add_argument(
            '--min-chars',
            type=int,
            default=None,
            help='最小字符数阈值'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='限制处理文档数量'
        )
        parser.add_argument(
            '--category',
            type=str,
            default=None,
            help='按类别过滤'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        self.stdout.write(self.style.SUCCESS('🚀 开始PDF文件管理...'))
        
        if action in ['all', 'sync']:
            self.sync_pdfs(options)
        
        if action in ['all', 'validate']:
            self.validate_pdfs(options)
            
        if action in ['all', 'clean']:
            self.clean_invalid_pdfs(options)
            
        if action in ['all', 'refresh']:
            self.refresh_metadata(options)
            
        if action in ['all', 'uuid-sync']:
            self.uuid_sync(options)
            
        if action in ['all', 'vector-status']:
            self.vector_status(options)
            
        self.stdout.write(self.style.SUCCESS('[成功] PDF文件管理完成！'))

    def sync_pdfs(self, options):
        """同步PDF文件"""
        self.stdout.write(self.style.SUCCESS('[恢复] 开始同步PDF文件...'))
        
        self.pdf_dir = Path(settings.BASE_DIR).parent / 'pdfs'
        
        if options['once']:
            self.sync_once()
        elif options['watch']:
            self.watch_folder(options['interval'])
        else:
            self.sync_once()

    def sync_once(self):
        """执行一次同步"""
        try:
            if not self.pdf_dir.exists():
                self.stdout.write(self.style.ERROR(f'[失败] PDF目录不存在: {self.pdf_dir}'))
                return
            
            # 扫描PDF文件
            pdf_files = list(self.pdf_dir.rglob('*.pdf'))
            self.stdout.write(f'📁 发现 {len(pdf_files)} 个PDF文件')
            
            added_count = 0
            updated_count = 0
            
            for pdf_file in pdf_files:
                try:
                    relative_path = pdf_file.relative_to(self.pdf_dir)
                    
                    # 检查文件是否已存在
                    doc, created = PDFDocument.objects.get_or_create(
                        filename=pdf_file.name,
                        defaults={
                            'file_path': str(pdf_file),
                            'title': pdf_file.stem,
                            'category': str(relative_path.parent) if relative_path.parent != Path('.') else 'default',
                            'file_size': pdf_file.stat().st_size,
                            'upload_date': timezone.now()
                        }
                    )
                    
                    if created:
                        added_count += 1
                        self.stdout.write(f'➕ 新增: {pdf_file.name}')
                    else:
                        # 更新文件信息
                        if doc.file_size != pdf_file.stat().st_size:
                            doc.file_size = pdf_file.stat().st_size
                            doc.save()
                            updated_count += 1
                            self.stdout.write(f'[恢复] 更新: {pdf_file.name}')
                            
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'[失败] 处理文件失败 {pdf_file}: {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'[成功] 同步完成: 新增 {added_count}, 更新 {updated_count}'))
            
        except Exception as e:
            logger.error(f"同步PDF文件失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'[失败] 同步失败: {str(e)}'))

    def watch_folder(self, interval):
        """监控文件夹变化"""
        self.stdout.write(f'👀 开始监控PDF文件夹，间隔 {interval} 秒...')
        self.stdout.write('按 Ctrl+C 停止监控')
        
        try:
            while True:
                self.sync_once()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS('\n[成功] 监控已停止'))

    def validate_pdfs(self, options):
        """验证PDF文件"""
        self.stdout.write(self.style.SUCCESS('🔍 开始验证PDF文件...'))
        
        dry_run = options['dry_run']
        
        # 获取所有文档
        documents = PDFDocument.objects.all()
        total_docs = documents.count()
        
        corrupted_count = 0
        fixed_count = 0
        errors = []
        
        for i, doc in enumerate(documents, 1):
            self.stdout.write(f"正在检查 {i}/{total_docs}: {doc.filename}")
            
            try:
                # 检查文件是否存在
                if not os.path.exists(doc.file_path):
                    self.stdout.write(self.style.WARNING(f"  文件不存在: {doc.file_path}"))
                    if not dry_run:
                        doc.delete()
                        fixed_count += 1
                    continue
                
                # 验证PDF文件
                try:
                    pdf_doc = fitz.open(doc.file_path)
                    page_count = len(pdf_doc)
                    pdf_doc.close()
                    
                    # 更新页数信息
                    if doc.page_count != page_count:
                        doc.page_count = page_count
                        if not dry_run:
                            doc.save()
                            
                except Exception as pdf_error:
                    self.stdout.write(self.style.ERROR(f"  PDF损坏: {pdf_error}"))
                    corrupted_count += 1
                    errors.append(f"{doc.filename}: {pdf_error}")
                    
                    if not dry_run:
                        doc.delete()
                        fixed_count += 1
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  检查失败: {e}"))
                errors.append(f"{doc.filename}: {e}")
        
        # 输出统计信息
        self.stdout.write(self.style.SUCCESS(f'\n[统计] 验证完成:'))
        self.stdout.write(f'  总文档数: {total_docs}')
        self.stdout.write(f'  损坏文档: {corrupted_count}')
        if not dry_run:
            self.stdout.write(f'  已修复: {fixed_count}')
        else:
            self.stdout.write(f'  需修复: {corrupted_count}')
        
        if errors:
            self.stdout.write(self.style.WARNING('\n[警告] 错误详情:'))
            for error in errors[:10]:  # 只显示前10个错误
                self.stdout.write(f'  {error}')

    def clean_invalid_pdfs(self, options):
        """清理无效PDF"""
        self.stdout.write(self.style.SUCCESS('🧹 开始清理无效PDF...'))
        
        apply_changes = options['apply']
        min_pages = options['min_pages']
        min_chars = options['min_chars']
        limit = options['limit']
        category = options['category']
        
        # 构建查询
        queryset = PDFDocument.objects.all()
        if category:
            queryset = queryset.filter(category=category)
        if limit:
            queryset = queryset[:limit]
        
        invalid_docs = []
        
        for doc in queryset:
            is_invalid, info = self.is_pdf_invalid(doc.file_path, min_pages, min_chars)
            if is_invalid:
                invalid_docs.append((doc, info))
        
        self.stdout.write(f'🔍 发现 {len(invalid_docs)} 个无效PDF文档')
        
        if not invalid_docs:
            self.stdout.write(self.style.SUCCESS('[成功] 没有发现无效PDF文档'))
            return
        
        # 显示无效文档信息
        for doc, info in invalid_docs:
            reasons = ', '.join(info['reason'])
            self.stdout.write(f'[失败] {doc.filename}: {reasons}')
        
        if apply_changes:
            # 执行删除
            with transaction.atomic():
                for doc, info in invalid_docs:
                    doc.delete()
                    self.stdout.write(f'🗑️ 已删除: {doc.filename}')
            
            self.stdout.write(self.style.SUCCESS(f'[成功] 已清理 {len(invalid_docs)} 个无效PDF文档'))
        else:
            self.stdout.write(self.style.WARNING('[警告] 这是预览模式，使用 --apply 执行实际删除'))

    def is_pdf_invalid(self, file_path: str, min_pages: int, min_chars: int = None) -> tuple[bool, dict]:
        """检查PDF是否无效"""
        info = {
            "exists": False,
            "open_ok": False,
            "pages": 0,
            "chars": 0,
            "reason": []
        }

        try:
            p = Path(file_path)
            if not p.exists():
                info["reason"].append("not_found")
                return True, info
            info["exists"] = True

            # 基础文件校验
            try:
                size_bytes = p.stat().st_size
                if size_bytes < 4096:  # 小于4KB
                    info["reason"].append(f"too_small:{size_bytes}")
                    return True, info
                
                with open(p, 'rb') as f:
                    head = f.read(2048)
                    head_lower = head.lower()
                    
                    # 检查PDF魔数
                    if not head.startswith(b'%PDF'):
                        info["reason"].append("invalid_header")
                        return True, info
                    
                    # 检查HTML伪装
                    if b'<html' in head_lower or b'<body' in head_lower:
                        info["reason"].append("html_disguised")
                        return True, info
                        
            except Exception as e:
                info["reason"].append(f"read_error:{e}")
                return True, info

            # PDF结构校验
            try:
                import fitz
                pdf_doc = fitz.open(file_path)
                page_count = len(pdf_doc)
                info["pages"] = page_count
                info["open_ok"] = True
                
                if page_count < min_pages:
                    info["reason"].append(f"too_few_pages:{page_count}")
                    pdf_doc.close()
                    return True, info
                
                # 字符数检查（如果指定）
                if min_chars is not None:
                    text_content = ""
                    for page_num in range(min(3, page_count)):  # 只检查前3页
                        page = pdf_doc[page_num]
                        text_content += page.get_text()
                    
                    char_count = len(text_content.strip())
                    info["chars"] = char_count
                    
                    if char_count < min_chars:
                        info["reason"].append(f"too_few_chars:{char_count}")
                        pdf_doc.close()
                        return True, info
                
                pdf_doc.close()
                
            except Exception as e:
                info["reason"].append(f"pdf_error:{e}")
                return True, info

            return False, info
            
        except Exception as e:
            info["reason"].append(f"unexpected_error:{e}")
            return True, info

    def refresh_metadata(self, options):
        """刷新PDF元数据"""
        self.stdout.write(self.style.SUCCESS('[恢复] 开始刷新PDF元数据...'))
        
        documents = PDFDocument.objects.all()
        updated_count = 0
        
        for doc in documents:
            try:
                if os.path.exists(doc.file_path):
                    # 更新文件大小
                    file_size = Path(doc.file_path).stat().st_size
                    if doc.file_size != file_size:
                        doc.file_size = file_size
                        doc.save()
                        updated_count += 1
                        self.stdout.write(f'[恢复] 更新元数据: {doc.filename}')
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[失败] 更新失败 {doc.filename}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'[成功] 元数据刷新完成，更新了 {updated_count} 个文档'))

    def uuid_sync(self, options):
        """UUID同步"""
        self.stdout.write(self.style.SUCCESS('[恢复] 开始UUID同步...'))
        
        documents = PDFDocument.objects.filter(uuid__isnull=True)
        updated_count = 0
        
        for doc in documents:
            try:
                import uuid
                doc.uuid = uuid.uuid4()
                doc.save()
                updated_count += 1
                self.stdout.write(f'🆔 添加UUID: {doc.filename}')
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'[失败] UUID同步失败 {doc.filename}: {e}'))
        
        self.stdout.write(self.style.SUCCESS(f'[成功] UUID同步完成，更新了 {updated_count} 个文档'))

    def vector_status(self, options):
        """检查向量状态"""
        self.stdout.write(self.style.SUCCESS('[统计] 检查向量状态...'))
        
        try:
            from pdf_processor.services import VectorSearchService
            service = VectorSearchService()
            
            # 获取向量数据库统计
            count = service.collection.count()
            self.stdout.write(f'📈 向量数据库文档数: {count}')
            
            # 获取数据库文档数
            db_count = PDFDocument.objects.count()
            self.stdout.write(f'[统计] 数据库文档数: {db_count}')
            
            if count != db_count:
                self.stdout.write(self.style.WARNING(f'[警告] 数据不一致: 向量库({count}) vs 数据库({db_count})'))
            else:
                self.stdout.write(self.style.SUCCESS('[成功] 数据一致'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[失败] 状态检查失败: {e}'))