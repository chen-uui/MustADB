"""
清理无效PDF脚本（管理命令）

判定标准（满足任一则视为无效）：
- 文件不存在或无法打开
- 页面数为0或小于最小页数阈值
- 文本提取字符数低于阈值（可选）

默认行为：dry-run 仅报告不删除；可用 --apply 执行删除。
支持 --min-pages, --min-chars, --limit, --category 过滤。
"""

import os
import logging
from pathlib import Path
from typing import List

from django.core.management.base import BaseCommand
from django.db import transaction

from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateDocumentProcessor

logger = logging.getLogger(__name__)


def is_pdf_invalid(file_path: str, min_pages: int, min_chars: int | None) -> tuple[bool, dict]:
    """检查PDF是否无效，返回(是否无效, 诊断信息)。"""
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

        # 基础文件校验：大小、魔数、HTML伪装
        try:
            size_bytes = p.stat().st_size
            if size_bytes < 4096:  # 小于4KB 基本视为无效
                info["reason"].append(f"too_small:{size_bytes}")
            with open(p, 'rb') as f:
                head = f.read(2048)
                head_lower = head.lower()
                if not head.startswith(b"%PDF"):
                    info["reason"].append("no_pdf_magic")
                # HTML/文本伪PDF
                if b"<html" in head_lower or b"<!doctype html" in head_lower:
                    info["reason"].append("html_disguised")
        except Exception as e:
            info["reason"].append(f"file_check_error:{e}")

        import fitz  # PyMuPDF
        with fitz.open(file_path) as doc:
            info["open_ok"] = True
            info["pages"] = len(doc)
            if info["pages"] < max(1, min_pages):
                info["reason"].append(f"too_few_pages:{info['pages']}")
            # 统计字符数（轻量）
            if min_chars is not None and min_chars > 0:
                sample_pages = min(info["pages"], 5)
                text_acc = []
                for i in range(sample_pages):
                    try:
                        text_acc.append(doc.load_page(i).get_text("text") or "")
                    except Exception:
                        pass
                info["chars"] = sum(len(t) for t in text_acc)
                if info["chars"] < min_chars:
                    info["reason"].append(f"too_few_chars:{info['chars']}")

        # 备选解析：有些文件PyMuPDF能开但后续解析失败，尝试用其他方法再验证
        try:
            # 使用统一的PDF处理工具进行二次验证
            from pdf_processor.pdf_utils import PDFUtils
            validation_result = PDFUtils.extract_text_and_metadata(file_path)
            if not validation_result['success']:
                info["reason"].append(f"pdf_utils_error:{validation_result.get('error', 'unknown')}")
        except Exception as e:
            info["reason"].append(f"pdf_utils_error:{e}")

    except Exception as e:
        info["reason"].append(f"open_error:{e}")
        return True, info

    return (len(info["reason"]) > 0), info


class Command(BaseCommand):
    help = "清理无效PDF（支持dry-run，按阈值与可选分类过滤）"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="实际删除（默认仅dry-run）")
        parser.add_argument("--min-pages", type=int, default=1, help="最小页数阈值，默认1")
        parser.add_argument("--min-chars", type=int, default=0, help="最小字符阈值，0表示不检查")
        parser.add_argument("--limit", type=int, default=0, help="最多检查的文档数量，0表示全部")
        parser.add_argument("--category", type=str, default="", help="按分类过滤")

    def handle(self, *args, **options):
        apply = options["apply"]
        min_pages = max(1, int(options["min_pages"]))
        min_chars = int(options["min_chars"]) or 0
        limit = int(options["limit"]) or 0
        category = (options["category"] or "").strip()

        self.stdout.write(self.style.NOTICE(
            f"开始清理无效PDF | dry-run={not apply} | min_pages={min_pages} | min_chars={min_chars} | category='{category or 'ALL'}'"
        ))

        qs = PDFDocument.objects.all().order_by("-upload_date")
        if category:
            qs = qs.filter(category=category)
        if limit > 0:
            qs = qs[:limit]

        # 初始化处理器以便删除向量
        processor = WeaviateDocumentProcessor()

        invalid_docs: List[PDFDocument] = []
        checked = 0

        for doc in qs:
            checked += 1
            is_invalid, info = is_pdf_invalid(doc.file_path, min_pages=min_pages, min_chars=(min_chars or None))
            if is_invalid:
                invalid_docs.append((doc, info))

        self.stdout.write(f"共检查 {checked} 个文档，判定无效 {len(invalid_docs)} 个。")

        if not invalid_docs:
            self.stdout.write(self.style.SUCCESS("没有发现需要清理的文档。"))
            return

        # 列出样本
        for doc, info in invalid_docs[:10]:
            self.stdout.write(f"无效: {doc.filename} | reasons={','.join(info['reason'])} | pages={info['pages']} | chars={info['chars']}")

        if not apply:
            self.stdout.write(self.style.WARNING("dry-run 模式未执行删除。添加 --apply 才会实际删除。"))
            return

        removed = 0
        with transaction.atomic():
            for doc, info in invalid_docs:
                try:
                    # 先删除向量数据
                    try:
                        processor.vector_service.delete_document(str(doc.id))
                    except Exception as e:
                        logger.warning(f"删除向量数据失败 {doc.id}: {e}")

                    # 删除文件
                    try:
                        if doc.file_path and os.path.exists(doc.file_path):
                            os.remove(doc.file_path)
                    except Exception as e:
                        logger.warning(f"删除文件失败 {doc.file_path}: {e}")

                    # 删除数据库记录
                    doc.delete()
                    removed += 1
                except Exception as e:
                    logger.error(f"删除文档失败 {doc.id}: {e}")

        self.stdout.write(self.style.SUCCESS(f"清理完成，删除 {removed} 个无效文档。"))


