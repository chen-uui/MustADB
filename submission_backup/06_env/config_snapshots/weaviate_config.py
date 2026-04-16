"""
Weaviate 连接与配置辅助
抽离连接创建逻辑，便于在不同模块复用与测试
"""

import logging

import weaviate

logger = logging.getLogger(__name__)


def connect_to_local_with_timeout(skip_init_checks: bool = True) -> weaviate.WeaviateClient:
	"""创建本地Weaviate连接，带超时配置并跳过初始化检查。
	与现有实现保持兼容。
	"""
	try:
		import weaviate.classes.init as wv_init
		client = weaviate.connect_to_local(
			additional_config=wv_init.AdditionalConfig(
				timeout=wv_init.Timeout(init=30)
			),
			skip_init_checks=skip_init_checks,
		)
		return client
	except Exception as e:
		logger.error(f"创建Weaviate本地连接失败: {e}")
		raise
