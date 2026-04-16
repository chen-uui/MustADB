"""Lightweight thread manager with pause/resume/stop support."""

import logging
import threading
from typing import Callable, Dict, Any

logger = logging.getLogger(__name__)


class ThreadManager:
    def __init__(self) -> None:
        self._threads: Dict[str, threading.Thread] = {}
        self._stops: Dict[str, threading.Event] = {}
        self._pauses: Dict[str, threading.Event] = {}
        self._locks: Dict[str, threading.Lock] = {}

    def start_thread(self, task_id: str, target_func: Callable, **kwargs: Any) -> bool:
        if task_id in self._threads and self._threads[task_id].is_alive():
            logger.info("ThreadManager: task %s already running", task_id)
            return True

        stop_event = threading.Event()
        pause_event = threading.Event()

        self._stops[task_id] = stop_event
        self._pauses[task_id] = pause_event
        self._locks[task_id] = threading.Lock()

        def runner() -> None:
            try:
                code_vars = target_func.__code__.co_varnames
                if 'stop_event' in code_vars:
                    kwargs['stop_event'] = stop_event
                if 'pause_event' in code_vars:
                    kwargs['pause_event'] = pause_event
                target_func(**kwargs)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("ThreadManager: task %s crashed: %s", task_id, exc, exc_info=True)
            finally:
                self._stops.pop(task_id, None)
                self._pauses.pop(task_id, None)
                self._locks.pop(task_id, None)
                self._threads.pop(task_id, None)

        thread = threading.Thread(target=runner, daemon=True)
        self._threads[task_id] = thread
        thread.start()
        logger.info("ThreadManager: started task %s", task_id)
        return True

    def stop_thread(self, task_id: str, save_progress: bool = True) -> bool:
        stop = self._stops.get(task_id)
        if not stop:
            logger.warning("ThreadManager: stop requested for unknown task %s", task_id)
            return False
        stop.set()
        logger.info("ThreadManager: stop signaled for %s", task_id)
        return True

    def pause_thread(self, task_id: str) -> bool:
        pause = self._pauses.get(task_id)
        if not pause:
            logger.warning("ThreadManager: pause requested for unknown task %s", task_id)
            return False
        pause.set()
        logger.info("ThreadManager: pause signaled for %s", task_id)
        return True

    def resume_thread(self, task_id: str) -> bool:
        pause = self._pauses.get(task_id)
        if not pause:
            logger.warning("ThreadManager: resume requested for unknown task %s", task_id)
            return False
        pause.clear()
        logger.info("ThreadManager: resume signaled for %s", task_id)
        return True

    def is_running(self, task_id: str) -> bool:
        thread = self._threads.get(task_id)
        return bool(thread and thread.is_alive())


thread_manager = ThreadManager()
