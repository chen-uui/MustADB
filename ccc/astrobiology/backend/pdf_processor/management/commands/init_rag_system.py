"""
初始化RAG系统的管理命令
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import logging
import time
import requests
from pdf_processor.rag_service import RAGService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '初始化RAG问答系统'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-reinit',
            action='store_true',
            help='强制重新初始化'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 开始初始化RAG系统...'))
        
        try:
            # 创建RAG服务实例
            service = RAGService()
            
            # 测试Weaviate连接
            self.stdout.write('🔍 测试Weaviate连接...')
            try:
                weaviate_host = os.getenv('WEAVIATE_HOST', 'localhost')
                weaviate_port = os.getenv('WEAVIATE_PORT', '8080')
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
                    models = response.json().get('models', [])
                    model_names = [m.get('name', '') for m in models]
                    if 'llama3.1:8b-instruct-q4_K_M' in model_names:
                        self.stdout.write(self.style.SUCCESS('[成功] LLM连接成功，模型 llama3.1:8b-instruct-q4_K_M 可用'))
                    else:
                        self.stdout.write(self.style.ERROR('[失败] LLM模型 llama3.1:8b-instruct-q4_K_M 未找到'))
                        self.stdout.write(self.style.WARNING('请运行: ollama pull llama3.1:8b-instruct-q4_K_M'))
                        return
                else:
                    self.stdout.write(self.style.ERROR(f'[失败] LLM连接失败: {response.status_code}'))
                    return
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'[失败] LLM连接失败: {e}'))
                self.stdout.write(self.style.WARNING('请确保Ollama服务已启动: ollama serve'))
                return
            
            # 初始化RAG服务
            self.stdout.write('⚙️ 初始化RAG服务...')
            service.initialize()
            self.stdout.write(self.style.SUCCESS('[成功] RAG服务初始化完成'))
            
            # 获取状态
            status = service.get_status()
            self.stdout.write(self.style.SUCCESS(f'[统计] 系统状态:'))
            self.stdout.write(f'  - 文档数量: {status["document_count"]}')
            self.stdout.write(f'  - Weaviate连接: {"[成功]" if status["weaviate_connected"] else "[失败]"}')
            self.stdout.write(f'  - LLM连接: {"[成功]" if status["llm_connected"] else "[失败]"}')
            
            if status["document_count"] == 0:
                self.stdout.write(self.style.WARNING('[警告] 当前没有文档，请上传并处理PDF文档'))
            else:
                # 测试问答功能
                self.stdout.write('🧪 测试问答功能...')
                test_result = service.ask_question("What is this document about?", top_k=3)
                self.stdout.write(self.style.SUCCESS('[成功] 问答功能测试完成'))
                self.stdout.write(f'  - 答案长度: {len(test_result.answer)} 字符')
                self.stdout.write(f'  - 相关片段: {test_result.total_contexts} 个')
            
            self.stdout.write(self.style.SUCCESS('🎉 RAG系统初始化完成！'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[失败] 初始化失败: {e}'))
            logger.error(f'RAG系统初始化失败: {e}')