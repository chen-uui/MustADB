"""
Django settings for astrobiology project.
"""
import os
from pathlib import Path

# 加载环境变量
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 环境变量获取函数
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

# 环境标识与安全配置
ENVIRONMENT = get_env_var('ENVIRONMENT', 'dev').lower()
IS_PROD = ENVIRONMENT == 'prod'
API_ALLOW_ANONYMOUS = get_env_var('API_ALLOW_ANONYMOUS', 'False').lower() == 'true'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_var(
    'SECRET_KEY',
    None if IS_PROD else 'dev-secret-key-change-in-production',
    required=IS_PROD
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_var('DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = get_env_var('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'pdf_processor',
    'meteorite_search',
    'astro_data',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 确保CORS中间件在安全中间件之前
CORS_MIDDLEWARE_POSITION = 0

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': get_env_var('DB_NAME', 'astrobiology_db'),
        'USER': get_env_var('DB_USER', 'postgres'),
        'PASSWORD': get_env_var('DB_PASSWORD', '123456'),
        'HOST': get_env_var('DB_HOST', 'localhost'),
        'PORT': get_env_var('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(get_env_var('DB_CONN_MAX_AGE', '60')),  # 允许连接复用，减少频繁握手
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# PDF存储路径
PDF_STORAGE_PATH = os.path.join(BASE_DIR, '..', 'data', 'pdfs')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 文件上传配置
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000  # 增加字段数量限制
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny' if API_ALLOW_ANONYMOUS else 'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'meteorite_search.authentication.BearerTokenAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'EXCEPTION_HANDLER': 'config.exception_handler.api_exception_handler',
    # 全局分页设置：返回count/next/previous/results结构
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# CORS / CSRF 设置
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_default_csrf = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
if API_ALLOW_ANONYMOUS or not IS_PROD:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in get_env_var('CORS_ALLOWED_ORIGINS', _default_origins).split(',') if origin.strip()
    ]
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in get_env_var('CSRF_TRUSTED_ORIGINS', _default_csrf).split(',') if origin.strip()
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# 安全头配置（生产开启）
if IS_PROD and not API_ALLOW_ANONYMOUS:
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
    SECURE_REFERRER_POLICY = "same-origin"
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
else:
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None
    SECURE_REFERRER_POLICY = None
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(MAIN_LOG_FILE),
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': get_env_var('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': get_env_var('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# 自定义配置
# OpenAI配置
OPENAI_CONFIG = {
    'API_KEY': get_env_var('OPENAI_API_KEY', 'sk-placeholder-key-for-development', required=True),
    'MODEL': get_env_var('OPENAI_MODEL', 'gpt-3.5-turbo'),
    'MAX_TOKENS': int(get_env_var('OPENAI_MAX_TOKENS', '1000')),
    'TEMPERATURE': float(get_env_var('OPENAI_TEMPERATURE', '0.7')),
}

# Weaviate配置
WEAVIATE_CONFIG = {
    'HOST': get_env_var('WEAVIATE_HOST', 'localhost'),
    'PORT': int(get_env_var('WEAVIATE_PORT', '8080')),
    'TIMEOUT': int(get_env_var('WEAVIATE_TIMEOUT', '30')),
    'URL': f"http://{get_env_var('WEAVIATE_HOST', 'localhost')}:{get_env_var('WEAVIATE_PORT', '8080')}",
}

# 嵌入模型配置
EMBEDDING_CONFIG = {
    'MODEL_NAME': get_env_var('EMBEDDING_MODEL', 'sentence-transformers/all-mpnet-base-v2'),
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

# 处理配置 - 与PDF处理工具保持一致，使用大分块优化
PROCESSING_CONFIG = {
    # 与pdf_utils.GlobalConfig保持一致，默认约700 token，10-12%重叠
    'CHUNK_SIZE': int(get_env_var('CHUNK_SIZE', '700')),
    'CHUNK_OVERLAP': int(get_env_var('CHUNK_OVERLAP', '80')),
    'MAX_WORKERS': int(get_env_var('MAX_WORKERS', '4')),
    'BATCH_SIZE': int(get_env_var('BATCH_SIZE', '10')),
}

# 创建必要的目录
def ensure_directories():
    """确保必要的目录存在"""
    directories = [
        MEDIA_ROOT,
        STATIC_ROOT,
        EMBEDDING_CONFIG['CACHE_DIR'],
        MAIN_LOG_FILE.parent,
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

# 初始化时创建目录
ensure_directories()
