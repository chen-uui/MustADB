"""
Django管理命令：从现有RAG系统中提取陨石数据
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
import logging
import json

from pdf_processor.rag_meteorite_extractor import rag_meteorite_extractor

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '从现有RAG系统中提取陨石数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--query',
            type=str,
            default='meteorite',
            help='搜索查询词 (默认: meteorite)'
        )
        parser.add_argument(
            '--max-docs',
            type=int,
            default=20,
            help='最大处理文档数 (默认: 20)'
        )
        parser.add_argument(
            '--keywords',
            type=str,
            nargs='+',
            help='关键词列表，用空格分隔'
        )
        parser.add_argument(
            '--meteorite-types',
            type=str,
            nargs='+',
            help='陨石类型列表，用空格分隔'
        )
        parser.add_argument(
            '--stats-only',
            action='store_true',
            help='仅显示统计信息'
        )
        parser.add_argument(
            '--count-docs',
            action='store_true',
            help='统计可用文档数量'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('开始从现有RAG系统中提取陨石数据...')
        )
        
        try:
            # 初始化提取器
            if not rag_meteorite_extractor.initialize_services():
                raise CommandError('服务初始化失败')
            
            # 仅显示统计信息
            if options['stats_only']:
                self.show_statistics()
                return
            
            # 统计可用文档数量
            if options['count_docs']:
                self.count_available_documents(options['query'])
                return
            
            # 执行数据提取
            task = None
            
            if options['keywords']:
                # 根据关键词提取
                self.stdout.write(f"使用关键词提取: {options['keywords']}")
                task = rag_meteorite_extractor.extract_by_keywords(
                    keywords=options['keywords'],
                    max_documents=options['max_docs']
                )
            elif options['meteorite_types']:
                # 根据陨石类型提取
                self.stdout.write(f"使用陨石类型提取: {options['meteorite_types']}")
                task = rag_meteorite_extractor.extract_by_meteorite_types(
                    meteorite_types=options['meteorite_types'],
                    max_documents=options['max_docs']
                )
            else:
                # 默认查询提取
                self.stdout.write(f"使用查询词提取: {options['query']}")
                task = rag_meteorite_extractor.extract_from_existing_documents(
                    search_query=options['query'],
                    max_documents=options['max_docs']
                )
            
            # 显示提取结果
            self.show_extraction_results(task)
            
        except Exception as e:
            logger.error(f"提取过程中出错: {str(e)}")
            raise CommandError(f'提取失败: {str(e)}')

    def show_statistics(self):
        """显示统计信息"""
        self.stdout.write(self.style.HTTP_INFO('\n=== 提取统计信息 ==='))
        
        try:
            stats = rag_meteorite_extractor.get_extraction_statistics()
            
            # 显示提取统计
            extraction_stats = stats.get('extraction_stats', {})
            self.stdout.write(f"总任务数: {extraction_stats.get('total_tasks', 0)}")
            self.stdout.write(f"成功提取: {extraction_stats.get('successful_extractions', 0)}")
            self.stdout.write(f"失败提取: {extraction_stats.get('failed_extractions', 0)}")
            self.stdout.write(f"已处理文档: {extraction_stats.get('documents_processed', 0)}")
            
            # 显示提取器统计
            extractor_stats = stats.get('extractor_stats', {})
            if extractor_stats:
                self.stdout.write(f"\n提取器统计:")
                for key, value in extractor_stats.items():
                    self.stdout.write(f"  {key}: {value}")
            
            # 显示存储统计
            storage_stats = stats.get('storage_stats', {})
            if storage_stats:
                self.stdout.write(f"\n存储统计:")
                for key, value in storage_stats.items():
                    self.stdout.write(f"  {key}: {value}")
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'获取统计信息失败: {str(e)}')
            )

    def count_available_documents(self, query):
        """统计可用文档数量"""
        self.stdout.write(self.style.HTTP_INFO(f'\n=== 统计可用文档数量 (查询: {query}) ==='))
        
        try:
            count = rag_meteorite_extractor.get_available_document_count(query)
            self.stdout.write(f"找到 {count} 个相关文档")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'统计文档数量失败: {str(e)}')
            )

    def show_extraction_results(self, task):
        """显示提取结果"""
        if not task:
            self.stdout.write(self.style.ERROR('提取任务为空'))
            return
        
        self.stdout.write(self.style.HTTP_INFO(f'\n=== 提取任务结果 ==='))
        self.stdout.write(f"任务ID: {task.task_id}")
        self.stdout.write(f"查询: {task.query}")
        self.stdout.write(f"状态: {task.status}")
        self.stdout.write(f"最大文档数: {task.max_documents}")
        
        if task.error_message:
            self.stdout.write(
                self.style.ERROR(f"错误信息: {task.error_message}")
            )
        
        if task.results:
            successful = len([r for r in task.results if r.success])
            failed = len([r for r in task.results if not r.success])
            
            self.stdout.write(f"\n处理结果:")
            self.stdout.write(f"  成功: {successful}")
            self.stdout.write(f"  失败: {failed}")
            self.stdout.write(f"  总计: {len(task.results)}")
            
            # 显示成功的提取结果
            if successful > 0:
                self.stdout.write(f"\n成功提取的数据:")
                success_count = 0
                for result in task.results:
                    if result.success and success_count < 5:  # 只显示前5个
                        self.stdout.write(f"  - 提取到 {len(result.meteorite_data)} 条陨石数据")
                        if result.meteorite_data:
                            # 显示第一条数据的简要信息
                            first_data = result.meteorite_data[0]
                            self.stdout.write(f"    示例: {first_data.name} ({first_data.meteorite_type})")
                        success_count += 1
                
                if successful > 5:
                    self.stdout.write(f"  ... 还有 {successful - 5} 个成功结果")
            
            # 显示失败的原因
            if failed > 0:
                self.stdout.write(f"\n失败原因:")
                error_count = 0
                for result in task.results:
                    if not result.success and error_count < 3:  # 只显示前3个错误
                        if result.errors:
                            self.stdout.write(f"  - {result.errors[0]}")
                        error_count += 1
                
                if failed > 3:
                    self.stdout.write(f"  ... 还有 {failed - 3} 个失败结果")
        
        # 显示最新统计信息
        self.stdout.write(f"\n=== 更新后的统计信息 ===")
        self.show_statistics()
        
        self.stdout.write(
            self.style.SUCCESS(f'\n提取任务完成！状态: {task.status}')
        )