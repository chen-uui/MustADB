"""
创建直接处理数据库表的Django管理命令
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command


class Command(BaseCommand):
    help = '创建直接处理系统的数据库表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新创建表（删除现有表）',
        )

    def handle(self, *args, **options):
        self.stdout.write('开始创建直接处理系统数据库表...')
        
        try:
            # 创建迁移文件
            self.stdout.write('创建迁移文件...')
            call_command('makemigrations', 'pdf_processor')
            
            # 应用迁移
            self.stdout.write('应用迁移...')
            call_command('migrate', 'pdf_processor')
            
            # 创建索引
            self._create_indexes()
            
            self.stdout.write(
                self.style.SUCCESS('成功创建直接处理系统数据库表！')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'创建数据库表时出错: {str(e)}')
            )
            raise

    def _create_indexes(self):
        """创建数据库索引"""
        self.stdout.write('创建数据库索引...')
        
        with connection.cursor() as cursor:
            # 创建直接处理结果表的索引
            indexes = [
                'CREATE INDEX IF NOT EXISTS idx_direct_processing_results_created_at ON direct_processing_results(created_at);',
                'CREATE INDEX IF NOT EXISTS idx_direct_processing_results_status ON direct_processing_results(status);',
                'CREATE INDEX IF NOT EXISTS idx_direct_processing_results_confidence ON direct_processing_results(confidence_score);',
                'CREATE INDEX IF NOT EXISTS idx_direct_processing_results_method ON direct_processing_results(extraction_method);',
                
                # 创建处理任务表的索引
                'CREATE INDEX IF NOT EXISTS idx_processing_tasks_task_id ON processing_tasks(task_id);',
                'CREATE INDEX IF NOT EXISTS idx_processing_tasks_status ON processing_tasks(status);',
                'CREATE INDEX IF NOT EXISTS idx_processing_tasks_created_at ON processing_tasks(created_at);',
                
                # 创建处理日志表的索引
                'CREATE INDEX IF NOT EXISTS idx_processing_logs_task_id ON processing_logs(task_id);',
                'CREATE INDEX IF NOT EXISTS idx_processing_logs_level ON processing_logs(level);',
                'CREATE INDEX IF NOT EXISTS idx_processing_logs_timestamp ON processing_logs(timestamp);',
                
                # 创建处理统计表的索引
                'CREATE INDEX IF NOT EXISTS idx_processing_statistics_date ON processing_statistics(date);',
                
                # 创建系统配置表的索引
                'CREATE INDEX IF NOT EXISTS idx_system_configurations_key ON system_configurations(key);',
                
                # 创建处理模板表的索引
                'CREATE INDEX IF NOT EXISTS idx_processing_templates_name ON processing_templates(name);',
                'CREATE INDEX IF NOT EXISTS idx_processing_templates_active ON processing_templates(is_active);',
            ]
            
            for index_sql in indexes:
                try:
                    cursor.execute(index_sql)
                    self.stdout.write(f'创建索引: {index_sql.split()[5]}')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'创建索引失败: {e}')
                    )
        
        self.stdout.write('数据库索引创建完成！')
