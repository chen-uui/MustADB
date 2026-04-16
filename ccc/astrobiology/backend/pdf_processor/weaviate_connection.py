"""
统一的Weaviate连接管理模块
整合所有Weaviate连接创建逻辑
"""
import os

# 禁用 weaviate/tqdm 的进度条输出，避免批处理刷屏
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("WEAVIATE_PROGRESS_BAR_DISABLE", "true")
os.environ.setdefault("WEAVIATE_NO_PROGRESS_BAR", "1")
os.environ.setdefault("WEAVIATE_PROGRESS_BAR", "false")
os.environ.setdefault("DISABLE_TQDM", "1")

import logging
import weaviate
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

class WeaviateConnectionManager:
    """统一的Weaviate连接管理器"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.host = settings.WEAVIATE_CONFIG['HOST']
        self.port = settings.WEAVIATE_CONFIG['PORT']
        self.timeout = settings.WEAVIATE_CONFIG['TIMEOUT']
        self.url = settings.WEAVIATE_CONFIG['URL']
    
    def get_client(self) -> Optional[weaviate.WeaviateClient]:
        """获取Weaviate客户端连接"""
        if self._client is None or not self._client.is_ready():
            self._create_connection()
        return self._client
    
    def _create_connection(self):
        """创建Weaviate连接"""
        try:
            logger.info(f"连接到Weaviate服务器: {self.host}:{self.port}")
            self._client = weaviate.connect_to_local(
                host=self.host,
                port=self.port,
                additional_config=weaviate.config.AdditionalConfig(
                    timeout=weaviate.config.Timeout(
                        init=self.timeout,
                        query=self.timeout,
                        insert=self.timeout
                    )
                )
            )
            
            if self._client.is_ready():
                logger.info("Weaviate连接成功")
            else:
                raise ConnectionError("Weaviate连接失败")
                
        except Exception as e:
            logger.error(f"创建Weaviate连接失败: {e}")
            raise
    
    def test_connection(self) -> bool:
        """测试连接状态"""
        try:
            client = self.get_client()
            if client is not None:
                return client.is_ready()
            return False
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
    
    def close_connection(self):
        """关闭连接"""
        if self._client:
            try:
                self._client.close()
                logger.info("Weaviate连接已关闭")
            except Exception as e:
                logger.error(f"关闭连接失败: {e}")
            finally:
                self._client = None

    def close(self):
        """关闭连接的别名方法，用于兼容性"""
        self.close_connection()

# 全局单例实例
weaviate_connection = WeaviateConnectionManager()