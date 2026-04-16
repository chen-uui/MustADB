"""
初始化直接处理系统的Django管理命令
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ..models.direct_processing_models import SystemConfiguration, ProcessingTemplate


class Command(BaseCommand):
    help = '初始化直接处理系统'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='重置系统配置',
        )

    def handle(self, *args, **options):
        self.stdout.write('开始初始化直接处理系统...')
        
        try:
            # 初始化系统配置
            self._init_system_configurations(options['reset'])
            
            # 初始化处理模板
            self._init_processing_templates(options['reset'])
            
            # 创建默认用户（如果不存在）
            self._create_default_user()
            
            self.stdout.write(
                self.style.SUCCESS('直接处理系统初始化完成！')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'初始化系统时出错: {str(e)}')
            )
            raise

    def _init_system_configurations(self, reset=False):
        """初始化系统配置"""
        self.stdout.write('初始化系统配置...')
        
        if reset:
            SystemConfiguration.objects.all().delete()
            self.stdout.write('已重置系统配置')
        
        # 默认系统配置
        configurations = [
            {
                'key': 'llm_base_url',
                'value': 'http://localhost:11434',
                'description': 'LLM服务基础URL',
                'config_type': 'string'
            },
            {
                'key': 'llm_model',
                'value': 'llama3.1:8b',
                'description': 'LLM模型名称',
                'config_type': 'string'
            },
            {
                'key': 'llm_timeout',
                'value': '300',
                'description': 'LLM请求超时时间（秒）',
                'config_type': 'integer'
            },
            {
                'key': 'max_file_size',
                'value': '52428800',
                'description': '最大文件大小（字节）',
                'config_type': 'integer'
            },
            {
                'key': 'max_text_length',
                'value': '100000',
                'description': '最大文本长度',
                'config_type': 'integer'
            },
            {
                'key': 'confidence_threshold',
                'value': '0.6',
                'description': '置信度阈值',
                'config_type': 'float'
            },
            {
                'key': 'enable_validation',
                'value': 'true',
                'description': '是否启用结果验证',
                'config_type': 'boolean'
            },
            {
                'key': 'enable_logging',
                'value': 'true',
                'description': '是否启用日志记录',
                'config_type': 'boolean'
            },
            {
                'key': 'log_level',
                'value': 'INFO',
                'description': '日志级别',
                'config_type': 'string'
            },
            {
                'key': 'batch_size',
                'value': '10',
                'description': '批量处理大小',
                'config_type': 'integer'
            }
        ]
        
        for config in configurations:
            obj, created = SystemConfiguration.objects.get_or_create(
                key=config['key'],
                defaults={
                    'value': config['value'],
                    'description': config['description'],
                    'config_type': config['config_type']
                }
            )
            if created:
                self.stdout.write(f'创建配置: {config["key"]}')
            else:
                self.stdout.write(f'配置已存在: {config["key"]}')

    def _init_processing_templates(self, reset=False):
        """初始化处理模板"""
        self.stdout.write('初始化处理模板...')
        
        if reset:
            ProcessingTemplate.objects.all().delete()
            self.stdout.write('已重置处理模板')
        
        # 默认处理模板
        templates = [
            {
                'name': '标准分析模板',
                'description': '标准的陨石论文分析模板',
                'prompt_template': '你是一个专业的天体生物学研究助手...',
                'processing_options': {
                    'focus': 'comprehensive',
                    'detail_level': 'high',
                    'language': 'chinese'
                },
                'validation_rules': {
                    'min_confidence': 0.6,
                    'required_fields': ['meteorite_data', 'organic_compounds'],
                    'validation_checks': ['completeness', 'consistency', 'format']
                },
                'is_default': True
            },
            {
                'name': '陨石数据提取模板',
                'description': '专注于陨石数据提取的模板',
                'prompt_template': '你是一个专业的陨石学研究助手...',
                'processing_options': {
                    'focus': 'meteorite',
                    'detail_level': 'high',
                    'language': 'chinese'
                },
                'validation_rules': {
                    'min_confidence': 0.7,
                    'required_fields': ['meteorite_data'],
                    'validation_checks': ['meteorite_classification', 'completeness']
                },
                'is_default': False
            },
            {
                'name': '有机化合物分析模板',
                'description': '专注于有机化合物分析的模板',
                'prompt_template': '你是一个专业的有机化学和天体生物学研究助手...',
                'processing_options': {
                    'focus': 'organic',
                    'detail_level': 'high',
                    'language': 'chinese'
                },
                'validation_rules': {
                    'min_confidence': 0.6,
                    'required_fields': ['organic_compounds'],
                    'validation_checks': ['organic_consistency', 'detection_method']
                },
                'is_default': False
            }
        ]
        
        for template in templates:
            obj, created = ProcessingTemplate.objects.get_or_create(
                name=template['name'],
                defaults={
                    'description': template['description'],
                    'prompt_template': template['prompt_template'],
                    'processing_options': template['processing_options'],
                    'validation_rules': template['validation_rules'],
                    'is_default': template['is_default']
                }
            )
            if created:
                self.stdout.write(f'创建模板: {template["name"]}')
            else:
                self.stdout.write(f'模板已存在: {template["name"]}')

    def _create_default_user(self):
        """创建默认用户"""
        self.stdout.write('检查默认用户...')
        
        try:
            # 创建超级用户（如果不存在）
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123'
                )
                self.stdout.write('创建默认管理员用户: admin/admin123')
            else:
                self.stdout.write('默认管理员用户已存在')
                
            # 创建普通用户（如果不存在）
            if not User.objects.filter(username='user').exists():
                User.objects.create_user(
                    username='user',
                    email='user@example.com',
                    password='user123'
                )
                self.stdout.write('创建默认普通用户: user/user123')
            else:
                self.stdout.write('默认普通用户已存在')
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'创建用户时出错: {str(e)}')
            )
