"""
统一的装饰器工具
用于API视图的错误处理和性能监控
"""
import logging
import time
from functools import wraps
from django.db import transaction
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def api_error_handler(func):
    """
    统一的API错误处理装饰器
    自动捕获异常并返回标准化的错误响应
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"{func.__name__}: 参数错误 - {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except PermissionError as e:
            logger.warning(f"{func.__name__}: 权限错误 - {str(e)}")
            return Response({
                'success': False,
                'error': '权限不足'
            }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"{func.__name__}: 系统错误 - {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': '系统内部错误，请稍后重试'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return wrapper


def performance_monitor(func):
    """
    性能监控装饰器
    记录函数执行时间
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # 如果执行时间超过1秒，记录警告
            if execution_time > 1.0:
                logger.warning(f"{func.__name__} 执行时间较长: {execution_time:.2f}秒")
            else:
                logger.debug(f"{func.__name__} 执行时间: {execution_time:.2f}秒")
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败 (耗时: {execution_time:.2f}秒): {str(e)}")
            raise
    return wrapper


def atomic_transaction(func):
    """
    事务装饰器
    确保函数在数据库事务中执行
    """
    @wraps(func)
    @transaction.atomic
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

