"""
User PDF upload views.
"""

import logging
import os
from typing import Any, Dict

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .api_errors import (
    build_error_payload,
    error_response,
    file_save_error,
    from_pdf_extraction_result,
    sanitize_error_detail,
)
from .models import PDFDocument
from .services.upload_storage_service import MEDIA_UPLOADS, UploadStorageService

logger = logging.getLogger(__name__)

PENDING_UPLOAD_CATEGORY = "用户上传待审核"


def _extract_pdf_metadata(file_path: str, uploaded_filename: str):
    import fitz  # PyMuPDF

    from .pdf_utils import PDFUtils

    with fitz.open(file_path) as doc:
        page_count = len(doc)

    extraction_result = PDFUtils.extract_text_and_metadata(file_path)
    if not extraction_result.get("success"):
        raise ValueError(extraction_result)

    metadata = extraction_result.get("metadata", {})
    title = metadata.get("title") or os.path.splitext(uploaded_filename)[0]
    authors = metadata.get("authors", "")
    year_str = metadata.get("year", "")
    year = int(year_str) if year_str and year_str.isdigit() else None
    journal = metadata.get("journal", "")
    doi = metadata.get("doi", "")

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "journal": journal,
        "doi": doi,
        "page_count": page_count,
    }


def _build_pending_review_base_kwargs(uploaded_filename: str, uploaded_by):
    return {
        "filename": uploaded_filename,
        "category": PENDING_UPLOAD_CATEGORY,
        "processed": False,
        "review_status": "pending",
        "uploaded_by": uploaded_by,
    }


def _build_duplicate_pending_document_kwargs(
    uploaded_filename: str,
    uploaded_by,
    duplicate_content_doc,
    duplicate_inspection,
    uploaded_file_size: int,
):
    document_kwargs = _build_pending_review_base_kwargs(uploaded_filename, uploaded_by)
    document_kwargs.update(
        {
            "title": getattr(duplicate_content_doc, "title", "") or os.path.splitext(uploaded_filename)[0],
            "authors": getattr(duplicate_content_doc, "authors", "") or "",
            "year": getattr(duplicate_content_doc, "year", None),
            "journal": getattr(duplicate_content_doc, "journal", "") or "",
            "doi": getattr(duplicate_content_doc, "doi", "") or "",
            "duplicate_of": duplicate_content_doc,
            "file_path": duplicate_content_doc.file_path,
            "file_size": getattr(duplicate_content_doc, "file_size", 0) or uploaded_file_size,
            "page_count": getattr(duplicate_content_doc, "page_count", 0) or 0,
            "sha1": getattr(duplicate_content_doc, "sha1", None) or duplicate_inspection.sha1,
        }
    )
    return document_kwargs


def _build_new_pending_document_kwargs(
    uploaded_filename: str,
    uploaded_by,
    metadata: dict,
    stored_upload,
    uploaded_file_size: int,
):
    document_kwargs = _build_pending_review_base_kwargs(uploaded_filename, uploaded_by)
    document_kwargs.update(
        {
            "title": metadata["title"],
            "authors": metadata["authors"],
            "year": metadata["year"],
            "journal": metadata["journal"],
            "doi": metadata["doi"],
            "duplicate_of": None,
            "file_path": stored_upload.file_path,
            "file_size": uploaded_file_size,
            "page_count": metadata["page_count"],
            "sha1": stored_upload.sha1,
        }
    )
    return document_kwargs


def _error_item(filename: str, error_code: str, message: str, detail: Any) -> Dict[str, Any]:
    payload = build_error_payload(error_code, message, detail)
    payload["filename"] = filename
    return payload


