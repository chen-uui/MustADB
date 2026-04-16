#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# 加载环境变量
try:
    from dotenv import load_dotenv
    # 查找.env文件的路径
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # 如果没有安装python-dotenv，跳过

# 应用兼容性修复
try:
    import huggingface_hub
    if not hasattr(huggingface_hub, 'cached_download'):
        from huggingface_hub import hf_hub_download
        huggingface_hub.cached_download = hf_hub_download
except ImportError:
    pass  # huggingface_hub未安装，跳过兼容性修复
except Exception as e:
    pass  # 静默处理兼容性问题

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
