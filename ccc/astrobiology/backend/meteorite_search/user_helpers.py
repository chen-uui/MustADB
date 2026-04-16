"""
用户相关的辅助函数
用于减少代码重复，统一用户获取逻辑
"""
from django.contrib.auth.models import User
from typing import Tuple


def get_or_create_system_user() -> Tuple[User, bool]:
    """
    获取或创建系统默认用户
    避免在多个视图中重复编写相同的用户创建代码
    
    Returns:
        (User, bool): 用户对象和是否新创建的标志
    """
    return User.objects.get_or_create(
        username='system_user',
        defaults={
            'email': 'system@example.com',
            'first_name': 'System',
            'last_name': 'User',
            'is_active': True,
            'is_staff': False,
            'is_superuser': False
        }
    )

