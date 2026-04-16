#!/usr/bin/env python
"""
初始化PDF问答系统
"""

from django.core.management.base import BaseCommand
from pdf_processor.haystack_qa_service_optimized import OptimizedPDFQAService
from pdf_processor.models import PDFDocument
from haystack import Document
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '初始化PDF问答系统'

    def handle(self, *args, **options):
        try:
            self.stdout.write(self.style.SUCCESS('开始初始化PDF问答系统...'))
            
            # 创建服务实例
            service = OptimizedPDFQAService()
            
            # 加载所有PDF文档
            pdf_docs = PDFDocument.objects.filter(processed=True)
            self.stdout.write(f'找到 {pdf_docs.count()} 个已处理的PDF文档')
            
            if pdf_docs.exists():
                # 创建Haystack文档
                documents = []
                for pdf_doc in pdf_docs:
                    doc = Document(
                        content=pdf_doc.title,  # 使用标题作为内容
                        meta={
                            'filename': pdf_doc.filename,
                            'title': pdf_doc.title,
                            'file_path': pdf_doc.file_path,
                            'category': pdf_doc.category,
                            'page_count': pdf_doc.page_count
                        }
                    )
                    documents.append(doc)
                
                # 初始化系统
                success = service.initialize(documents)
                if success:
                    self.stdout.write(self.style.SUCCESS('PDF问答系统初始化成功！'))
                    
                    # 加载Mistral模型
                    self.stdout.write('正在加载Mistral模型...')
                    service._initialize_mistral_model()
                    self.stdout.write(self.style.SUCCESS('Mistral模型加载完成！'))
                    
                    # 检查最终状态
                    status = service.get_status()
                    self.stdout.write(f'系统状态: {status}')
                    
                else:
                    self.stdout.write(self.style.ERROR('系统初始化失败'))
                    
            else:
                self.stdout.write(self.style.WARNING('没有找到已处理的PDF文档'))
                
        except Exception as e:
            logger.error(f'初始化失败: {e}')
            self.stdout.write(self.style.ERROR(f'初始化失败: {e}'))