@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def user_upload_pdfs(request):
    """User uploads create pending-review PDFDocument records."""
    try:
        if "files" not in request.FILES:
            return error_response(
                error_code="NO_FILES_UPLOADED",
                message="未检测到上传文件",
                detail="请求中缺少 files 字段",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_files = request.FILES.getlist("files")
        if len(uploaded_files) == 0:
            return error_response(
                error_code="NO_FILES_SELECTED",
                message="请选择要上传的 PDF 文件",
                detail="files 列表为空",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if len(uploaded_files) > 10:
            return error_response(
                error_code="UPLOAD_LIMIT_EXCEEDED",
                message="单次最多上传 10 个文件",
                detail=f"当前上传数量: {len(uploaded_files)}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        results = []

        for uploaded_file in uploaded_files:
            try:
                if not uploaded_file.name.lower().endswith(".pdf"):
                    results.append(
                        _error_item(
                            uploaded_file.name,
                            "UNSUPPORTED_FILE_TYPE",
                            "仅支持上传 PDF 文件",
                            f"文件名: {uploaded_file.name}",
                        )
                    )
                    continue

                max_size = 50 * 1024 * 1024
                if uploaded_file.size > max_size:
                    results.append(
                        _error_item(
                            uploaded_file.name,
                            "FILE_TOO_LARGE",
                            "文件大小超过 50MB 限制",
                            f"当前大小: {uploaded_file.size / 1024 / 1024:.2f}MB",
                        )
                    )
                    continue

                duplicate_inspection = UploadStorageService.inspect_uploaded_file(uploaded_file)
                UploadStorageService.log_duplicate_inspection(logger, "user_upload", duplicate_inspection)

                existing_doc = PDFDocument.objects.filter(filename=uploaded_file.name).first()
                if existing_doc:
                    results.append(
                        _error_item(
                            uploaded_file.name,
                            "DUPLICATE_FILENAME",
                            "同名文件已存在",
                            f"document_id={existing_doc.id}",
                        )
                    )
                    continue

                uploaded_by = request.user if request.user.is_authenticated else None
                duplicate_content_doc = None
                document_kwargs = None

                if duplicate_inspection.duplicate_detected and duplicate_inspection.duplicate_document_id:
                    duplicate_record = PDFDocument.objects.filter(
                        id=duplicate_inspection.duplicate_document_id
                    ).first()
                    duplicate_content_doc = UploadStorageService.resolve_content_document(duplicate_record)
                    duplicate_file_path = getattr(duplicate_content_doc, "file_path", None)
                    if not duplicate_file_path or not os.path.exists(duplicate_file_path):
                        logger.warning(
                            "Duplicate hit could not reuse existing content file: incoming=%s duplicate_document_id=%s file_path=%s",
                            uploaded_file.name,
                            duplicate_inspection.duplicate_document_id,
                            duplicate_file_path,
                        )
                        duplicate_content_doc = None

                if duplicate_content_doc is not None:
                    logger.info(
                        "user_upload_duplicate_hit incoming=%s duplicate_document_id=%s canonical_filename=%s",
                        uploaded_file.name,
                        duplicate_content_doc.id,
                        getattr(duplicate_content_doc, "filename", ""),
                    )
                    document_kwargs = _build_duplicate_pending_document_kwargs(
                        uploaded_file.name,
                        uploaded_by,
                        duplicate_content_doc,
                        duplicate_inspection,
                        uploaded_file.size,
                    )

                if document_kwargs is None:
                    try:
                        stored_upload = UploadStorageService.save_uploaded_file(
                            uploaded_file,
                            storage_key=MEDIA_UPLOADS,
                            naming_strategy="uuid",
                            precomputed_inspection=duplicate_inspection,
                        )
                    except Exception as exc:
                        logger.exception("保存用户上传文件失败: %s", uploaded_file.name)
                        error_info = file_save_error(exc)
                        results.append(
                            _error_item(
                                uploaded_file.name,
                                error_info.error_code,
                                error_info.message,
                                error_info.detail,
                            )
                        )
                        continue

                    file_path = stored_upload.file_path

                    try:
                        metadata = _extract_pdf_metadata(file_path, uploaded_file.name)
                    except Exception as exc:
                        if os.path.exists(file_path):
                            os.remove(file_path)

                        extraction_payload = exc.args[0] if exc.args and isinstance(exc.args[0], dict) else None
                        if extraction_payload:
                            error_info = from_pdf_extraction_result(extraction_payload)
                        else:
                            error_info = from_pdf_extraction_result(
                                {
                                    "error_code": "PDF_OPEN_FAILED",
                                    "error": sanitize_error_detail(exc),
                                }
                            )
                        logger.exception("提取用户上传 PDF 元数据失败: %s", uploaded_file.name)
                        results.append(
                            _error_item(
                                uploaded_file.name,
                                error_info.error_code,
                                "文件格式不支持或 PDF 已损坏",
                                error_info.detail,
                            )
                        )
                        continue

                    document_kwargs = _build_new_pending_document_kwargs(
                        uploaded_file.name,
                        uploaded_by,
                        metadata,
                        stored_upload,
                        uploaded_file.size,
                    )

                try:
                    pdf_document = PDFDocument.objects.create(**document_kwargs)
                except Exception as exc:
                    logger.exception("写入用户上传记录失败: %s", uploaded_file.name)
                    results.append(
                        _error_item(
                            uploaded_file.name,
                            "DATABASE_WRITE_FAILED",
                            "数据库写入失败",
                            exc,
                        )
                    )
                    continue

                results.append(
                    {
                        "filename": uploaded_file.name,
                        "success": True,
                        "document_id": str(pdf_document.id),
                        "title": pdf_document.title,
                        "message": "上传成功，等待审核",
                        "detail": "文件已保存并创建待审核记录",
                    }
                )

                logger.info("User uploaded PDF: %s (ID: %s)", uploaded_file.name, pdf_document.id)

            except Exception as exc:
                logger.exception("处理用户上传文件失败: %s", uploaded_file.name)
                results.append(
                    _error_item(
                        uploaded_file.name,
                        "UPLOAD_ITEM_FAILED",
                        "上传失败",
                        exc,
                    )
                )

        success_count = sum(1 for item in results if item.get("success"))
        return Response(
            {
                "success": success_count > 0,
                "results": results,
                "summary": {
                    "total": len(results),
                    "successful": success_count,
                    "failed": len(results) - success_count,
                },
            },
            status=status.HTTP_200_OK,
        )

    except Exception as exc:
        logger.exception("User upload error")
        return error_response(
            error_code="UPLOAD_REQUEST_FAILED",
            message="上传请求处理失败",
            detail=exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
