from django.core.management.base import BaseCommand
from django.conf import settings
from pdf_processor.services import VectorSearchService
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '初始化向量数据库'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有向量数据库',
        )
    
    def handle(self, *args, **options):
        try:
            service = VectorSearchService()
            
            if options['clear']:
                # 清除现有集合
                try:
                    service.chroma_client.delete_collection("pdf_documents")
                    self.stdout.write(
                        self.style.SUCCESS('成功清除现有向量数据库')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'清除数据库时出错: {e}')
                    )
            
            # 重新创建集合
            service.collection = service.chroma_client.get_or_create_collection(
                name="pdf_documents",
                metadata={"hnsw:space": "cosine"}
            )
            
            # 显示统计信息
            count = service.collection.count()
            self.stdout.write(
                self.style.SUCCESS(f'向量数据库初始化完成，当前包含 {count} 个文档')
            )
            
        except Exception as e:
            logger.error(f"初始化向量数据库失败: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f'初始化失败: {str(e)}')
            )