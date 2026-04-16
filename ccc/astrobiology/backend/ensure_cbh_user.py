#!/usr/bin/env python
"""
确保cbh用户存在并获取token
"""
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.django_settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

username = 'cbh'
password = 'cbh010920'

# 检查用户是否存在
user, created = User.objects.get_or_create(
    username=username,
    defaults={
        'email': 'cbh@astrobiology.com',
        'first_name': 'CBH',
        'last_name': 'User',
        'is_staff': True,
        'is_superuser': True,
    }
)

# 更新密码（无论用户是否新创建）
user.set_password(password)
user.save()

if created:
    print(f"✅ 创建新用户: {username}")
else:
    print(f"ℹ️  用户已存在: {username}，已更新密码")

# 创建或获取token
token, token_created = Token.objects.get_or_create(user=user)

if token_created:
    print(f"✅ 创建新token: {token.key}")
else:
    print(f"ℹ️  Token已存在: {token.key}")

print("\n" + "="*50)
print("用户认证信息:")
print(f"用户名: {username}")
print(f"密码: {password}")
print(f"Token: {token.key}")
print("="*50)

