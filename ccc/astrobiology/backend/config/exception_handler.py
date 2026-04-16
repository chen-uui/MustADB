from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

from pdf_processor.api_errors import build_error_payload, sanitize_error_detail

logger = logging.getLogger(__name__)


def _serialize_response_detail(data: Any) -> str:
    return sanitize_error_detail(data, max_length=800)


def _resolve_exception_meta(exc: Exception, response_status: int) -> tuple[str, str]:
    default_code = ""
    if isinstance(exc, APIException):
        default_code = str(getattr(exc, "default_code", "") or "").upper()

    mapping = {
        status.HTTP_400_BAD_REQUEST: ("BAD_REQUEST", "请求参数错误"),
        status.HTTP_401_UNAUTHORIZED: ("UNAUTHORIZED", "身份认证失败"),
        status.HTTP_403_FORBIDDEN: ("FORBIDDEN", "没有权限执行该操作"),
        status.HTTP_404_NOT_FOUND: ("NOT_FOUND", "请求的接口或资源不存在"),
        status.HTTP_405_METHOD_NOT_ALLOWED: ("METHOD_NOT_ALLOWED", "请求方法不支持"),
        status.HTTP_406_NOT_ACCEPTABLE: ("NOT_ACCEPTABLE", "请求格式不支持"),
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: ("UNSUPPORTED_MEDIA_TYPE", "请求内容类型不受支持"),
        status.HTTP_429_TOO_MANY_REQUESTS: ("TOO_MANY_REQUESTS", "请求过于频繁，请稍后重试"),
    }

    return mapping.get(
        response_status,
        (default_code or "SERVER_ERROR", "服务器内部错误"),
    )


def api_exception_handler(exc: Exception, context: dict):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    error_code, message = _resolve_exception_meta(exc, response.status_code)
    detail = _serialize_response_detail(response.data or getattr(exc, "detail", "") or str(exc))

    response.data = build_error_payload(
        error_code=error_code,
        message=message,
        detail=detail,
    )
    return response
