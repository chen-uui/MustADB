"""
PDF处理器应用配置
"""

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class PdfProcessorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pdf_processor'
    verbose_name = 'PDF处理器'

    def ready(self):
        """应用准备就绪时的初始化操作"""
        try:
            from .startup import configure_runtime
            configure_runtime()
            logger.info("PDF处理器运行环境已初始化")
        except Exception as e:
            logger.error(f"运行环境初始化失败: {str(e)}")

        try:
            # 导入任务恢复服务
            from .task_recovery_service import task_recovery_service

            # 只初始化服务，用户需要手动点击恢复按钮来恢复任务
            logger.info("PDF处理器应用初始化完成，任务恢复服务已准备就绪")

        except Exception as e:
            logger.error(f"PDF处理器应用初始化失败: {str(e)}")
            # 不抛出异常，避免影响应用启动