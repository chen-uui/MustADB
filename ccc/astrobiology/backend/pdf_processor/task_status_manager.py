"""Simple in-memory task status manager used by async extractors."""

import logging
from threading import Lock
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TaskStatusManager:
    def __init__(self) -> None:
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def update_task_status(self, task_id: str, status: str, progress_data: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            entry = self._statuses.setdefault(task_id, {})
            entry['status'] = status

            if progress_data:
                progress_entry = entry.setdefault('progress', {})
                # 合并新的进度信息，保留之前的关键字段，避免在不同阶段被覆盖为0
                progress_entry.update(progress_data)
            elif 'progress' not in entry:
                entry['progress'] = {}
        logger.debug("TaskStatus: %s -> %s (progress keys=%s)", task_id, status, list((progress_data or {}).keys()))

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._statuses.get(task_id)

    def clear_task(self, task_id: str) -> None:
        with self._lock:
            self._statuses.pop(task_id, None)

    def clear_cache(self, task_id: Optional[str] = None) -> None:
        with self._lock:
            if task_id:
                self._statuses.pop(task_id, None)
            else:
                self._statuses.clear()


task_status_manager = TaskStatusManager()
