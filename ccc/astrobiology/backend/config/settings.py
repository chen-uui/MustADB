"""
统一的配置管理
整合所有配置项，避免重复定义
"""
import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).resolve().parent.parent

# 环境变量
def get_env_var(name: str, default=None, required=False):
    """获取环境变量，支持默认值和必需检查"""
    value = os.getenv(name, default)
    if required and value is None:
        raise ValueError(f"Required environment variable {name} is not set")
    return value


def resolve_log_path(raw_value=None, default_filename='astrobiology.log'):
    """Normalize relative log paths against the backend BASE_DIR."""
    default_path = (BASE_DIR / 'logs' / default_filename).resolve()
    if not raw_value:
        return default_path

    path = Path(raw_value).expanduser()
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    return path


MAIN_LOG_FILE = resolve_log_path(get_env_var('LOG_FILE', None))

# 服务器配置
SERVER_CONFIG = {
    'HOST': get_env_var('SERVER_HOST', '127.0.0.1'),
    'PORT': int(get_env_var('SERVER_PORT', '8000')),
    'DEBUG': get_env_var('DEBUG', 'True').lower() == 'true',
    'ALLOWED_HOSTS': get_env_var('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','),
}

# 数据库配置
DATABASE_CONFIG = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': get_env_var('DB_NAME', 'astrobiology_db'),
    'USER': get_env_var('DB_USER', 'postgres'),
    'PASSWORD': get_env_var('DB_PASSWORD', ''),
    'HOST': get_env_var('DB_HOST', 'localhost'),
    'PORT': get_env_var('DB_PORT', '5432'),
}

# Weaviate配置
WEAVIATE_CONFIG = {
    'HOST': get_env_var('WEAVIATE_HOST', 'localhost'),
    'PORT': int(get_env_var('WEAVIATE_PORT', '8080')),
    'TIMEOUT': int(get_env_var('WEAVIATE_TIMEOUT', '30')),
    'URL': f"http://{get_env_var('WEAVIATE_HOST', 'localhost')}:{get_env_var('WEAVIATE_PORT', '8080')}",
}

# Redis配置
REDIS_CONFIG = {
    'HOST': get_env_var('REDIS_HOST', 'localhost'),
    'PORT': int(get_env_var('REDIS_PORT', '6379')),
    'DB': int(get_env_var('REDIS_DB', '0')),
    'PASSWORD': get_env_var('REDIS_PASSWORD'),
    'URL': f"redis://{get_env_var('REDIS_HOST', 'localhost')}:{get_env_var('REDIS_PORT', '6379')}/{get_env_var('REDIS_DB', '0')}",
}

# LLM配置 (优先使用Ollama，备用OpenAI)
LLM_CONFIG = {
    # Ollama配置 (主要)
    'OLLAMA_BASE_URL': get_env_var('OLLAMA_BASE_URL', 'http://localhost:11434'),
    'OLLAMA_MODEL': get_env_var('OLLAMA_MODEL', 'llama3.1:8b-instruct-q4_K_M'),
    'OLLAMA_TIMEOUT': int(get_env_var('OLLAMA_TIMEOUT', '300')),
    
    # OpenAI配置 (备用)
    'OPENAI_API_KEY': get_env_var('OPENAI_API_KEY', required=False),
    'OPENAI_MODEL': get_env_var('OPENAI_MODEL', 'gpt-3.5-turbo'),
    'OPENAI_MAX_TOKENS': int(get_env_var('OPENAI_MAX_TOKENS', '1000')),
    'OPENAI_TEMPERATURE': float(get_env_var('OPENAI_TEMPERATURE', '0.7')),
}

# 嵌入模型配置
EMBEDDING_CONFIG = {
    'MODEL_NAME': get_env_var('EMBEDDING_MODEL', 'sentence-transformers/all-mpnet-base-v2'),  # 使用更高质量的模型
    'CACHE_DIR': get_env_var('MODEL_CACHE_DIR', str(BASE_DIR / 'models')),
    'DEVICE': get_env_var('EMBEDDING_DEVICE', 'cpu'),
    'BATCH_SIZE': int(get_env_var('EMBEDDING_BATCH_SIZE', '32')),
}

# 重排序模型配置 - 使用正确的模型名称
RERANKER_CONFIG = {
    'MODEL_NAME': get_env_var('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2'),
    'CACHE_DIR': get_env_var('RERANKER_CACHE_DIR', str(BASE_DIR / 'models')),
    'DEVICE': get_env_var('RERANKER_DEVICE', 'cpu'),
}

# 文件存储配置
STORAGE_CONFIG = {
    'UPLOAD_DIR': get_env_var('UPLOAD_DIR', str(BASE_DIR / 'uploads')),
    'MAX_FILE_SIZE': int(get_env_var('MAX_FILE_SIZE', '50')) * 1024 * 1024,  # 50MB
    'ALLOWED_EXTENSIONS': get_env_var('ALLOWED_EXTENSIONS', 'pdf,txt,docx').split(','),
}

# 日志配置
LOGGING_CONFIG = 'logging_config.LOGGING_CONFIG'

# 日志设置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': get_env_var('LOG_LEVEL', 'INFO'),
            'class': 'logging.FileHandler',
            'filename': str(MAIN_LOG_FILE),
            'formatter': 'verbose',
        },
        'astro_file': {
            'level': get_env_var('LOG_LEVEL', 'INFO'),
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(MAIN_LOG_FILE),
            'maxBytes': 5 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': get_env_var('LOG_LEVEL', 'INFO'),
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'astro_file'],
        'level': get_env_var('LOG_LEVEL', 'INFO'),
    },
}

# REST Framework配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# 安全配置
SECURITY_CONFIG = {
    'SECRET_KEY': get_env_var('SECRET_KEY', 'dev-secret-key-change-before-production'),
    'JWT_SECRET': get_env_var('JWT_SECRET', 'dev-jwt-secret-change-before-production'),
    'JWT_EXPIRATION': int(get_env_var('JWT_EXPIRATION', '3600')),  # 1小时
    'CORS_ORIGINS': get_env_var('CORS_ORIGINS', 'http://localhost:3000').split(','),
}

# 处理配置
PROCESSING_CONFIG = {
    # 以token计：默认700 token，约等效3000字符英文
    'CHUNK_SIZE': int(get_env_var('CHUNK_SIZE', '700')),
    'CHUNK_OVERLAP': int(get_env_var('CHUNK_OVERLAP', '80')),
    'MAX_WORKERS': int(get_env_var('MAX_WORKERS', '4')),
    'BATCH_SIZE': int(get_env_var('BATCH_SIZE', '10')),
}

# 创建必要的目录
def ensure_directories():
    """确保必要的目录存在"""
    directories = [
        STORAGE_CONFIG['UPLOAD_DIR'],
        EMBEDDING_CONFIG['CACHE_DIR'],
        RERANKER_CONFIG['CACHE_DIR'],
        MAIN_LOG_FILE.parent,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# 初始化时创建目录
ensure_directories()
