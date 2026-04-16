"""
用户相关的工具函数
用于减少代码重复，统一用户信息序列化
"""
from typing import Dict, Any
from django.contrib.auth.models import User


def serialize_user_info(user: User) -> Dict[str, Any]:
    """
    序列化用户信息为标准格式
    避免在多个视图中重复编写相同的序列化代码
    
    Args:
        user: Django User对象
        
    Returns:
        包含用户信息的字典
    """
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined.isoformat(),
        'last_login': user.last_login.isoformat() if user.last_login else None
    }

