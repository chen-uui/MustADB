from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authtoken.models import Token


class BearerTokenAuthentication(TokenAuthentication):
    """
    自定义Bearer Token认证类
    支持 'Bearer <token>' 格式的Authorization头
    """
    keyword = 'Bearer'
    
    def authenticate_credentials(self, key):
        """
        验证token凭据
        如果token不存在或无效，抛出AuthenticationFailed异常
        """
        try:
            token = Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')
        
        if not token.user.is_active:
            raise AuthenticationFailed('User inactive or deleted.')
        
        return (token.user, token)