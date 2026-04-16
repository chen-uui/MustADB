"""
数据库优化配置
用于处理大规模数据的配置
"""

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'astrobiology_db',
        'USER': 'astro_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000ms'
        },
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
    }
}

# 连接池配置
DATABASE_POOL = {
    'default': {
        'max_overflow': 10,
        'pool_size': 20,
        'recycle': 3600,
        'timeout': 30,
    }
}

# 分片配置
DATABASE_SHARDING = {
    'meteorites': {
        'shard_key': 'classification',
        'shards': {
            'carbonaceous': 'meteorites_carbon',
            'ordinary': 'meteorites_ordinary',
            'iron': 'meteorites_iron',
        }
    }
}