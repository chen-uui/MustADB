"""
Canonical PDF processor URL configuration.

`config.urls` includes `pdf_processor.urls`, which resolves to this package
entry. Keep the authoritative urlpatterns here so runtime behavior and static
reading stay aligned.
"""

from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from ..views_auth import (
    change_password,
    get_user_info,
    login,
    logout,
    register,
    update_profile,
)
from ..views_health import health_check, metrics, quick_health
from ..views_qa_extraction import PDFQAViewSet, ask_question_api, qa_demo
from ..views_task_cleanup import (
    cleanup_stale_tasks,
    force_cleanup_all_running_tasks,
    get_running_tasks_status,
)
from ..views_task_list import get_extraction_tasks
from ..views_unified_rag import (
    UnifiedExtractionView,
    UnifiedQuestionView,
    UnifiedSearchView,
    service_status,
)
from ..views_user_upload import user_upload_pdfs
from ..weaviate_views import WeaviatePDFViewSet


def _extraction_unavailable(request, *args, **kwargs):
    return JsonResponse(
        {"success": False, "error": "extraction endpoints temporarily unavailable"},
        status=503,
    )


try:
    from ..views_extraction import (
        confirm_and_save_extraction,
        extract_from_selected_segments,
        get_extraction_progress,
        get_task_status,
        pause_extraction_task,
        preview_search,
        reset_batch_extraction_state,
        resume_extraction_task,
        search_meteorite_segments,
        single_task_cancel,
        single_task_enqueue,
        single_task_search,
        single_task_segments,
        single_task_status,
        start_batch_extraction,
        start_extraction_from_db,
        stop_extraction_task,
    )
except Exception:
    preview_search = _extraction_unavailable
    reset_batch_extraction_state = _extraction_unavailable
    get_extraction_progress = _extraction_unavailable
    start_extraction_from_db = _extraction_unavailable
    start_batch_extraction = _extraction_unavailable
    confirm_and_save_extraction = _extraction_unavailable
    search_meteorite_segments = _extraction_unavailable
    extract_from_selected_segments = _extraction_unavailable
    pause_extraction_task = _extraction_unavailable
    resume_extraction_task = _extraction_unavailable
    stop_extraction_task = _extraction_unavailable
    get_task_status = _extraction_unavailable
    single_task_search = _extraction_unavailable
    single_task_enqueue = _extraction_unavailable
    single_task_status = _extraction_unavailable
    single_task_cancel = _extraction_unavailable
    single_task_segments = _extraction_unavailable


router = DefaultRouter()
router.register(r"documents", WeaviatePDFViewSet, basename="pdf-document")
router.register(r"weaviate-pdfs", WeaviatePDFViewSet, basename="weaviate-pdf")
router.register(r"qa", PDFQAViewSet, basename="pdf-qa")


urlpatterns = [
    path("documents/user-upload/", user_upload_pdfs, name="user_upload_pdfs"),
    path(
        "documents/process_pending/",
        WeaviatePDFViewSet.as_view({"post": "process_pending"}),
        name="process_pending",
    ),
    path(
        "documents/process-pending/",
        WeaviatePDFViewSet.as_view({"post": "process_pending"}),
        name="process_pending_legacy",
    ),
    path(
        "documents/process_stale/",
        WeaviatePDFViewSet.as_view({"post": "process_stale"}),
        name="process_stale",
    ),
    path(
        "documents/process-stale/",
        WeaviatePDFViewSet.as_view({"post": "process_stale"}),
        name="process_stale_legacy",
    ),
    path(
        "documents/processing-status/",
        WeaviatePDFViewSet.as_view({"get": "processing_status"}),
        name="processing_status_legacy",
    ),
    path(
        "documents/cancel-processing/",
        WeaviatePDFViewSet.as_view({"post": "cancel_processing"}),
        name="cancel_processing_legacy",
    ),
    path(
        "documents/reprocess-all/",
        WeaviatePDFViewSet.as_view({"post": "reprocess_all"}),
        name="reprocess_all_legacy",
    ),
    path(
        "documents/sync-files/",
        WeaviatePDFViewSet.as_view({"post": "sync_files"}),
        name="sync_files_legacy",
    ),
    path("", include(router.urls)),
    path("auth/login/", login, name="login"),
    path("auth/register/", register, name="register"),
    path("auth/logout/", logout, name="logout"),
    path("auth/user-info/", get_user_info, name="get_user_info"),
    path("auth/update-profile/", update_profile, name="update_profile"),
    path("auth/change-password/", change_password, name="change_password"),
    path("health/", health_check, name="health_check"),
    path("health/quick/", quick_health, name="quick_health"),
    path("health/metrics/", metrics, name="metrics"),
    path("qa/demo/", qa_demo, name="qa_demo"),
    path("qa/ask/", ask_question_api, name="ask_question_api"),
    path("extraction/preview/", preview_search, name="preview_search"),
    path("extraction/reset-state/", reset_batch_extraction_state, name="reset_batch_extraction_state"),
    path("extraction/progress/<str:task_id>/", get_extraction_progress, name="get_extraction_progress"),
    path("extraction/start-from-db/", start_extraction_from_db, name="start_extraction_from_db"),
    path("extraction/start-batch/", start_batch_extraction, name="start_batch_extraction"),
    path("extraction/confirm-save/", confirm_and_save_extraction, name="confirm_and_save_extraction"),
    path("extraction/search-segments/", search_meteorite_segments, name="search_meteorite_segments"),
    path("extraction/extract-selected/", extract_from_selected_segments, name="extract_from_selected_segments"),
    path("extraction/pause/<str:task_id>/", pause_extraction_task, name="pause_extraction_task_with_id"),
    path("extraction/resume/<str:task_id>/", resume_extraction_task, name="resume_extraction_task_with_id"),
    path("extraction/stop/<str:task_id>/", stop_extraction_task, name="stop_extraction_task_with_id"),
    path("extraction/status/<str:task_id>/", get_task_status, name="get_task_status_with_id"),
    path("extraction/pause/", pause_extraction_task, name="pause_extraction_task"),
    path("extraction/resume/", resume_extraction_task, name="resume_extraction_task"),
    path("extraction/stop/", stop_extraction_task, name="stop_extraction_task"),
    path("extraction/status/", get_task_status, name="get_task_status"),
    path("extraction/single/search/", single_task_search, name="single_task_search"),
    path("extraction/single/enqueue/", single_task_enqueue, name="single_task_enqueue"),
    path("extraction/single/status/", single_task_status, name="single_task_status"),
    path("extraction/single/cancel/", single_task_cancel, name="single_task_cancel"),
    path("extraction/single/segments/", single_task_segments, name="single_task_segments"),
    path("tasks/cleanup-stale/", cleanup_stale_tasks, name="cleanup_stale_tasks"),
    path("tasks/force-cleanup/", force_cleanup_all_running_tasks, name="force_cleanup_all_running_tasks"),
    path("tasks/running-status/", get_running_tasks_status, name="get_running_tasks_status"),
    path("tasks/list/", get_extraction_tasks, name="get_extraction_tasks"),
    path("unified/search/", UnifiedSearchView.as_view(), name="unified_search"),
    path("unified/question/", UnifiedQuestionView.as_view(), name="unified_question"),
    path("unified/extract/", UnifiedExtractionView.as_view(), name="unified_extract"),
    path("unified/status/", service_status, name="unified_status"),
]
