"""
测试断点续传功能的Django管理命令
"""

import time
import json
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from meteorite_search.models import DataExtractionTask
from pdf_processor.task_checkpoint_manager import checkpoint_manager
from pdf_processor.task_recovery_service import task_recovery_service
from pdf_processor.batch_extraction_service import BatchExtractionService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '测试断点续传功能'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            choices=['checkpoint', 'recovery', 'full'],
            default='full',
            help='测试类型: checkpoint(检查点), recovery(恢复), full(完整测试)'
        )
        parser.add_argument(
            '--task-id',
            type=str,
            help='指定要测试的任务ID'
        )
        parser.add_argument(
            '--simulate-crash',
            action='store_true',
            help='模拟系统崩溃'
        )

    def handle(self, *args, **options):
        test_type = options['test_type']
        task_id = options.get('task_id')
        simulate_crash = options.get('simulate_crash', False)

        self.stdout.write(self.style.SUCCESS(f'开始测试断点续传功能 - 测试类型: {test_type}'))

        if test_type == 'checkpoint':
            self.test_checkpoint_functionality()
        elif test_type == 'recovery':
            self.test_recovery_functionality(task_id)
        elif test_type == 'full':
            self.test_full_checkpoint_recovery(simulate_crash)

    def test_checkpoint_functionality(self):
        """测试检查点功能"""
        self.stdout.write('测试检查点功能...')
        
        # 创建测试任务
        task = DataExtractionTask.objects.create(
            task_id=f'test_checkpoint_{int(time.time())}',
            task_type='batch_extraction',
            status='running',
            parameters={'test': True, 'batch_size': 10},
            total_documents=100,
            processed_documents=0
        )
        
        try:
            # 模拟批次处理并保存检查点
            for batch_num in range(1, 6):  # 5个批次
                # 模拟处理进度
                processed = batch_num * 20
                task.processed_documents = processed
                task.save()
                
                # 创建检查点数据
                checkpoint_data = {
                    'batch_number': batch_num,
                    'processed_documents': processed,
                    'processed_doc_ids': [f'doc_{i}' for i in range(1, processed + 1)],
                    'extraction_log': [f'批次 {batch_num} 处理完成'],
                    'current_batch_size': 20,
                    'timestamp': timezone.now().isoformat()
                }
                
                # 保存检查点
                success = checkpoint_manager.save_checkpoint(task.task_id, checkpoint_data)
                
                if success:
                    self.stdout.write(f'✓ 批次 {batch_num} 检查点保存成功')
                else:
                    self.stdout.write(self.style.ERROR(f'✗ 批次 {batch_num} 检查点保存失败'))
                
                time.sleep(0.5)  # 模拟处理时间
            
            # 测试检查点列表
            checkpoints = checkpoint_manager.list_checkpoints(task.task_id)
            self.stdout.write(f'检查点列表: {len(checkpoints)} 个检查点')
            
            # 测试加载最新检查点
            latest_checkpoint = checkpoint_manager.load_latest_checkpoint(task.task_id)
            if latest_checkpoint:
                self.stdout.write(f'✓ 最新检查点加载成功: 批次 {latest_checkpoint["batch_number"]}')
            else:
                self.stdout.write(self.style.ERROR('✗ 最新检查点加载失败'))
            
            # 测试检查点统计
            stats = checkpoint_manager.get_checkpoint_stats(task.task_id)
            self.stdout.write(f'检查点统计: {json.dumps(stats, indent=2, ensure_ascii=False)}')
            
            # 清理测试数据
            checkpoint_manager.clear_checkpoints(task.task_id)
            task.delete()
            
            self.stdout.write(self.style.SUCCESS('✓ 检查点功能测试完成'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 检查点功能测试失败: {str(e)}'))
            # 清理
            checkpoint_manager.clear_checkpoints(task.task_id)
            task.delete()

    def test_recovery_functionality(self, task_id=None):
        """测试恢复功能"""
        self.stdout.write('测试恢复功能...')
        
        if task_id:
            # 测试指定任务的恢复
            try:
                result = task_recovery_service.manual_recover_task(task_id)
                if result['success']:
                    self.stdout.write(self.style.SUCCESS(f'✓ 任务 {task_id} 恢复成功'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ 任务 {task_id} 恢复失败: {result.get("error")}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ 任务恢复测试失败: {str(e)}'))
        else:
            # 测试系统启动恢复
            try:
                results = task_recovery_service.check_and_recover_interrupted_tasks()
                self.stdout.write(f'系统启动恢复结果: {json.dumps(results, indent=2, ensure_ascii=False)}')
                self.stdout.write(self.style.SUCCESS('✓ 系统启动恢复测试完成'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ 系统启动恢复测试失败: {str(e)}'))

    def test_full_checkpoint_recovery(self, simulate_crash=False):
        """完整的断点续传测试"""
        self.stdout.write('开始完整的断点续传测试...')
        
        # 创建测试任务
        task = DataExtractionTask.objects.create(
            task_id=f'test_full_{int(time.time())}',
            task_type='batch_extraction',
            status='running',
            parameters={
                'test': True,
                'batch_size': 20,
                'search_queries': ['test meteorite']
            },
            total_documents=100,
            processed_documents=0
        )
        
        try:
            # 第一阶段：正常处理并保存检查点
            self.stdout.write('第一阶段：模拟正常处理...')
            
            for batch_num in range(1, 4):  # 处理3个批次
                processed = batch_num * 20
                task.processed_documents = processed
                task.save()
                
                checkpoint_data = {
                    'batch_number': batch_num,
                    'processed_documents': processed,
                    'processed_doc_ids': [f'doc_{i}' for i in range(1, processed + 1)],
                    'extraction_log': [f'批次 {batch_num} 处理完成'],
                    'current_batch_size': 20,
                    'search_queries': ['test meteorite'],
                    'timestamp': timezone.now().isoformat()
                }
                
                checkpoint_manager.save_checkpoint(task.task_id, checkpoint_data)
                self.stdout.write(f'  批次 {batch_num} 完成 (已处理 {processed}/100 文档)')
                time.sleep(0.3)
            
            # 第二阶段：模拟中断
            if simulate_crash:
                self.stdout.write('第二阶段：模拟系统崩溃...')
                task.status = 'paused'  # 模拟任务被中断
                task.save()
                
                # 模拟系统重启后的恢复
                self.stdout.write('第三阶段：模拟系统重启后恢复...')
                time.sleep(1)
                
                # 尝试恢复任务
                recovery_result = task_recovery_service.manual_recover_task(task.task_id)
                
                if recovery_result['success']:
                    self.stdout.write(self.style.SUCCESS('✓ 任务恢复成功'))
                    
                    # 验证恢复状态
                    task.refresh_from_db()
                    latest_checkpoint = checkpoint_manager.load_latest_checkpoint(task.task_id)
                    
                    if latest_checkpoint:
                        self.stdout.write(f'  恢复到批次: {latest_checkpoint["batch_number"]}')
                        self.stdout.write(f'  已处理文档: {latest_checkpoint["processed_documents"]}')
                        self.stdout.write(f'  处理的文档ID数量: {len(latest_checkpoint["processed_doc_ids"])}')
                    
                    # 继续处理剩余批次
                    self.stdout.write('继续处理剩余批次...')
                    start_batch = latest_checkpoint['batch_number'] + 1 if latest_checkpoint else 1
                    
                    for batch_num in range(start_batch, 6):  # 完成剩余批次
                        processed = batch_num * 20
                        task.processed_documents = processed
                        task.save()
                        
                        checkpoint_data = {
                            'batch_number': batch_num,
                            'processed_documents': processed,
                            'processed_doc_ids': [f'doc_{i}' for i in range(1, processed + 1)],
                            'extraction_log': [f'批次 {batch_num} 处理完成（恢复后）'],
                            'current_batch_size': 20,
                            'search_queries': ['test meteorite'],
                            'timestamp': timezone.now().isoformat()
                        }
                        
                        checkpoint_manager.save_checkpoint(task.task_id, checkpoint_data)
                        self.stdout.write(f'  批次 {batch_num} 完成 (已处理 {processed}/100 文档)')
                        time.sleep(0.3)
                    
                    # 标记任务完成
                    task.status = 'completed'
                    task.completed_at = timezone.now()
                    task.save()
                    
                    self.stdout.write(self.style.SUCCESS('✓ 任务完全恢复并完成'))
                    
                else:
                    self.stdout.write(self.style.ERROR(f'✗ 任务恢复失败: {recovery_result.get("error")}'))
            
            # 测试结果验证
            self.stdout.write('\n测试结果验证:')
            
            # 检查点统计
            stats = checkpoint_manager.get_checkpoint_stats(task.task_id)
            self.stdout.write(f'  检查点统计: {json.dumps(stats, indent=2, ensure_ascii=False)}')
            
            # 任务状态
            task.refresh_from_db()
            self.stdout.write(f'  最终任务状态: {task.status}')
            self.stdout.write(f'  处理文档数: {task.processed_documents}/{task.total_documents}')
            
            # 清理测试数据
            checkpoint_manager.clear_checkpoints(task.task_id)
            task.delete()
            
            self.stdout.write(self.style.SUCCESS('\n✓ 完整断点续传测试完成'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 完整测试失败: {str(e)}'))
            # 清理
            checkpoint_manager.clear_checkpoints(task.task_id)
            task.delete()
            raise

    def test_performance_impact(self):
        """测试检查点对性能的影响"""
        self.stdout.write('测试检查点性能影响...')
        
        # 测试不同检查点间隔的性能
        intervals = [1, 5, 10, 20]
        
        for interval in intervals:
            checkpoint_manager.set_checkpoint_interval(interval)
            
            start_time = time.time()
            
            # 模拟批次处理
            task_id = f'perf_test_{interval}_{int(time.time())}'
            
            for i in range(50):  # 50个批次
                if checkpoint_manager.should_save_checkpoint(i):
                    checkpoint_data = {
                        'batch_number': i,
                        'processed_documents': i * 10,
                        'timestamp': timezone.now().isoformat()
                    }
                    checkpoint_manager.save_checkpoint(task_id, checkpoint_data)
                
                time.sleep(0.01)  # 模拟处理时间
            
            end_time = time.time()
            duration = end_time - start_time
            
            # 统计检查点数量
            checkpoints = checkpoint_manager.list_checkpoints(task_id)
            
            self.stdout.write(f'  间隔 {interval}: 耗时 {duration:.2f}s, 检查点数量 {len(checkpoints)}')
            
            # 清理
            checkpoint_manager.clear_checkpoints(task_id)
        
        self.stdout.write(self.style.SUCCESS('✓ 性能测试完成'))