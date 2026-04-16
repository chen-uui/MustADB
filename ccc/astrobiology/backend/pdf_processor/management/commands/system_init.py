"""
系统初始化综合管理命令
整合了多个初始化相关的功能：
- RAG系统初始化
- QA系统初始化  
- 向量数据库初始化
- Weaviate初始化
- 增强初始化
"""

import os
import logging
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

from pdf_processor.rag_service import RAGService
from pdf_processor.haystack_qa_service_optimized import OptimizedPDFQAService
from pdf_processor.services import VectorSearchService
from pdf_processor.weaviate_services import WeaviateConfig, WeaviateDocumentProcessor
from pdf_processor.models import PDFDocument
from haystack import Document

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '系统初始化综合命令'

    def add_arguments(self, parser):
        parser.add_argument(
            '--component',
            choices=['rag', 'qa', 'vector', 'weaviate', 'enhanced', 'all'],
            default='all',
            help='选择要初始化的组件'
        )
        parser.add_argument(
            '--force-reinit',
            action='store_true',
            help='强制重新初始化'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有数据库',
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='重新处理所有文档'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=2,
            help='并发工作线程数'
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=None,
            help='文本分块大小'
        )
        parser.add_argument(
            '--chunk-overlap',
            type=int,
            default=None,
            help='分块重叠大小'
        )

    def handle(self, *args, **options):
        component = options['component']
        
        self.stdout.write(self.style.SUCCESS('🚀 开始系统初始化...'))
        
        if component in ['all', 'rag']:
            self.init_rag_system(options)
        
        if component in ['all', 'qa']:
            self.init_qa_system(options)
            
        if component in ['all', 'vector']:
            self.init_vector_db(options)
            
        if component in ['all', 'weaviate']:
            self.init_weaviate(options)
            
        if component in ['all', 'enhanced']:
            self.enhanced_init(options)
            
        self.stdout.write(self.style.SUCCESS('[成功] 系统初始化完成！'))

    def init_rag_system(self, options):
        """初始化RAG系统"""
        self.stdout.write(self.style.SUCCESS('🔧 初始化RAG系统...'))
        
        try:
            # 测试Weaviate连接
            self.stdout.write('🔍 测试Weaviate连接...')
            weaviate_host = os.getenv('WEAVIATE_HOST', 'localhost')
            weaviate_port = os.getenv('WEAVIATE_PORT', '8080')
            
            try:
                response = requests.get(f'http://{weaviate_host}:{weaviate_port}/v1/.well-known/ready', timeout=30)
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS('[成功] Weaviate连接成功'))
                else:
                    self.stdout.write(self.style.ERROR(f'[失败] Weaviate连接失败: {response.status_code}'))
                    return
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'[失败] Weaviate连接失败: {e}'))
                self.stdout.write(self.style.WARNING('请确保Weaviate服务已启动: docker-compose up weaviate'))
                return
            
            # 测试LLM连接
            self.stdout.write('🤖 测试LLM连接...')
            try:
                response = requests.get('http://localhost:11434/api/tags', timeout=30)
                if response.status_code == 200:
                    self.stdout.write(self.style.SUCCESS('[成功] LLM连接成功'))
                else:
                    self.stdout.write(self.style.ERROR(f'[失败] LLM连接失败: {response.status_code}'))
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.WARNING(f'[警告] LLM连接失败: {e}'))
            
            # 创建RAG服务实例
            service = RAGService()
            self.stdout.write(self.style.SUCCESS('[成功] RAG系统初始化完成'))
            
        except Exception as e:
            logger.error(f"RAG系统初始化失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'[失败] RAG系统初始化失败: {str(e)}'))

    def init_qa_system(self, options):
        """初始化QA系统"""
        self.stdout.write(self.style.SUCCESS('🔧 初始化PDF问答系统...'))
        
        try:
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
                        content=pdf_doc.title,
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
                    self.stdout.write(self.style.SUCCESS('[成功] PDF问答系统初始化成功！'))
                    
                    # 加载Mistral模型
                    self.stdout.write('正在加载Mistral模型...')
                    service._initialize_mistral_model()
                    self.stdout.write(self.style.SUCCESS('[成功] Mistral模型加载完成'))
                else:
                    self.stdout.write(self.style.ERROR('[失败] PDF问答系统初始化失败'))
            else:
                self.stdout.write(self.style.WARNING('[警告] 没有找到已处理的PDF文档'))
                
        except Exception as e:
            logger.error(f"QA系统初始化失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'[失败] QA系统初始化失败: {str(e)}'))

    def init_vector_db(self, options):
        """初始化向量数据库"""
        self.stdout.write(self.style.SUCCESS('🔧 初始化向量数据库...'))
        
        try:
            service = VectorSearchService()
            
            if options['clear']:
                # 清除现有集合
                try:
                    service.chroma_client.delete_collection("pdf_documents")
                    self.stdout.write(self.style.SUCCESS('[成功] 成功清除现有向量数据库'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'[警告] 清除数据库时出错: {e}'))
            
            # 重新创建集合
            service.collection = service.chroma_client.get_or_create_collection(
                name="pdf_documents",
                metadata={"hnsw:space": "cosine"}
            )
            
            # 显示统计信息
            count = service.collection.count()
            self.stdout.write(self.style.SUCCESS(f'[成功] 向量数据库初始化完成，当前包含 {count} 个文档'))
            
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'[失败] 向量数据库初始化失败: {str(e)}'))

    def init_weaviate(self, options):
        """初始化Weaviate"""
        self.stdout.write(self.style.SUCCESS('🔧 初始化Weaviate向量数据库...'))
        
        try:
            # 创建处理器实例
            processor = WeaviateDocumentProcessor()
            
            # 获取PDF文档
            if options['reprocess']:
                documents = PDFDocument.objects.all()
                self.stdout.write(f'重新处理所有 {documents.count()} 个文档')
            else:
                documents = PDFDocument.objects.filter(processed=False)
                self.stdout.write(f'处理 {documents.count()} 个未处理文档')
            
            if documents.exists():
                # 处理文档
                for doc in documents:
                    try:
                        processor.process_document(doc)
                        self.stdout.write(f'[成功] 处理完成: {doc.filename}')
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'[失败] 处理失败 {doc.filename}: {e}'))
            else:
                self.stdout.write(self.style.WARNING('[警告] 没有需要处理的文档'))
                
            self.stdout.write(self.style.SUCCESS('[成功] Weaviate初始化完成'))
            
        except Exception as e:
            logger.error(f"Weaviate初始化失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'[失败] Weaviate初始化失败: {str(e)}'))

    def enhanced_init(self, options):
        """增强初始化"""
        self.stdout.write(self.style.SUCCESS('🔧 执行增强初始化...'))
        
        try:
            # 这里可以添加增强初始化的具体逻辑
            # 例如：检查系统依赖、创建必要目录、设置权限等
            
            # 检查必要目录
            pdf_dir = Path(settings.BASE_DIR).parent / 'pdfs'
            if not pdf_dir.exists():
                pdf_dir.mkdir(parents=True, exist_ok=True)
                self.stdout.write(f'[成功] 创建PDF目录: {pdf_dir}')
            
            # 检查数据目录
            data_dir = Path(settings.BASE_DIR).parent / 'data'
            if not data_dir.exists():
                data_dir.mkdir(parents=True, exist_ok=True)
                self.stdout.write(f'[成功] 创建数据目录: {data_dir}')
            
            self.stdout.write(self.style.SUCCESS('[成功] 增强初始化完成'))
            
        except Exception as e:
            logger.error(f"增强初始化失败: {str(e)}")
            self.stdout.write(self.style.ERROR(f'[失败] 增强初始化失败: {str(e)}'))