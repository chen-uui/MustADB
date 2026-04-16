"""
统一的日志配置
提供高性能的日志管理和监控
"""

import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent


def resolve_log_path(raw_value=None, default_filename='astrobiology.log'):
    """Normalize relative log paths against the backend BASE_DIR."""
    default_path = (BASE_DIR / 'logs' / default_filename).resolve()
    if not raw_value:
        return default_path

    path = Path(raw_value).expanduser()
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    return path


LOG_DIR = (BASE_DIR / "logs").resolve()
LOG_DIR.mkdir(parents=True, exist_ok=True)
MAIN_LOG_FILE = resolve_log_path(os.getenv('LOG_FILE', '').strip() or None)

# 日志配置
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'standard': {
            'format': '[{asctime}] {levelname} [{module}:{lineno}] {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(MAIN_LOG_FILE),
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8'
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'errors.log'),
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 5,
            'formatter': 'verbose',
            'encoding': 'utf-8'
        },
        'performance_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(LOG_DIR / 'performance.log'),
            'maxBytes': 100 * 1024 * 1024,  # 100MB
            'backupCount': 10,
            'formatter': 'json',
            'encoding': 'utf-8'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',  # 临时替换为控制台输出，避免Django配置依赖
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'pdf_processor': {
            'handlers': ['console', 'file', 'error_file', 'performance_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'weaviate': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'rag_service': {
            'handlers': ['console', 'file', 'performance_file'],
            'level': 'DEBUG',
            'propagate': False,
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    }
}


def setup_logging():
    """设置日志配置"""
    import logging.config
    logging.config.dictConfig(LOGGING_CONFIG)


def get_performance_logger(name: str) -> logging.Logger:
    """获取性能日志记录器"""
    logger = logging.getLogger(name)
    return logger


def log_performance(func):
    """性能监控装饰器"""
    import time
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger = get_performance_logger('performance')
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.debug(
                f"Function {func.__name__} executed in {execution_time:.3f}s",
                extra={
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'args_length': len(str(args)),
                    'kwargs_length': len(str(kwargs))
                }
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}",
                extra={
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'error': str(e)
                }
            )
            raise
    
    return wrapper


class QueryPerformanceMonitor:
    """查询性能监控器"""
    
    def __init__(self, logger_name: str = 'rag_performance'):
        self.logger = get_performance_logger(logger_name)
        self.query_times = []
    
    def record_query(self, query: str, execution_time: float, result_count: int):
        """记录查询性能"""
        self.query_times.append({
            'query': query[:100],  # 限制查询长度
            'execution_time': execution_time,
            'result_count': result_count,
            'timestamp': datetime.now().isoformat()
        })
        
        self.logger.info(
            f"Query executed",
            extra={
                'query': query[:100],
                'execution_time': execution_time,
                'result_count': result_count,
                'query_type': 'rag_search'
            }
        )
    
    def get_average_query_time(self) -> float:
        """获取平均查询时间"""
        if not self.query_times:
            return 0.0
        return sum(t['execution_time'] for t in self.query_times) / len(self.query_times)
    
    def get_slow_queries(self, threshold: float = 2.0) -> list:
        """获取慢查询"""
        return [t for t in self.query_times if t['execution_time'] > threshold]


# 全局性能监控器
performance_monitor = QueryPerformanceMonitor()


if __name__ == "__main__":
    # 测试日志配置
    setup_logging()
    logger = logging.getLogger('pdf_processor')
    logger.info("日志系统测试成功")
    
    # 测试性能监控
    @log_performance
    def test_function():
        import time
        time.sleep(0.1)
        return "test"
    
    result = test_function()
    print(f"测试结果: {result}")
