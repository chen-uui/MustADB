import os
import django
from django.core.management.base import BaseCommand
from django.utils import timezone
from pdf_processor.models import PDFDocument
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '验证所有PDF文件的有效性，清理损坏的文件'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅检查而不删除文件',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS('开始验证PDF文件...'))
        
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
                        doc.save()
                        
                    self.stdout.write(self.style.SUCCESS(f"  ✓ 有效PDF文件 ({page_count} 页)"))
                    
                except Exception as e:
                    corrupted_count += 1
                    self.stdout.write(self.style.ERROR(f"  ✗ 损坏的PDF文件: {str(e)}"))
                    
                    if not dry_run:
                        try:
                            # 删除损坏的文件
                            if os.path.exists(doc.file_path):
                                os.remove(doc.file_path)
                                self.stdout.write(self.style.WARNING(f"    已删除损坏文件"))
                            
                            # 删除数据库记录
                            doc.delete()
                            self.stdout.write(self.style.WARNING(f"    已删除数据库记录"))
                            fixed_count += 1
                            
                        except Exception as delete_error:
                            errors.append(f"删除失败 {doc.filename}: {str(delete_error)}")
                            self.stdout.write(self.style.ERROR(f"    删除失败: {str(delete_error)}"))
                    
            except Exception as e:
                errors.append(f"检查失败 {doc.filename}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"  检查失败: {str(e)}"))
        
        # 输出统计信息
        self.stdout.write(self.style.SUCCESS(f"\n验证完成！"))
        self.stdout.write(f"总文档数: {total_docs}")
        self.stdout.write(f"损坏文件: {corrupted_count}")
        self.stdout.write(f"修复数量: {fixed_count}")
        self.stdout.write(f"错误数量: {len(errors)}")
        
        if errors:
            self.stdout.write(self.style.ERROR("\n错误详情:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n注意：使用了 --dry-run 模式，未进行实际修复"))