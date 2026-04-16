"""
PostgreSQL数据库配置
专为高性能陨石数据搜索优化
"""

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'astrobiology_db',
        'USER': 'postgres',
        'PASSWORD': 'your_postgres_password',  # 请修改为实际密码
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000ms',
            'sslmode': 'disable',  # 本地开发使用
        },
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
        'ATOMIC_REQUESTS': True,  # 每个请求自动使用事务
    }
}

# PostgreSQL优化配置
POSTGRESQL_OPTIMIZATION = {
    # 连接池配置
    'min_connections': 5,
    'max_connections': 20,
    'connection_timeout': 10,
    
    # 查询优化
    'work_mem': '64MB',
    'maintenance_work_mem': '256MB',
    'effective_cache_size': '1GB',
    
    # 全文搜索配置
    'default_text_search_config': 'english',
    'full_text_search_language': 'english',
    
    # JSON配置
    'jsonb_ops': True,  # 启用JSONB操作符优化
}

# PostgreSQL特有功能配置
POSTGRESQL_FEATURES = {
    # 全文搜索配置
    'full_text_search': {
        'search_vector_config': 'english',
        'search_vector_weights': 'A',  # 权重设置
    },
    
    # JSON字段优化
    'json_optimization': {
        'gin_indexes': True,
        'jsonb_storage': True,
    },
    
    # 分区表配置（大数据量时使用）
    'partitioning': {
        'enabled': False,  # 默认关闭，数据量大时开启
        'partition_key': 'classification',
        'partition_strategy': 'list',
    },
}

# 数据库初始化SQL
DATABASE_INIT_SQL = [
    """
    CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- 用于相似度搜索
    """,
    """
    CREATE EXTENSION IF NOT EXISTS unaccent;  -- 用于重音字符处理
    """,
    """
    -- 创建全文搜索配置
    ALTER TEXT SEARCH CONFIGURATION english ADD MAPPING FOR hword, hword_part, word WITH english_stem;
    """,
]