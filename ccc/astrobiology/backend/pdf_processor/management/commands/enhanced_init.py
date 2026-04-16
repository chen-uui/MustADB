#!/usr/bin/env python
"""
增强版PDF问答系统初始化命令
使用新的增强版服务
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
from pathlib import Path
import logging
from tqdm import tqdm

from pdf_processor.models import PDFDocument, DocumentChunk
from pdf_processor.enhanced_services import DocumentProcessor, ProcessingConfig

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '使用增强版服务初始化PDF问答系统'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='重新处理所有已处理的文档'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=None,
            help='分块大小 (默认使用全局配置)'
        )
        parser.add_argument(
            '--chunk-overlap',
            type=int,
            default=None,
            help='分块重叠大小 (默认使用全局配置)'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=2,
            help='并发工作线程数 (默认: 2)'
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.SUCCESS('🚀 开始增强版PDF问答系统初始化...'))
            
            # 配置 - 使用统一配置
            from pdf_processor.pdf_utils import GlobalConfig
            
            config = ProcessingConfig(
                chunk_size=options['chunk_size'] or GlobalConfig.CHUNK_SIZE,
                chunk_overlap=options['chunk_overlap'] or GlobalConfig.CHUNK_OVERLAP
            )
            
            # 创建处理器
            processor = DocumentProcessor(config)
            
            # 获取文档列表
            if options['reprocess']:
                pdf_docs = PDFDocument.objects.all()
                self.stdout.write(f'📋 找到 {pdf_docs.count()} 个文档(包括已处理)')
            else:
                pdf_docs = PDFDocument.objects.filter(processed=False)
                self.stdout.write(f'📋 找到 {pdf_docs.count()} 个未处理文档')
            
            if not pdf_docs.exists():
                self.stdout.write(self.style.WARNING('[警告]  没有找到PDF文档'))
                return
            
            # 如果重新处理，先清理现有数据
            if options['reprocess']:
                self.stdout.write('🧹 清理现有向量数据...')
                for doc in pdf_docs:
                    processor.vector_service.delete_document(str(doc.id))
                
                # 清理数据库中的分块
                DocumentChunk.objects.all().delete()
                
                # 重置处理状态
                pdf_docs.update(processed=False, processing_error=None)
            
            # 处理文档
            pdf_paths = [doc.file_path for doc in pdf_docs]
            metadata_list = [
                {
                    "title": doc.title,
                    "authors": doc.authors or '',
                    "year": str(doc.year) if doc.year else '',
                    "journal": doc.journal or '',
                    "doi": doc.doi or '',
                    "abstract": doc.abstract or '',
                    "keywords": doc.keywords or '',
                    "category": doc.category,
                    "upload_date": str(doc.upload_date)
                }
                for doc in pdf_docs
            ]
            
            self.stdout.write('[恢复] 开始处理文档...')
            results = processor.process_documents_batch(
                pdf_paths,
                max_workers=options['workers'],
                metadata_list=metadata_list
            )
            
            # 更新数据库状态
            success_count = 0
            for doc, result in zip(pdf_docs, results):
                if result.get("status") == "success":
                    doc.processed = True
                    doc.processing_error = None
                    doc.page_count = result.get("total_pages", 0)
                    doc.save()
                    success_count += 1
                    
                    # 保存分块信息
                    for i, chunk_id in enumerate(result.get("chunk_ids", [])):
                        DocumentChunk.objects.create(
                            document=doc,
                            content="",  # 实际内容存储在向量数据库中
                            page_number=1,  # 简化的页码
                            chunk_index=i,
                            embedding_id=chunk_id
                        )
                else:
                    doc.processed = False
                    doc.processing_error = result.get("error", "未知错误")
                    doc.save()
            
            # 显示统计信息
            stats = processor.vector_service.get_collection_stats()
            
            self.stdout.write(self.style.SUCCESS(f'[成功] 处理完成!'))
            self.stdout.write(f'   成功处理: {success_count} 个文档')
            self.stdout.write(f'   失败处理: {len(results) - success_count} 个文档')
            self.stdout.write(f'   向量文档总数: {stats["total_documents"]}')
            self.stdout.write(f'   嵌入模型: {stats["embedding_model"]}')
            
            # 测试搜索功能
            self.stdout.write('🔍 测试搜索功能...')
            test_results = processor.search_documents("测试", n_results=1)
            if test_results:
                self.stdout.write(self.style.SUCCESS('   搜索功能正常'))
            else:
                self.stdout.write(self.style.WARNING('   搜索功能待验证'))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'[失败] 初始化失败: {str(e)}')
            )
            logger.exception("增强版初始化失败")