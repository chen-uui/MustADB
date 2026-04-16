from django.core.management.base import BaseCommand
from pdf_processor.weaviate_services import WeaviateVectorService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '检查向量数据库状态'
    
    def handle(self, *args, **options):
        try:
            service = WeaviateVectorService()
            
            # 获取统计信息
            stats = service.get_collection_stats()
            
            self.stdout.write(self.style.SUCCESS('向量数据库状态:'))
            self.stdout.write(f"  集合名称: {stats.get('collection_name', 'N/A')}")
            self.stdout.write(f"  文档分块总数: {stats.get('total_chunks', 0)}")
            self.stdout.write(f"  唯一文档数: {stats.get('unique_documents', 0)}")
            self.stdout.write(f"  嵌入模型: {stats.get('embedding_model', 'N/A')}")
            self.stdout.write(f"  Weaviate URL: {stats.get('weaviate_url', 'N/A')}")
            self.stdout.write(f"  连接状态: {'正常' if service.is_healthy() else '异常'}")
            
            if 'error' in stats:
                self.stdout.write(f"  错误信息: {stats['error']}")
            
            # 获取示例文档
            sample_docs = service.get_all_chunks(limit=3)
            if sample_docs:
                self.stdout.write("\n示例文档片段:")
                for i, doc in enumerate(sample_docs, 1):
                    self.stdout.write(f"  {i}. 文档ID: {doc.get('document_id', 'N/A')}")
                    self.stdout.write(f"     标题: {doc.get('title', 'N/A')}")
                    self.stdout.write(f"     内容: {doc.get('content', 'N/A')[:100]}...")
                    self.stdout.write("")
            else:
                self.stdout.write("\n暂无文档数据")
            
        except Exception as e:
            logger.error(f"检查向量数据库状态失败: {e}")
            self.stdout.write(
                self.style.ERROR(f'检查失败: {e}')
            )
        finally:
            # 确保关闭连接
            try:
                service.close()
            except:
                pass