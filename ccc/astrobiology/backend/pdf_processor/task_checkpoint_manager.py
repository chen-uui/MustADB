"""
任务检查点管理器
实现数据提取任务的持久化检查点功能，支持断点续传
"""

import json
import os
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


class TaskCheckpointManager:
    """任务检查点管理器 - 支持文件系统持久化"""
    
    def __init__(self, checkpoint_dir: Optional[str] = None):
        """
        初始化检查点管理器
        
        Args:
            checkpoint_dir: 检查点存储目录，默认使用项目下的checkpoints目录
        """
        # 确定检查点目录
        if checkpoint_dir:
            self.checkpoint_dir = Path(checkpoint_dir)
        else:
            # 默认目录：项目根目录下的 checkpoints 文件夹
            current_dir = Path(__file__).parent.parent.parent
            self.checkpoint_dir = current_dir / 'checkpoints' / 'extraction_tasks'
        
        # 确保目录存在
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置参数
        self._checkpoint_interval = 5  # 每5个批次保存一次检查点
        self._max_checkpoints = 20  # 每个任务最多保留20个检查点
        self._lock = Lock()  # 线程安全锁
        
        logger.info(f"TaskCheckpointManager initialized with directory: {self.checkpoint_dir}")
    
    def set_checkpoint_interval(self, interval: int) -> None:
        """设置检查点保存间隔"""
        self._checkpoint_interval = interval
        logger.info(f"Checkpoint interval set to {interval}")
    
    def set_max_checkpoints(self, max_count: int) -> None:
        """设置每个任务的最大检查点数量"""
        self._max_checkpoints = max_count
        logger.info(f"Max checkpoints per task set to {max_count}")
    
    def should_save_checkpoint(self, batch_number: int) -> bool:
        """判断是否应该保存检查点"""
        if batch_number == 0:
            return False
        return batch_number % self._checkpoint_interval == 0
    
    def create_checkpoint_data(self, **kwargs) -> Dict[str, Any]:
        """
        创建检查点数据
        
        Args:
            **kwargs: 检查点数据字段
            
        Returns:
            格式化的检查点数据字典
        """
        checkpoint_data = {
            'created_at': datetime.now().isoformat(),
            'version': '1.0',  # 检查点版本
            **kwargs
        }
        return checkpoint_data
    
    def _get_task_checkpoint_dir(self, task_id: str) -> Path:
        """获取任务专属的检查点目录"""
        return self.checkpoint_dir / task_id
    
    def save_checkpoint(self, task_id: str, checkpoint_data: Dict[str, Any]) -> bool:
        """
        保存检查点到文件系统
        
        Args:
            task_id: 任务ID
            checkpoint_data: 检查点数据
            
        Returns:
            是否保存成功
        """
        with self._lock:
            try:
                # 确保任务目录存在
                task_dir = self._get_task_checkpoint_dir(task_id)
                task_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成检查点文件名（使用时间戳）
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                checkpoint_filename = f"checkpoint_{timestamp}.json"
                checkpoint_path = task_dir / checkpoint_filename
                
                # 保存检查点文件
                with open(checkpoint_path, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Checkpoint saved: {checkpoint_path}")
                
                # 清理旧检查点
                self._cleanup_old_checkpoints(task_id)
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to save checkpoint for task {task_id}: {str(e)}", exc_info=True)
                return False
    
    def load_latest_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        加载最新的检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            检查点数据，如果不存在则返回None
        """
        with self._lock:
            try:
                task_dir = self._get_task_checkpoint_dir(task_id)
                
                if not task_dir.exists():
                    logger.debug(f"No checkpoint directory for task {task_id}")
                    return None
                
                # 查找所有检查点文件
                checkpoint_files = sorted(task_dir.glob('checkpoint_*.json'), reverse=True)
                
                if not checkpoint_files:
                    logger.debug(f"No checkpoints found for task {task_id}")
                    return None
                
                # 加载最新的检查点
                latest_checkpoint = checkpoint_files[0]
                with open(latest_checkpoint, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                logger.info(f"Loaded latest checkpoint: {latest_checkpoint}")
                return checkpoint_data
                
            except Exception as e:
                logger.error(f"Failed to load checkpoint for task {task_id}: {str(e)}", exc_info=True)
                return None
    
    def load_checkpoint_by_id(self, task_id: str, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        根据检查点ID加载检查点
        
        Args:
            task_id: 任务ID
            checkpoint_id: 检查点ID（文件名的一部分）
            
        Returns:
            检查点数据，如果不存在则返回None
        """
        with self._lock:
            try:
                task_dir = self._get_task_checkpoint_dir(task_id)
                checkpoint_file = task_dir / f"checkpoint_{checkpoint_id}.json"
                
                if not checkpoint_file.exists():
                    logger.debug(f"Checkpoint {checkpoint_id} not found for task {task_id}")
                    return None
                
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                return checkpoint_data
                
            except Exception as e:
                logger.error(f"Failed to load checkpoint {checkpoint_id}: {str(e)}", exc_info=True)
                return None
    
    def list_checkpoints(self, task_id: str) -> List[Dict[str, Any]]:
        """
        列出任务的所有检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            检查点列表
        """
        with self._lock:
            try:
                task_dir = self._get_task_checkpoint_dir(task_id)
                
                if not task_dir.exists():
                    return []
                
                # 查找所有检查点文件
                checkpoint_files = sorted(task_dir.glob('checkpoint_*.json'), reverse=True)
                
                checkpoints = []
                for checkpoint_file in checkpoint_files:
                    try:
                        with open(checkpoint_file, 'r', encoding='utf-8') as f:
                            checkpoint_data = json.load(f)
                        
                        # 提取检查点ID（从文件名中）
                        checkpoint_id = checkpoint_file.stem.replace('checkpoint_', '')
                        
                        checkpoints.append({
                            'id': checkpoint_id,
                            'created_at': checkpoint_data.get('created_at'),
                            'file_path': str(checkpoint_file),
                            'summary': self._create_checkpoint_summary(checkpoint_data)
                        })
                        
                    except Exception as e:
                        logger.warning(f"Failed to read checkpoint file {checkpoint_file}: {str(e)}")
                        continue
                
                return checkpoints
                
            except Exception as e:
                logger.error(f"Failed to list checkpoints for task {task_id}: {str(e)}", exc_info=True)
                return []
    
    def get_checkpoint_stats(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务的检查点统计信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            统计信息字典
        """
        with self._lock:
            try:
                task_dir = self._get_task_checkpoint_dir(task_id)
                
                if not task_dir.exists():
                    return {
                        'has_checkpoints': False,
                        'checkpoint_count': 0,
                        'latest_checkpoint_time': None,
                        'total_size': 0
                    }
                
                # 查找所有检查点文件
                checkpoint_files = sorted(task_dir.glob('checkpoint_*.json'), reverse=True)
                
                if not checkpoint_files:
                    return {
                        'has_checkpoints': False,
                        'checkpoint_count': 0,
                        'latest_checkpoint_time': None,
                        'total_size': 0
                    }
                
                # 计算总大小
                total_size = sum(f.stat().st_size for f in checkpoint_files)
                
                # 获取最新检查点的时间
                latest_checkpoint_time = None
                if checkpoint_files:
                    try:
                        with open(checkpoint_files[0], 'r', encoding='utf-8') as f:
                            latest_data = json.load(f)
                            latest_checkpoint_time = latest_data.get('created_at')
                    except Exception as e:
                        logger.warning(f"Failed to read latest checkpoint: {str(e)}")
                
                return {
                    'has_checkpoints': True,
                    'checkpoint_count': len(checkpoint_files),
                    'latest_checkpoint_time': latest_checkpoint_time,
                    'total_size': total_size,
                    'total_size_mb': round(total_size / (1024 * 1024), 2)
                }
                
            except Exception as e:
                logger.error(f"Failed to get checkpoint stats for task {task_id}: {str(e)}", exc_info=True)
                return {
                    'has_checkpoints': False,
                    'checkpoint_count': 0,
                    'latest_checkpoint_time': None,
                    'total_size': 0,
                    'error': str(e)
                }
    
    def clear_checkpoints(self, task_id: str) -> bool:
        """
        清除任务的所有检查点
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否清除成功
        """
        with self._lock:
            try:
                task_dir = self._get_task_checkpoint_dir(task_id)
                
                if not task_dir.exists():
                    logger.debug(f"No checkpoint directory for task {task_id}")
                    return True
                
                # 删除整个任务目录
                shutil.rmtree(task_dir)
                
                logger.info(f"Cleared all checkpoints for task {task_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to clear checkpoints for task {task_id}: {str(e)}", exc_info=True)
                return False
    
    def _cleanup_old_checkpoints(self, task_id: str) -> None:
        """
        清理旧的检查点（保留最新的N个）
        
        Args:
            task_id: 任务ID
        """
        try:
            task_dir = self._get_task_checkpoint_dir(task_id)
            
            if not task_dir.exists():
                return
            
            # 查找所有检查点文件并按时间排序
            checkpoint_files = sorted(task_dir.glob('checkpoint_*.json'))
            
            # 如果检查点数量超过限制，删除最旧的
            if len(checkpoint_files) > self._max_checkpoints:
                files_to_delete = checkpoint_files[:-self._max_checkpoints]
                for file_to_delete in files_to_delete:
                    try:
                        file_to_delete.unlink()
                        logger.debug(f"Deleted old checkpoint: {file_to_delete}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old checkpoint {file_to_delete}: {str(e)}")
                
                logger.info(f"Cleaned up {len(files_to_delete)} old checkpoints for task {task_id}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints: {str(e)}", exc_info=True)
    
    def _create_checkpoint_summary(self, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建检查点摘要信息
        
        Args:
            checkpoint_data: 检查点数据
            
        Returns:
            摘要信息字典
        """
        summary = {
            'created_at': checkpoint_data.get('created_at'),
            'version': checkpoint_data.get('version', '1.0')
        }
        
        # 提取关键信息
        if 'current_batch' in checkpoint_data:
            summary['current_batch'] = checkpoint_data['current_batch'].get('batch_num', 0)
        
        if 'progress' in checkpoint_data:
            summary['progress_percentage'] = checkpoint_data['progress'].get('progress_percentage', 0)
            summary['processed_documents'] = checkpoint_data['progress'].get('processed_documents', 0)
        
        return summary
    
    def backup_checkpoint(self, task_id: str, checkpoint_id: str, backup_dir: str) -> bool:
        """
        备份检查点到指定目录
        
        Args:
            task_id: 任务ID
            checkpoint_id: 检查点ID
            backup_dir: 备份目录
            
        Returns:
            是否备份成功
        """
        try:
            task_dir = self._get_task_checkpoint_dir(task_id)
            checkpoint_file = task_dir / f"checkpoint_{checkpoint_id}.json"
            
            if not checkpoint_file.exists():
                logger.error(f"Checkpoint {checkpoint_id} not found for task {task_id}")
                return False
            
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 复制检查点文件到备份目录
            shutil.copy2(checkpoint_file, backup_path / checkpoint_file.name)
            
            logger.info(f"Checkpoint backed up to {backup_path / checkpoint_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup checkpoint: {str(e)}", exc_info=True)
            return False


# 创建全局检查点管理器实例
checkpoint_manager = TaskCheckpointManager()

