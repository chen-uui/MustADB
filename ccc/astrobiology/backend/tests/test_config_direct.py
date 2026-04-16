#!/usr/bin/env python
"""
直接测试配置，不通过Django
"""
import os
import sys

# 设置路径
sys.path.insert(0, '.')

print("🔍 直接测试配置...")
print(f"当前工作目录: {os.getcwd()}")
print(f"Python路径: {sys.path[0]}")

# 检查环境变量
print(f"\n环境变量检查:")
print(f"CHUNK_SIZE: {os.getenv('CHUNK_SIZE', 'not set')}")
print(f"CHUNK_OVERLAP: {os.getenv('CHUNK_OVERLAP', 'not set')}")

# 直接导入模块
print(f"\n直接导入pdf_utils...")
import pdf_processor.pdf_utils
print(f"模块文件路径: {pdf_processor.pdf_utils.__file__}")

# 检查配置
print(f"\n配置检查:")
print(f"CHUNK_SIZE: {pdf_processor.pdf_utils.GlobalConfig.CHUNK_SIZE}")
print(f"CHUNK_OVERLAP: {pdf_processor.pdf_utils.GlobalConfig.CHUNK_OVERLAP}")

# 检查是否有其他GlobalConfig类
print(f"\n检查是否有其他GlobalConfig类...")
import inspect
for name, obj in inspect.getmembers(pdf_processor.pdf_utils):
    if name == 'GlobalConfig':
        print(f"找到GlobalConfig: {obj}")
        print(f"CHUNK_SIZE: {obj.CHUNK_SIZE}")
        print(f"CHUNK_OVERLAP: {obj.CHUNK_OVERLAP}")
