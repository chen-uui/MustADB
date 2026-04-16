"""
错误处理模块 - 处理直接处理系统中的各种错误
"""

import logging
import traceback
import functools
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型枚举"""
    VALIDATION_ERROR = "validation_error"
    PROCESSING_ERROR = "processing_error"
    LLM_ERROR = "llm_error"
    FILE_ERROR = "file_error"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    MEMORY_ERROR = "memory_error"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorInfo:
    """错误信息"""
    error_type: ErrorType
    error_code: str
    message: str
    details: Dict[str, Any]
    timestamp: str
    traceback: Optional[str] = None


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        """初始化错误处理器"""
        self.error_log = []
        self.max_log_size = 1000
        
        logger.info("ErrorHandler initialized")
    
    def handle_error(self, error: Exception, error_type: ErrorType, context: Dict[str, Any] = None) -> ErrorInfo:
        """处理错误"""
        try:
            error_info = ErrorInfo(
                error_type=error_type,
                error_code=self._generate_error_code(error_type),
                message=str(error),
                details=context or {},
                timestamp=self._get_timestamp(),
                traceback=traceback.format_exc()
            )
            
            # 记录错误
            self._log_error(error_info)
            
            # 根据错误类型采取不同的处理策略
            self._handle_error_by_type(error_info)
            
            return error_info
            
        except Exception as e:
            logger.error(f"Error in error handler: {str(e)}")
            return ErrorInfo(
                error_type=ErrorType.UNKNOWN_ERROR,
                error_code="ERROR_HANDLER_FAILED",
                message=str(e),
                details={},
                timestamp=self._get_timestamp()
            )
    
    def _generate_error_code(self, error_type: ErrorType) -> str:
        """生成错误代码"""
        error_codes = {
            ErrorType.VALIDATION_ERROR: "VAL_001",
            ErrorType.PROCESSING_ERROR: "PROC_001",
            ErrorType.LLM_ERROR: "LLM_001",
            ErrorType.FILE_ERROR: "FILE_001",
            ErrorType.DATABASE_ERROR: "DB_001",
            ErrorType.NETWORK_ERROR: "NET_001",
            ErrorType.MEMORY_ERROR: "MEM_001",
            ErrorType.TIMEOUT_ERROR: "TIME_001",
            ErrorType.UNKNOWN_ERROR: "UNK_001"
        }
        
        return error_codes.get(error_type, "UNK_001")
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _log_error(self, error_info: ErrorInfo):
        """记录错误"""
        try:
            # 添加到错误日志
            self.error_log.append(error_info)
            
            # 限制日志大小
            if len(self.error_log) > self.max_log_size:
                self.error_log = self.error_log[-self.max_log_size:]
            
            # 记录到日志文件
            logger.error(f"Error {error_info.error_code}: {error_info.message}")
            if error_info.traceback:
                logger.error(f"Traceback: {error_info.traceback}")
                
        except Exception as e:
            logger.error(f"Error logging error: {str(e)}")
    
    def _handle_error_by_type(self, error_info: ErrorInfo):
        """根据错误类型处理错误"""
        try:
            if error_info.error_type == ErrorType.VALIDATION_ERROR:
                self._handle_validation_error(error_info)
            elif error_info.error_type == ErrorType.PROCESSING_ERROR:
                self._handle_processing_error(error_info)
            elif error_info.error_type == ErrorType.LLM_ERROR:
                self._handle_llm_error(error_info)
            elif error_info.error_type == ErrorType.FILE_ERROR:
                self._handle_file_error(error_info)
            elif error_info.error_type == ErrorType.DATABASE_ERROR:
                self._handle_database_error(error_info)
            elif error_info.error_type == ErrorType.NETWORK_ERROR:
                self._handle_network_error(error_info)
            elif error_info.error_type == ErrorType.MEMORY_ERROR:
                self._handle_memory_error(error_info)
            elif error_info.error_type == ErrorType.TIMEOUT_ERROR:
                self._handle_timeout_error(error_info)
            else:
                self._handle_unknown_error(error_info)
                
        except Exception as e:
            logger.error(f"Error in error type handler: {str(e)}")
    
    def _handle_validation_error(self, error_info: ErrorInfo):
        """处理验证错误"""
        logger.warning(f"Validation error: {error_info.message}")
        # 可以在这里添加特定的验证错误处理逻辑
    
    def _handle_processing_error(self, error_info: ErrorInfo):
        """处理处理错误"""
        logger.error(f"Processing error: {error_info.message}")
        # 可以在这里添加特定的处理错误处理逻辑
    
    def _handle_llm_error(self, error_info: ErrorInfo):
        """处理LLM错误"""
        logger.error(f"LLM error: {error_info.message}")
        # 可以在这里添加特定的LLM错误处理逻辑
    
    def _handle_file_error(self, error_info: ErrorInfo):
        """处理文件错误"""
        logger.error(f"File error: {error_info.message}")
        # 可以在这里添加特定的文件错误处理逻辑
    
    def _handle_database_error(self, error_info: ErrorInfo):
        """处理数据库错误"""
        logger.error(f"Database error: {error_info.message}")
        # 可以在这里添加特定的数据库错误处理逻辑
    
    def _handle_network_error(self, error_info: ErrorInfo):
        """处理网络错误"""
        logger.error(f"Network error: {error_info.message}")
        # 可以在这里添加特定的网络错误处理逻辑
    
    def _handle_memory_error(self, error_info: ErrorInfo):
        """处理内存错误"""
        logger.error(f"Memory error: {error_info.message}")
        # 可以在这里添加特定的内存错误处理逻辑
    
    def _handle_timeout_error(self, error_info: ErrorInfo):
        """处理超时错误"""
        logger.error(f"Timeout error: {error_info.message}")
        # 可以在这里添加特定的超时错误处理逻辑
    
    def _handle_unknown_error(self, error_info: ErrorInfo):
        """处理未知错误"""
        logger.error(f"Unknown error: {error_info.message}")
        # 可以在这里添加特定的未知错误处理逻辑
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        try:
            error_counts = {}
            for error in self.error_log:
                error_type = error.error_type.value
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            return {
                'total_errors': len(self.error_log),
                'error_counts': error_counts,
                'recent_errors': [
                    {
                        'error_code': error.error_code,
                        'message': error.message,
                        'timestamp': error.timestamp
                    }
                    for error in self.error_log[-10:]  # 最近10个错误
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting error summary: {str(e)}")
            return {'error': str(e)}
    
    def clear_error_log(self):
        """清理错误日志"""
        self.error_log.clear()
        logger.info("Error log cleared")


class ValidationErrorHandler:
    """验证错误处理器"""
    
    def __init__(self):
        """初始化验证错误处理器"""
        self.validation_rules = {}
        
        logger.info("ValidationErrorHandler initialized")
    
    def validate_file(self, file_path: str) -> Dict[str, Any]:
        """验证文件"""
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # 检查文件是否存在
            import os
            if not os.path.exists(file_path):
                validation_result['valid'] = False
                validation_result['errors'].append('File does not exist')
                return validation_result
            
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                validation_result['valid'] = False
                validation_result['errors'].append('File is empty')
                return validation_result
            
            if file_size > 50 * 1024 * 1024:  # 50MB
                validation_result['valid'] = False
                validation_result['errors'].append('File too large (max 50MB)')
                return validation_result
            
            # 检查文件类型
            if not file_path.lower().endswith('.pdf'):
                validation_result['valid'] = False
                validation_result['errors'].append('Only PDF files are allowed')
                return validation_result
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating file: {str(e)}")
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}'],
                'warnings': []
            }
    
    def validate_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """验证处理选项"""
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # 检查必需选项
            required_options = ['focus', 'detail_level', 'language']
            for option in required_options:
                if option not in options:
                    validation_result['errors'].append(f'Missing required option: {option}')
                    validation_result['valid'] = False
            
            # 检查选项值
            if 'focus' in options:
                valid_focuses = ['comprehensive', 'meteorite', 'organic', 'mineral']
                if options['focus'] not in valid_focuses:
                    validation_result['errors'].append(f'Invalid focus value: {options["focus"]}')
                    validation_result['valid'] = False
            
            if 'detail_level' in options:
                valid_levels = ['high', 'medium', 'low']
                if options['detail_level'] not in valid_levels:
                    validation_result['errors'].append(f'Invalid detail level: {options["detail_level"]}')
                    validation_result['valid'] = False
            
            if 'language' in options:
                valid_languages = ['chinese', 'english']
                if options['language'] not in valid_languages:
                    validation_result['errors'].append(f'Invalid language: {options["language"]}')
                    validation_result['valid'] = False
            
            if 'confidence_threshold' in options:
                threshold = options['confidence_threshold']
                if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 1:
                    validation_result['errors'].append('Invalid confidence threshold (must be between 0 and 1)')
                    validation_result['valid'] = False
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating options: {str(e)}")
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}'],
                'warnings': []
            }


class RetryHandler:
    """重试处理器"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """初始化重试处理器"""
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        logger.info(f"RetryHandler initialized with max_retries={max_retries}, retry_delay={retry_delay}")
    
    def retry_on_error(self, func: Callable, *args, **kwargs):
        """在错误时重试函数"""
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"Function {func.__name__} failed after {self.max_retries} retries")
                    raise e
                
                logger.warning(f"Function {func.__name__} failed on attempt {attempt + 1}, retrying in {self.retry_delay}s")
                time.sleep(self.retry_delay)
    
    def retry_on_specific_error(self, func: Callable, error_types: tuple, *args, **kwargs):
        """在特定错误时重试函数"""
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                if attempt == self.max_retries:
                    logger.error(f"Function {func.__name__} failed after {self.max_retries} retries")
                    raise e
                
                logger.warning(f"Function {func.__name__} failed with {type(e).__name__} on attempt {attempt + 1}, retrying in {self.retry_delay}s")
                time.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"Function {func.__name__} failed with unexpected error: {str(e)}")
                raise e


def error_handler_decorator(error_type: ErrorType, context: Dict[str, Any] = None):
    """错误处理装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = ErrorHandler()
                error_info = error_handler.handle_error(e, error_type, context)
                
                # 根据错误类型决定是否重新抛出异常
                if error_type in [ErrorType.VALIDATION_ERROR, ErrorType.FILE_ERROR]:
                    raise e
                else:
                    # 对于其他错误类型，返回错误信息而不是抛出异常
                    return {'error': error_info.message, 'error_code': error_info.error_code}
        
        return wrapper
    return decorator


def retry_on_error(max_retries: int = 3, retry_delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_handler = RetryHandler(max_retries, retry_delay)
            return retry_handler.retry_on_error(func, *args, **kwargs)
        return wrapper
    return decorator


def validate_input(func):
    """输入验证装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 这里可以添加输入验证逻辑
            return func(*args, **kwargs)
        except Exception as e:
            error_handler = ErrorHandler()
            error_info = error_handler.handle_error(e, ErrorType.VALIDATION_ERROR, {'function': func.__name__})
            raise e
        return wrapper
    return decorator


# 全局错误处理器实例
global_error_handler = ErrorHandler()
global_validation_handler = ValidationErrorHandler()
global_retry_handler = RetryHandler()
