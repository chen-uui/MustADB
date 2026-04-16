"""
通用工具函数。
"""

import json
import logging
from typing import Any, Dict

from django.http import HttpRequest
from rest_framework import status
from rest_framework.response import Response

from .api_errors import build_success_payload, error_response

logger = logging.getLogger(__name__)


def parse_request_body(request: HttpRequest) -> Dict[str, Any]:
    """安全解析 JSON 请求体。"""
    if not request.body:
        return {}

    try:
        return json.loads(request.body)
    except json.JSONDecodeError as exc:
        logger.warning("JSON 解析失败: %s", exc)
        raise ValueError("无效的 JSON 格式")


def validate_pagination_params(page: Any, page_size: Any, max_page_size: int = 100) -> tuple[int, int]:
    """规范化分页参数。"""
    try:
        page = max(1, int(page))
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = max(1, min(max_page_size, int(page_size)))
    except (ValueError, TypeError):
        page_size = 20

    return page, page_size


def validate_threshold(threshold: Any, default: float = 0.5) -> float:
    """规范化 0 到 1 之间的阈值参数。"""
    try:
        threshold = float(threshold)
        if not 0 <= threshold <= 1:
            return default
        return threshold
    except (ValueError, TypeError):
        return default


def create_error_response(error_message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    """返回统一错误响应。"""
    return error_response(
        error_code="REQUEST_FAILED",
        message=error_message,
        detail=error_message,
        status_code=status_code,
    )


def create_success_response(data: Any, status_code: int = status.HTTP_200_OK) -> Response:
    """返回统一成功响应。"""
    return Response(build_success_payload(data=data), status=status_code)
