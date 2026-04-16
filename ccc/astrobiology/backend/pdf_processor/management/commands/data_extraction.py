"""
数据提取管理命令
整合了数据提取相关的功能：
- 陨石数据提取
- Weaviate元数据回填
"""

import os
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateDocumentProcessor

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '数据提取管理命令'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            choices=['meteorite', 'backfill', 'all'],
            default='all',
            help='选择要执行的操作'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='限制处理文档数量'
        )
        parser.add_argument(
            '--category',
            type=str,
            default=None,
            help='按类别过滤'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新处理'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        self.stdout.write(self.style.SUCCESS('🚀 开始数据提取...'))
        
        if action in ['all', 'meteorite']:
            self.extract_meteorite_data(options)
        
        if action in ['all', 'backfill']:
            self.backfill_weaviate_metadata(options)
            
        self.stdout.write(self.style.SUCCESS('[成功] 数据提取完成！'))

    def extract_meteorite_data(self, options):
        """提取陨石数据"""
        self.stdout.write(self.style.SUCCESS('🌠 开始提取陨石数据...'))
        
        try:
            # 构建查询
            queryset = PDFDocument.objects.filter(processed=True)
            
            if options['category']:
                queryset = queryset.filter(category=options['category'])
            
            if options['limit']:
                queryset = queryset[:options['limit']]
            
            total_docs = queryset.count()
            self.stdout.write(f'[文档] 找到 {total_docs} 个待处理文档')
            
            processed_count = 0
            error_count = 0
            
            for i, doc in enumerate(queryset, 1):
                self.stdout.write(f'处理 {i}/{total_docs}: {doc.filename}')
                
                try:
                    # 这里可以添加具体的陨石数据提取逻辑
                    # 例如：使用NLP模型提取陨石相关信息
                    
                    # 模拟数据提取过程
                    self.extract_meteorite_info_from_doc(doc)
                    
                    processed_count += 1
                    self.stdout.write(f'[成功] 提取完成: {doc.filename}')
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f'[失败] 提取失败 {doc.filename}: {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'[成功] 陨石数据提取完成: 成功 {processed_count}, 失败 {error_count}'))
            
        except Exception as e:
            logger.error(f"陨石数据提取失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'[失败] 陨石数据提取失败: {str(e)}'))

    def extract_meteorite_info_from_doc(self, doc):
        """从文档中提取陨石信息"""
        # 这里可以实现具体的陨石信息提取逻辑
        # 例如：
        # 1. 读取PDF内容
        # 2. 使用NLP模型识别陨石名称、分类、发现地点等
        # 3. 提取化学成分、矿物组成等信息
        # 4. 保存到数据库
        
        try:
            import fitz
            pdf_doc = fitz.open(doc.file_path)
            
            # 提取文本内容
            text_content = ""
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                text_content += page.get_text()
            
            pdf_doc.close()
            
            # 这里可以添加NLP处理逻辑
            # 例如：使用正则表达式或机器学习模型提取陨石信息
            
            # 更新文档的处理状态
            doc.processed = True
            doc.save()
            
        except Exception as e:
            raise Exception(f"提取陨石信息失败: {e}")

    def backfill_weaviate_metadata(self, options):
        """回填Weaviate元数据"""
        self.stdout.write(self.style.SUCCESS('[恢复] 开始回填Weaviate元数据...'))
        
        try:
            # 创建Weaviate处理器
            processor = WeaviateDocumentProcessor()
            
            # 获取需要回填的文档
            if options['force']:
                documents = PDFDocument.objects.all()
                self.stdout.write(f'强制回填所有 {documents.count()} 个文档')
            else:
                # 这里可以添加逻辑来识别需要回填的文档
                # 例如：缺少某些元数据字段的文档
                documents = PDFDocument.objects.filter(processed=True)
                self.stdout.write(f'回填 {documents.count()} 个已处理文档')
            
            if options['category']:
                documents = documents.filter(category=options['category'])
            
            if options['limit']:
                documents = documents[:options['limit']]
            
            processed_count = 0
            error_count = 0
            
            for doc in documents:
                try:
                    # 回填元数据
                    self.backfill_document_metadata(doc, processor)
                    
                    processed_count += 1
                    self.stdout.write(f'[成功] 回填完成: {doc.filename}')
                    
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f'[失败] 回填失败 {doc.filename}: {e}'))
            
            self.stdout.write(self.style.SUCCESS(f'[成功] 元数据回填完成: 成功 {processed_count}, 失败 {error_count}'))
            
        except Exception as e:
            logger.error(f"Weaviate元数据回填失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'[失败] 元数据回填失败: {str(e)}'))

    def backfill_document_metadata(self, doc, processor):
        """回填单个文档的元数据"""
        try:
            # 这里可以实现具体的元数据回填逻辑
            # 例如：
            # 1. 从Weaviate中查询文档
            # 2. 更新缺失的元数据字段
            # 3. 重新索引文档
            
            # 检查文档是否存在于Weaviate中
            # 如果不存在，则重新处理
            if not self.document_exists_in_weaviate(doc):
                processor.process_document(doc)
                self.stdout.write(f'[恢复] 重新处理文档: {doc.filename}')
            else:
                # 更新元数据
                self.update_document_metadata(doc)
                self.stdout.write(f'📝 更新元数据: {doc.filename}')
                
        except Exception as e:
            raise Exception(f"回填文档元数据失败: {e}")

    def document_exists_in_weaviate(self, doc):
        """检查文档是否存在于Weaviate中"""
        try:
            # 这里可以实现检查逻辑
            # 例如：通过文档ID或文件名查询Weaviate
            return True  # 临时返回True
            
        except Exception as e:
            logger.warning(f"检查文档存在性失败: {e}")
            return False

    def update_document_metadata(self, doc):
        """更新文档元数据"""
        try:
            # 这里可以实现元数据更新逻辑
            # 例如：
            # 1. 重新提取文档信息
            # 2. 更新数据库记录
            # 3. 同步到Weaviate
            
            # 更新最后修改时间
            from django.utils import timezone
            doc.last_modified = timezone.now()
            doc.save()
            
        except Exception as e:
            raise Exception(f"更新文档元数据失败: {e}")