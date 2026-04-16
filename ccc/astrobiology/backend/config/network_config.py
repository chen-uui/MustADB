"""
网络配置 - 处理SSL连接和代理问题
"""
import os
import ssl
import certifi
from typing import Dict, Any

class NetworkConfig:
    """网络配置管理器"""
    
    @staticmethod
    def setup_ssl_context():
        """设置SSL上下文以解决连接问题"""
        # 使用certifi提供的CA证书
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context
    
    @staticmethod
    def get_request_kwargs():
        """获取requests库的默认参数"""
        return {
            'verify': False,  # 禁用SSL验证
            'timeout': 30,
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
    
    @staticmethod
    def setup_hf_tokenizer():
        """设置Hugging Face tokenizer配置"""
        # 禁用SSL验证的tokenizer配置
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        
        # 设置本地缓存目录
        cache_dir = os.path.join(os.path.dirname(__file__), '..', 'models', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        return {
            'local_files_only': True,  # 优先使用本地文件
            'cache_dir': cache_dir,
            'trust_remote_code': True,
            'force_download': False,
            'resume_download': True
        }