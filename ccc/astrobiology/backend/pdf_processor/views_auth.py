"""
用户认证相关的API视图
提供登录、注册、用户信息管理功能
"""

import logging
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from .user_utils import serialize_user_info

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """用户登录"""
    try:
        data = request.data
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return Response({
                'success': False,
                'error': '用户名和密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证用户
        user = authenticate(username=username, password=password)
        if not user:
            return Response({
                'success': False,
                'error': '用户名或密码错误'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({
                'success': False,
                'error': '用户账户已被禁用'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # 获取或创建token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'success': True,
            'token': token.key,
            'user': serialize_user_info(user)
        })
        
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return Response({
            'success': False,
            'error': '登录过程中发生错误'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """用户注册"""
    try:
        data = request.data
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        # 验证必填字段
        if not username or not password:
            return Response({
                'success': False,
                'error': '用户名和密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(password) < 6:
            return Response({
                'success': False,
                'error': '密码长度至少6位'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            return Response({
                'success': False,
                'error': '用户名已存在'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查邮箱是否已存在
        if email and User.objects.filter(email=email).exists():
            return Response({
                'success': False,
                'error': '邮箱已被使用'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建用户
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        
        # 创建token
        token = Token.objects.create(user=user)
        
        user_info = serialize_user_info(user)
        # 注册时不需要last_login
        user_info.pop('last_login', None)
        
        return Response({
            'success': True,
            'message': '注册成功',
            'token': token.key,
            'user': user_info
        }, status=status.HTTP_201_CREATED)
        
    except IntegrityError as e:
        logger.error(f"注册失败 - 数据完整性错误: {str(e)}")
        return Response({
            'success': False,
            'error': '用户名或邮箱已存在'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"注册失败: {str(e)}")
        return Response({
            'success': False,
            'error': '注册过程中发生错误'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    """获取当前用户信息"""
    try:
        user = request.user
        return Response({
            'success': True,
            'user': serialize_user_info(user)
        })
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        return Response({
            'success': False,
            'error': '获取用户信息失败'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """用户登出"""
    try:
        # 删除用户的token
        Token.objects.filter(user=request.user).delete()
        
        return Response({
            'success': True,
            'message': '登出成功'
        })
    except Exception as e:
        logger.error(f"登出失败: {str(e)}")
        return Response({
            'success': False,
            'error': '登出过程中发生错误'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """更新用户资料"""
    try:
        user = request.user
        data = request.data
        
        # 更新允许修改的字段
        if 'email' in data:
            email = data['email'].strip()
            if email and User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({
                    'success': False,
                    'error': '邮箱已被其他用户使用'
                }, status=status.HTTP_400_BAD_REQUEST)
            user.email = email
        
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        
        user.save()
        
        return Response({
            'success': True,
            'message': '资料更新成功',
            'user': serialize_user_info(user)
        })
        
    except Exception as e:
        logger.error(f"更新用户资料失败: {str(e)}")
        return Response({
            'success': False,
            'error': '更新资料过程中发生错误'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """修改密码"""
    try:
        user = request.user
        data = request.data
        
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return Response({
                'success': False,
                'error': '旧密码和新密码不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if len(new_password) < 6:
            return Response({
                'success': False,
                'error': '新密码长度至少6位'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证旧密码
        if not user.check_password(old_password):
            return Response({
                'success': False,
                'error': '旧密码错误'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 设置新密码
        user.set_password(new_password)
        user.save()
        
        # 删除旧token，强制重新登录
        Token.objects.filter(user=user).delete()
        
        return Response({
            'success': True,
            'message': '密码修改成功，请重新登录'
        })
        
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        return Response({
            'success': False,
            'error': '修改密码过程中发生错误'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)