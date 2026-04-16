"""
任务恢复服务
实现系统启动时和手动触发的中断任务恢复功能
"""
import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction

from meteorite_search.models import DataExtractionTask
from .task_checkpoint_manager import checkpoint_manager
from .batch_extraction_service import BatchExtractionService

logger = logging.getLogger(__name__)


class TaskRecoveryService:
	"""任务恢复服务 - 支持系统启动恢复和手动恢复"""
	
	def __init__(self) -> None:
		self._last_status: Dict[str, Any] = {
			"status": "idle",
			"recovered_count": 0,
			"errors": [],
			"last_run_time": None
		}
	
	def check_and_recover_interrupted_tasks(
		self,
		max_tasks: int = 10,
		force_recovery: bool = False
	) -> List[Dict[str, Any]]:
		"""
		扫描并尝试恢复被中断的任务
		
		Args:
			max_tasks: 最大恢复任务数量
			force_recovery: 是否强制恢复（忽略某些检查条件）
		
		Returns:
			恢复结果列表
		"""
		logger.info("TaskRecoveryService: Starting check_and_recover_interrupted_tasks")
		
		try:
			# 查找可恢复的任务
			recoverable_tasks = self._find_recoverable_tasks(max_tasks)
			
			if not recoverable_tasks:
				logger.info("No recoverable tasks found")
				self._last_status = {
					"status": "completed",
					"recovered_count": 0,
					"errors": [],
					"last_run_time": timezone.now().isoformat()
				}
				return []
			
			logger.info(f"Found {len(recoverable_tasks)} recoverable tasks")
			
			# 尝试恢复每个任务
			recovery_results = []
			errors = []
			
			for task in recoverable_tasks:
				try:
					result = self._attempt_recovery(task, force_recovery)
					recovery_results.append(result)
					
					if result['success']:
						logger.info(f"Successfully recovered task {task.task_id}")
					else:
						logger.warning(f"Failed to recover task {task.task_id}: {result.get('error', 'Unknown error')}")
						errors.append(f"Task {task.task_id}: {result.get('error', 'Unknown error')}")
						
				except Exception as e:
					error_msg = f"Error recovering task {task.task_id}: {str(e)}"
					logger.error(error_msg, exc_info=True)
					errors.append(error_msg)
					recovery_results.append({
						'task_id': task.task_id,
						'success': False,
						'error': str(e)
					})
			
			# 更新状态
			recovered_count = sum(1 for r in recovery_results if r.get('success', False))
			self._last_status = {
				"status": "completed",
				"recovered_count": recovered_count,
				"errors": errors,
				"last_run_time": timezone.now().isoformat(),
				"total_checked": len(recoverable_tasks)
			}
			
			logger.info(f"Recovery completed: {recovered_count}/{len(recoverable_tasks)} tasks recovered")
			
			return recovery_results
			
		except Exception as e:
			logger.error(f"check_and_recover_interrupted_tasks failed: {str(e)}", exc_info=True)
			self._last_status = {
				"status": "error",
				"recovered_count": 0,
				"errors": [str(e)],
				"last_run_time": timezone.now().isoformat()
			}
			return []
	
	def manual_recover_task(self, task_id: str) -> Dict[str, Any]:
		"""
		手动恢复指定任务
		
		Args:
			task_id: 任务ID
		
		Returns:
			恢复结果
		"""
		logger.info(f"TaskRecoveryService: manual_recover_task {task_id}")
		
		try:
			# 查找任务
			try:
				task = DataExtractionTask.objects.get(task_id=task_id)
			except DataExtractionTask.DoesNotExist:
				return {
					"task_id": task_id,
					"success": False,
					"error": "Task not found"
				}
			
			# 检查任务是否可恢复
			if task.status not in ['paused', 'failed', 'running']:
				return {
					"task_id": task_id,
					"success": False,
					"error": f"Cannot recover task with status: {task.status}"
				}
			
			# 尝试恢复
			result = self._attempt_recovery(task, force_recovery=True)
			
			if result['success']:
				logger.info(f"Manually recovered task {task_id}")
			else:
				logger.warning(f"Manual recovery failed for task {task_id}: {result.get('error')}")
			
			return result
			
		except Exception as e:
			logger.error(f"manual_recover_task failed for {task_id}: {str(e)}", exc_info=True)
			return {
				"task_id": task_id,
				"success": False,
				"error": str(e)
			}
	
	def get_recovery_status(self) -> Dict[str, Any]:
		"""
		获取恢复服务状态
		
		Returns:
			状态字典
		"""
		return dict(self._last_status)
	
	def _find_recoverable_tasks(self, max_tasks: int) -> List[DataExtractionTask]:
		"""
		查找可恢复的任务
		
		Args:
			max_tasks: 最大返回任务数
		
		Returns:
			可恢复的任务列表
		"""
		try:
			# 查找状态为paused、failed或running的任务
			recoverable_tasks = DataExtractionTask.objects.filter(
				status__in=['paused', 'failed', 'running']
			).order_by('-created_at')[:max_tasks]
			
			return list(recoverable_tasks)
			
		except Exception as e:
			logger.error(f"Failed to find recoverable tasks: {str(e)}", exc_info=True)
			return []
	
	def _attempt_recovery(
		self,
		task: DataExtractionTask,
		force_recovery: bool = False
	) -> Dict[str, Any]:
		"""
		尝试恢复单个任务
		
		Args:
			task: 任务对象
			force_recovery: 是否强制恢复
		
		Returns:
			恢复结果
		"""
		try:
			# 检查是否有检查点
			checkpoint_stats = checkpoint_manager.get_checkpoint_stats(task.task_id)
			has_checkpoints = checkpoint_stats.get('has_checkpoints', False)
			
			if not has_checkpoints and not force_recovery:
				return {
					"task_id": task.task_id,
					"success": False,
					"error": "No checkpoints available",
					"recovery_method": "none"
				}
			
			# 根据任务类型选择恢复方法
			if task.task_type in ['batch_documents', 'batch_by_docs']:
				return self._recover_batch_extraction_task(task)
			else:
				return {
					"task_id": task.task_id,
					"success": False,
					"error": f"Unsupported task type: {task.task_type}",
					"recovery_method": "none"
				}
			
		except Exception as e:
			logger.error(f"Failed to attempt recovery for task {task.task_id}: {str(e)}", exc_info=True)
			return {
				"task_id": task.task_id,
				"success": False,
				"error": str(e),
				"recovery_method": "none"
			}
	
	def _recover_batch_extraction_task(self, task: DataExtractionTask) -> Dict[str, Any]:
		"""
		恢复批量提取任务
		
		Args:
			task: 任务对象
		
		Returns:
			恢复结果
		"""
		try:
			logger.info(f"Attempting to recover batch extraction task {task.task_id}")
			
			# 更新任务状态为恢复中
			with transaction.atomic():
				task.status = 'pending'
				task.save(update_fields=['status'])
			
			# 使用BatchExtractionService恢复任务
			batch_service = BatchExtractionService()
			recovery_success = batch_service.resume_batch_extraction(task.task_id)
			
			if recovery_success:
				return {
					"task_id": task.task_id,
					"success": True,
					"message": "Task recovery initiated successfully",
					"recovery_method": "batch_extraction_service",
					"recovered_at": timezone.now().isoformat()
				}
			else:
				return {
					"task_id": task.task_id,
					"success": False,
					"error": "Failed to initiate task recovery",
					"recovery_method": "batch_extraction_service"
				}
			
		except Exception as e:
			logger.error(f"Failed to recover batch extraction task {task.task_id}: {str(e)}", exc_info=True)
			
			# 更新任务状态为失败
			try:
				with transaction.atomic():
					task.status = 'failed'
					task.save(update_fields=['status'])
			except Exception as save_error:
				logger.error(f"Failed to update task status: {str(save_error)}")
			
			return {
				"task_id": task.task_id,
				"success": False,
				"error": str(e),
				"recovery_method": "batch_extraction_service"
			}


# 创建全局恢复服务实例
task_recovery_service = TaskRecoveryService()
