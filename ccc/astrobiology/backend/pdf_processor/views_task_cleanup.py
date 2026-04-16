"""Task cleanup views for extraction task recovery and cancellation."""

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from meteorite_search.models import DataExtractionTask

from .task_status_manager import task_status_manager
from .thread_manager import thread_manager

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([AllowAny])
def cleanup_stale_tasks(request):
    """Mark DB tasks as cancelled when no in-memory worker is still alive."""
    try:
        with transaction.atomic():
            running_tasks = DataExtractionTask.objects.filter(status="running")

            cleaned_count = 0
            for task in running_tasks:
                if not thread_manager.is_running(task.task_id):
                    task.status = "cancelled"
                    task.completed_at = timezone.now()
                    task.save(update_fields=["status", "completed_at"])
                    cleaned_count += 1
                    logger.info("cleanup_stale_tasks cancelled task %s", task.task_id)
                    task_status_manager.clear_cache(task.task_id)

            return Response(
                {
                    "success": True,
                    "message": f"cleaned {cleaned_count} stale tasks",
                    "cleaned_count": cleaned_count,
                }
            )

    except Exception as exc:
        logger.error("cleanup_stale_tasks failed: %s", exc)
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([AllowAny])
def force_cleanup_all_running_tasks(request):
    """Cancel running DB tasks and explicitly signal any live worker threads."""
    try:
        with transaction.atomic():
            running_tasks = list(DataExtractionTask.objects.filter(status="running"))

            stopped_count = 0
            missing_thread_count = 0
            cleanup_results = []

            for task in running_tasks:
                thread_stop_signaled = thread_manager.stop_thread(task.task_id, save_progress=True)
                if thread_stop_signaled:
                    stopped_count += 1
                    logger.info("force_cleanup_all_running_tasks stop signaled for %s", task.task_id)
                else:
                    missing_thread_count += 1
                    logger.warning("force_cleanup_all_running_tasks no live thread for %s", task.task_id)

                task.status = "cancelled"
                task.completed_at = timezone.now()
                task.save(update_fields=["status", "completed_at"])
                task_status_manager.clear_cache(task.task_id)
                cleanup_results.append(
                    {
                        "task_id": task.task_id,
                        "thread_stop_signaled": thread_stop_signaled,
                        "db_status_updated": True,
                    }
                )

            return Response(
                {
                    "success": True,
                    "message": f"cleaned {len(running_tasks)} running tasks",
                    "cleaned_count": len(running_tasks),
                    "stopped_count": stopped_count,
                    "missing_thread_count": missing_thread_count,
                    "results": cleanup_results,
                }
            )

    except Exception as exc:
        logger.error("force_cleanup_all_running_tasks failed: %s", exc)
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([AllowAny])
def get_running_tasks_status(request):
    """Return the running task list for operational inspection."""
    try:
        running_tasks = DataExtractionTask.objects.filter(status="running")

        tasks_info = []
        for task in running_tasks:
            updated_at = getattr(task, "updated_at", None)
            time_since_update = None
            if updated_at:
                time_since_update = (timezone.now() - updated_at).total_seconds()
            tasks_info.append(
                {
                    "task_id": task.task_id,
                    "task_type": task.task_type,
                    "created_at": task.created_at,
                    "updated_at": updated_at,
                    "time_since_update_seconds": time_since_update,
                    "is_stale": bool(time_since_update and time_since_update > 300),
                }
            )

        return Response(
            {
                "success": True,
                "running_tasks_count": len(tasks_info),
                "tasks": tasks_info,
            }
        )

    except Exception as exc:
        logger.error("get_running_tasks_status failed: %s", exc)
        return Response({"success": False, "error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
