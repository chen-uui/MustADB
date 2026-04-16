from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Any, Dict, Optional

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

DOCUMENT_PROCESSING_ERROR_CACHE_KEY = "pdf_document_processing_error:{document_id}"
DOCUMENT_PROCESSING_ERROR_TTL = 60 * 60 * 6

HTML_TAG_RE = re.compile(r"<[^>]+>")
TRACEBACK_LINE_RE = re.compile(r"^\s*(Traceback|File \")")
LATIN1_MOJIBAKE_RE = re.compile(r"[ÃÂÆÐØÐæçéåø]")


@dataclass
class APIErrorInfo:
    error_code: str
    message: str
    detail: str
    status_code: int = status.HTTP_400_BAD_REQUEST


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bytes):
        for encoding in ("utf-8", "gb18030", "latin-1"):
            try:
                return value.decode(encoding)
            except Exception:
                continue
        return value.decode("utf-8", errors="replace")

    if isinstance(value, str):
        return value

    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    return str(value)


def _repair_mojibake(text: str) -> str:
    if not text or not LATIN1_MOJIBAKE_RE.search(text):
        return text

    try:
        repaired = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        return text

    if repaired and repaired != text:
        return repaired
    return text


def normalize_text(value: Any) -> str:
    text = _repair_mojibake(_coerce_text(value))
    text = unescape(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    if "<html" in text.lower() or "<!doctype html" in text.lower():
        text = HTML_TAG_RE.sub(" ", text)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate_text(value: Any, max_length: int = 500) -> str:
    text = normalize_text(value)
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


def sanitize_error_detail(value: Any, max_length: int = 500) -> str:
    raw = _coerce_text(value)
    if not raw:
        return ""

    if "Traceback (most recent call last)" in raw:
        filtered_lines = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or TRACEBACK_LINE_RE.match(line):
                continue
            filtered_lines.append(line)
        raw = " | ".join(filtered_lines)

    return truncate_text(raw, max_length=max_length)


def build_error_payload(
    error_code: str,
    message: str,
    detail: Any = "",
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    safe_message = truncate_text(message, max_length=200) or "请求失败"
    safe_detail = sanitize_error_detail(detail) or safe_message
    payload: Dict[str, Any] = {
        "success": False,
        "error_code": error_code or "REQUEST_FAILED",
        "message": safe_message,
        "detail": safe_detail,
        "error": safe_message,
    }
    if extra:
        payload.update(extra)
    return payload


def error_response(
    error_code: str,
    message: str,
    detail: Any = "",
    *,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    extra: Optional[Dict[str, Any]] = None,
) -> Response:
    return Response(
        build_error_payload(error_code, message, detail, extra=extra),
        status=status_code,
    )


def build_success_payload(
    *,
    message: Optional[str] = None,
    data: Any = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"success": True}
    if message:
        payload["message"] = truncate_text(message, max_length=200)
    if data is not None:
        payload["data"] = data
    if extra:
        payload.update(extra)
    return payload


def processing_error_result(
    error_code: str,
    message: str,
    detail: Any = "",
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = build_error_payload(error_code, message, detail, extra=extra)
    payload["status"] = "error"
    return payload


def file_save_error(detail: Any) -> APIErrorInfo:
    return APIErrorInfo(
        error_code="FILE_SAVE_FAILED",
        message="文件保存失败",
        detail=sanitize_error_detail(detail),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def pdf_parse_error(detail: Any, *, error_code: str = "PDF_PARSE_FAILED") -> APIErrorInfo:
    return APIErrorInfo(
        error_code=error_code,
        message="PDF 解析失败",
        detail=sanitize_error_detail(detail),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def ocr_error(detail: Any) -> APIErrorInfo:
    return APIErrorInfo(
        error_code="OCR_FAILED",
        message="OCR 识别失败",
        detail=sanitize_error_detail(detail),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def text_chunk_error(detail: Any) -> APIErrorInfo:
    return APIErrorInfo(
        error_code="TEXT_CHUNK_FAILED",
        message="文本切块失败",
        detail=sanitize_error_detail(detail),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def vector_index_error(detail: Any) -> APIErrorInfo:
    return APIErrorInfo(
        error_code="VECTOR_INDEX_FAILED",
        message="向量库写入失败",
        detail=sanitize_error_detail(detail),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def embedding_error(detail: Any) -> APIErrorInfo:
    return APIErrorInfo(
        error_code="EMBEDDING_FAILED",
        message="嵌入生成失败",
        detail=sanitize_error_detail(detail),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def database_write_error(detail: Any) -> APIErrorInfo:
    return APIErrorInfo(
        error_code="DATABASE_WRITE_FAILED",
        message="数据库写入失败",
        detail=sanitize_error_detail(detail),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def generic_processing_error(detail: Any, *, error_code: str = "PDF_PROCESS_FAILED") -> APIErrorInfo:
    return APIErrorInfo(
        error_code=error_code,
        message="PDF 处理失败",
        detail=sanitize_error_detail(detail),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def from_pdf_extraction_result(result: Dict[str, Any]) -> APIErrorInfo:
    extraction_code = str(result.get("error_code") or "").strip().upper()
    detail = (
        result.get("error")
        or result.get("detail")
        or result.get("diagnostics")
        or "未知错误"
    )

    mapping = {
        "FILE_NOT_FOUND": APIErrorInfo(
            "PDF_FILE_NOT_FOUND",
            "PDF 文件不存在",
            sanitize_error_detail(detail),
            status.HTTP_404_NOT_FOUND,
        ),
        "EMPTY_FILE": APIErrorInfo(
            "PDF_EMPTY_FILE",
            "PDF 文件为空",
            sanitize_error_detail(detail),
            status.HTTP_400_BAD_REQUEST,
        ),
        "PDF_OPEN_FAILED": APIErrorInfo(
            "PDF_OPEN_FAILED",
            "PDF 解析失败",
            sanitize_error_detail(detail),
            status.HTTP_400_BAD_REQUEST,
        ),
        "PDF_DATA_ERROR": APIErrorInfo(
            "PDF_DATA_ERROR",
            "文件格式不支持或 PDF 已损坏",
            sanitize_error_detail(detail),
            status.HTTP_400_BAD_REQUEST,
        ),
        "NO_TEXT_EXTRACTED": APIErrorInfo(
            "NO_TEXT_EXTRACTED",
            "PDF 未提取到可读文本",
            sanitize_error_detail(detail),
            status.HTTP_400_BAD_REQUEST,
        ),
        "OCR_FAILED": ocr_error(detail),
        "MEMORY_ERROR": APIErrorInfo(
            "PDF_MEMORY_ERROR",
            "PDF 处理资源不足",
            sanitize_error_detail(detail),
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ),
        "UNKNOWN_ERROR": generic_processing_error(detail),
    }
    return mapping.get(extraction_code, generic_processing_error(detail))


def from_processing_result(result: Dict[str, Any]) -> APIErrorInfo:
    if not isinstance(result, dict):
        return generic_processing_error("处理结果格式异常")

    explicit_code = str(result.get("error_code") or "").strip().upper()
    if explicit_code:
        status_code = result.get("status_code") or status.HTTP_500_INTERNAL_SERVER_ERROR
        try:
            status_code = int(status_code)
        except Exception:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return APIErrorInfo(
            error_code=explicit_code,
            message=truncate_text(result.get("message") or result.get("error") or "PDF 处理失败", max_length=200),
            detail=sanitize_error_detail(result.get("detail") or result.get("error") or "未知错误"),
            status_code=status_code,
        )

    detail = sanitize_error_detail(result.get("detail") or result.get("error") or "未知错误")
    lowered = detail.lower()

    if any(token in lowered for token in ("ocr", "tesseract")) or "识别" in detail:
        return ocr_error(detail)
    if any(token in lowered for token in ("embedding", "sentence-transformer", "model encode")) or "嵌入" in detail:
        return embedding_error(detail)
    if any(token in lowered for token in ("weaviate", "vector", "index")) or any(token in detail for token in ("向量", "索引")):
        return vector_index_error(detail)
    if any(token in lowered for token in ("chunk", "splitter")) or any(token in detail for token in ("切块", "分块")):
        return text_chunk_error(detail)
    if any(token in lowered for token in ("database", "postgres", "sqlite", "integrityerror")) or "数据库" in detail:
        return database_write_error(detail)
    if any(token in lowered for token in ("pdf", "document closed", "open failed")) or any(token in detail for token in ("PDF", "损坏", "格式")):
        return pdf_parse_error(detail)

    return generic_processing_error(detail)


def remember_document_processing_error(document_id: Any, error_code: str, message: str, detail: Any) -> None:
    if not document_id:
        return

    payload = {
        "error_code": truncate_text(error_code, max_length=100),
        "message": truncate_text(message, max_length=200),
        "detail": sanitize_error_detail(detail),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    cache.set(
        DOCUMENT_PROCESSING_ERROR_CACHE_KEY.format(document_id=document_id),
        payload,
        DOCUMENT_PROCESSING_ERROR_TTL,
    )


def clear_document_processing_error(document_id: Any) -> None:
    if not document_id:
        return
    cache.delete(DOCUMENT_PROCESSING_ERROR_CACHE_KEY.format(document_id=document_id))


def get_document_processing_error(document_id: Any) -> Optional[Dict[str, Any]]:
    if not document_id:
        return None

    cached = cache.get(DOCUMENT_PROCESSING_ERROR_CACHE_KEY.format(document_id=document_id))
    if not isinstance(cached, dict):
        return None

    return {
        "error_code": truncate_text(cached.get("error_code"), max_length=100),
        "message": truncate_text(cached.get("message"), max_length=200),
        "detail": sanitize_error_detail(cached.get("detail")),
        "updated_at": truncate_text(cached.get("updated_at"), max_length=100),
    }
