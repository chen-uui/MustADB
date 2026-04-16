#!/usr/bin/env python
"""
测试Django设置过程中的配置变化
"""
import os
import sys

print("🔍 测试Django设置过程中的配置变化...")

# 设置路径
sys.path.insert(0, '.')

print(f"\nDjango设置前环境变量:")
print(f"CHUNK_SIZE: {os.getenv('CHUNK_SIZE', 'not set')}")
print(f"CHUNK_OVERLAP: {os.getenv('CHUNK_OVERLAP', 'not set')}")

# 设置Django
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')

print(f"\nDjango设置后环境变量:")
print(f"CHUNK_SIZE: {os.getenv('CHUNK_SIZE', 'not set')}")
print(f"CHUNK_OVERLAP: {os.getenv('CHUNK_OVERLAP', 'not set')}")

# 初始化Django
django.setup()

print(f"\nDjango初始化后环境变量:")
print(f"CHUNK_SIZE: {os.getenv('CHUNK_SIZE', 'not set')}")
print(f"CHUNK_OVERLAP: {os.getenv('CHUNK_OVERLAP', 'not set')}")

# 导入配置
from pdf_processor.pdf_utils import GlobalConfig
print(f"\nGlobalConfig配置:")
print(f"CHUNK_SIZE: {GlobalConfig.CHUNK_SIZE}")
print(f"CHUNK_OVERLAP: {GlobalConfig.CHUNK_OVERLAP}")
