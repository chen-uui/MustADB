"""
系统启动时自动恢复中断任务的Django管理命令
"""

import logging
from django.core.management.base import BaseCommand
from pdf_processor.task_recovery_service import task_recovery_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '系统启动时自动恢复中断的任务'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只检查可恢复的任务，不实际执行恢复'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制恢复所有符合条件的任务'
        )
        parser.add_argument(
            '--max-tasks',
            type=int,
            default=10,
            help='最大恢复任务数量（默认10）'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        max_tasks = options.get('max_tasks', 10)

        self.stdout.write(self.style.SUCCESS('开始系统启动恢复检查...'))

        if dry_run:
            self.stdout.write('运行模式: 仅检查 (不执行恢复)')
        else:
            self.stdout.write('运行模式: 执行恢复')

        try:
            # 执行恢复检查
            if dry_run:
                # 仅检查模式
                recovery_results = self._check_recoverable_tasks(max_tasks)
            else:
                # 实际恢复模式
                recovery_results = task_recovery_service.check_and_recover_interrupted_tasks(
                    max_tasks=max_tasks,
                    force_recovery=force
                )

            # 输出结果
            self._display_recovery_results(recovery_results, dry_run)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'系统启动恢复失败: {str(e)}'))
            logger.error(f"系统启动恢复失败: {str(e)}")
            raise

    def _check_recoverable_tasks(self, max_tasks):
        """检查可恢复的任务（仅检查模式）"""
        from meteorite_search.models import DataExtractionTask
        from pdf_processor.task_checkpoint_manager import checkpoint_manager
        
        # 查找可恢复的任务
        recoverable_tasks = DataExtractionTask.objects.filter(
            status__in=['paused', 'failed']
        ).order_by('-created_at')[:max_tasks]
        
        results = {
            'total_checked': recoverable_tasks.count(),
            'recoverable_tasks': [],
            'tasks_with_checkpoints': 0,
            'tasks_without_checkpoints': 0
        }
        
        for task in recoverable_tasks:
            # 检查是否有检查点
            checkpoint_stats = checkpoint_manager.get_checkpoint_stats(task.task_id)
            has_checkpoints = checkpoint_stats.get('has_checkpoints', False)
            
            if has_checkpoints:
                results['tasks_with_checkpoints'] += 1
            else:
                results['tasks_without_checkpoints'] += 1
            
            task_info = {
                'task_id': task.task_id,
                'task_type': task.task_type,
                'status': task.status,
                'created_at': task.created_at.isoformat(),
                'progress_percentage': task.get_progress_percentage(),
                'has_checkpoints': has_checkpoints,
                'checkpoint_count': checkpoint_stats.get('checkpoint_count', 0),
                'can_recover': has_checkpoints or task.status == 'paused'
            }
            
            results['recoverable_tasks'].append(task_info)
        
        return results

    def _display_recovery_results(self, results, dry_run=False):
        """显示恢复结果"""
        if dry_run:
            self.stdout.write('\n=== 可恢复任务检查结果 ===')
            self.stdout.write(f'总检查任务数: {results["total_checked"]}')
            self.stdout.write(f'有检查点的任务: {results["tasks_with_checkpoints"]}')
            self.stdout.write(f'无检查点的任务: {results["tasks_without_checkpoints"]}')
            
            if results['recoverable_tasks']:
                self.stdout.write('\n可恢复的任务列表:')
                for task in results['recoverable_tasks']:
                    status_icon = '✓' if task['can_recover'] else '✗'
                    checkpoint_info = f"({task['checkpoint_count']} 个检查点)" if task['has_checkpoints'] else "(无检查点)"
                    
                    self.stdout.write(
                        f'  {status_icon} {task["task_id"]} - {task["status"]} - '
                        f'{task["progress_percentage"]:.1f}% {checkpoint_info}'
                    )
            else:
                self.stdout.write('没有找到可恢复的任务')
                
        else:
            self.stdout.write('\n=== 系统启动恢复结果 ===')
            
            if 'recovered_tasks' in results:
                recovered_count = len(results['recovered_tasks'])
                self.stdout.write(f'成功恢复任务数: {recovered_count}')
                
                if recovered_count > 0:
                    self.stdout.write('\n恢复的任务:')
                    for task_result in results['recovered_tasks']:
                        if task_result['success']:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  ✓ {task_result["task_id"]} - 恢复成功'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  ✗ {task_result["task_id"]} - 恢复失败: {task_result.get("error", "未知错误")}'
                                )
                            )
            
            if 'skipped_tasks' in results:
                skipped_count = len(results['skipped_tasks'])
                if skipped_count > 0:
                    self.stdout.write(f'\n跳过的任务数: {skipped_count}')
                    for task_id in results['skipped_tasks']:
                        self.stdout.write(f'  - {task_id}')
            
            if 'errors' in results and results['errors']:
                self.stdout.write(self.style.ERROR('\n恢复过程中的错误:'))
                for error in results['errors']:
                    self.stdout.write(self.style.ERROR(f'  • {error}'))
        
        self.stdout.write(self.style.SUCCESS('\n系统启动恢复检查完成'))