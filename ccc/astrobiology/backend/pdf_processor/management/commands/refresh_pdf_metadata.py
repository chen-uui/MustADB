from django.core.management.base import BaseCommand
from ...models import PDFDocument
from ...pdf_utils import PDFUtils
import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Re-extract metadata from source PDFs and update PDFDocument fields (title/authors/year/journal/doi). Optionally rename files to match paper titles."

    def add_arguments(self, parser):
        parser.add_argument('--id', type=str, help='Only refresh a specific document UUID')
        parser.add_argument('--limit', type=int, default=1000)
        parser.add_argument('--rename-files', action='store_true', help='Rename PDF files to match paper titles after metadata refresh')

    def handle(self, *args, **options):
        qs = PDFDocument.objects.all().order_by('-upload_date')
        if options.get('id'):
            qs = qs.filter(id=options['id'])
        if options.get('limit'):
            qs = qs[: options['limit']]

        updated = 0
        renamed = 0
        
        for doc in qs:
            try:
                result = PDFUtils.extract_text_and_metadata(doc.file_path)
                if not result.get('success'):
                    logger.warning(f"Skip {doc.id}, extract failed: {result.get('error')}")
                    continue
                meta = result.get('metadata', {}) or {}
                # 仅在有值时覆盖，避免覆盖成空
                title = meta.get('title') or doc.title
                authors = meta.get('authors') or doc.authors
                year = int(meta.get('year')) if meta.get('year') and str(meta.get('year')).isdigit() else doc.year
                journal = meta.get('journal') or doc.journal
                doi = meta.get('doi') or doc.doi

                changed = False
                if title and title != doc.title:
                    doc.title = title
                    changed = True
                if authors and authors != doc.authors:
                    doc.authors = authors
                    changed = True
                if year and year != doc.year:
                    doc.year = year
                    changed = True
                if journal and journal != doc.journal:
                    doc.journal = journal
                    changed = True
                if doi and doi != doc.doi:
                    doc.doi = doi
                    changed = True

                # 如果启用了重命名选项，且标题有效，重命名文件
                if options.get('rename_files') and title:
                    rename_result = self._rename_file_to_title(doc, title)
                    if rename_result:
                        renamed += 1
                        changed = True

                if changed:
                    doc.save()
                    updated += 1
            except Exception as e:
                logger.warning(f"Failed refresh {doc.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Metadata refresh done: updated={updated}, renamed={renamed}"))

    def _rename_file_to_title(self, doc: PDFDocument, title: str) -> bool:
        """
        将PDF文件重命名为论文标题
        
        Args:
            doc: PDFDocument实例
            title: 论文标题
            
        Returns:
            是否成功重命名
        """
        try:
            # 检查标题是否有效（不是文档ID或通用标题）
            if (not title or 
                title == "Academic Paper" or 
                title == "Untitled Document" or
                PDFUtils._is_document_id(title)):
                return False
            
            current_path = Path(doc.file_path)
            if not current_path.exists():
                logger.warning(f"文件不存在，无法重命名: {doc.file_path}")
                return False
            
            # 生成安全的文件名
            safe_filename = self._sanitize_filename(title)
            if not safe_filename:
                return False
            
            new_filename = f"{safe_filename}.pdf"
            new_path = current_path.parent / new_filename
            
            # 如果新文件名和当前文件名相同，不需要重命名
            if current_path.name == new_filename:
                return False
            
            # 如果目标文件已存在，添加序号
            counter = 1
            original_new_path = new_path
            while new_path.exists():
                new_filename = f"{safe_filename}_{counter}.pdf"
                new_path = current_path.parent / new_filename
                counter += 1
                if counter > 100:  # 防止无限循环
                    logger.warning(f"无法生成唯一文件名: {original_new_path}")
                    return False
            
            # 重命名文件
            current_path.rename(new_path)
            
            # 更新数据库中的filename和file_path
            doc.filename = new_filename
            doc.file_path = str(new_path)
            
            logger.info(f"文件重命名成功: {current_path.name} -> {new_filename}")
            return True
            
        except Exception as e:
            logger.error(f"重命名文件失败 {doc.file_path}: {e}", exc_info=True)
            return False
    
    def _sanitize_filename(self, title: str, max_length: int = 200) -> str:
        """
        将标题转换为安全的文件名
        
        Args:
            title: 原始标题
            max_length: 最大长度
            
        Returns:
            安全的文件名（不含扩展名）
        """
        if not title:
            return ""
        
        # 移除或替换Windows/Unix文件系统不支持的字符
        # Windows不支持: < > : " / \ | ? *
        # 保留常用标点但限制长度
        
        # 移除或替换非法字符
        safe = re.sub(r'[<>:"/\\|?*]', '-', title)
        
        # 移除控制字符
        safe = re.sub(r'[\x00-\x1f\x7f]', '', safe)
        
        # 移除前导/尾随空格和点
        safe = safe.strip(' .')
        
        # 限制连续的点或空格
        safe = re.sub(r'\.{2,}', '.', safe)
        safe = re.sub(r'\s+', ' ', safe)
        
        # 限制长度
        if len(safe) > max_length:
            safe = safe[:max_length].rstrip()
        
        # 确保不为空
        if not safe or len(safe.strip()) < 3:
            return ""
        
        return safe


