#!/usr/bin/env python
"""
测试配置值
"""
import os
import sys

# 设置路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置环境变量
os.environ.setdefault('DEBUG', 'True')
os.environ.setdefault('SECRET_KEY', 'dev-secret-key')
os.environ.setdefault('DB_NAME', 'astrobiology_db')
os.environ.setdefault('DB_USER', 'postgres')
os.environ.setdefault('DB_PASSWORD', '123456')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_PORT', '5432')

print("环境变量检查:")
print(f"CHUNK_SIZE: {os.getenv('CHUNK_SIZE', 'not set')}")
print(f"CHUNK_OVERLAP: {os.getenv('CHUNK_OVERLAP', 'not set')}")

print("\nPDF_UTILS配置:")
from pdf_processor.pdf_utils import GlobalConfig
print(f"GlobalConfig.CHUNK_SIZE: {GlobalConfig.CHUNK_SIZE}")
print(f"GlobalConfig.CHUNK_OVERLAP: {GlobalConfig.CHUNK_OVERLAP}")

print("\nDjango配置:")
# 直接读取django_settings.py
import importlib.util
spec = importlib.util.spec_from_file_location("django_settings", "config/django_settings.py")
django_settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(django_settings)
print(f"PROCESSING_CONFIG['CHUNK_SIZE']: {django_settings.PROCESSING_CONFIG['CHUNK_SIZE']}")
print(f"PROCESSING_CONFIG['CHUNK_OVERLAP']: {django_settings.PROCESSING_CONFIG['CHUNK_OVERLAP']}")

print("\n检查get_env_var函数:")
print(f"get_env_var('CHUNK_SIZE', '20000'): {django_settings.get_env_var('CHUNK_SIZE', '20000')}")
print(f"get_env_var('CHUNK_OVERLAP', '2000'): {django_settings.get_env_var('CHUNK_OVERLAP', '2000')}")
