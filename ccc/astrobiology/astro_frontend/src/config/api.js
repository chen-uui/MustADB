export const API_CONFIG = {
  BASE_URL:
    process.env.NODE_ENV === 'production'
      ? window.location.origin
      : `http://${import.meta.env.VITE_BACKEND_HOST || 'localhost'}:${import.meta.env.VITE_BACKEND_PORT || '8000'}`,
  ENDPOINTS: {
    UPLOAD: '/api/pdf/documents/upload/',
    SEARCH: '/api/pdf/documents/search/',
    DOCUMENTS: '/api/pdf/documents/',
    STATS: '/api/pdf/documents/stats/',
    PROCESS_PENDING: '/api/pdf/documents/process_pending/',
    PROCESS_STALE: '/api/pdf/documents/process_stale/',
    REPROCESS_ALL: '/api/pdf/documents/reprocess_all/',
    SYNC_FILES: '/api/pdf/documents/sync_files/',

    DOCUMENT_DETAIL: (id) => `/api/pdf/documents/${id}/`,
    DOWNLOAD: (id) => `/api/pdf/documents/${id}/download/`,
    PROCESS_SINGLE: (id) => `/api/pdf/documents/${id}/process/`,
    DELETE: (id) => `/api/pdf/documents/${id}/`,

    QA_ASK: '/api/pdf/qa/ask/',
    QA_ASK_OPTIMIZED: '/api/pdf/qa/ask_optimized/',
    QA_STATUS: '/api/pdf/qa/status/',
    QA_DEMO: '/api/pdf/qa/demo/',
    QA_ASK_DIRECT: '/api/pdf/qa/ask_direct/',

    UNIFIED_SEARCH: '/api/pdf/unified/search/',
    UNIFIED_QUESTION: '/api/pdf/unified/question/',
    UNIFIED_EXTRACT: '/api/pdf/unified/extract/',
    UNIFIED_STATUS: '/api/pdf/unified/status/',

    CHUNKS: '/api/pdf/documents/chunks/',

    SEARCH_METEORITE_SEGMENTS: '/api/pdf/extraction/search-segments/',
    EXTRACT_FROM_SELECTED_SEGMENTS: '/api/pdf/extraction/extract-segments/',

    START_BATCH_EXTRACTION: '/api/pdf/extraction/start-batch/',
    RESET_BATCH_EXTRACTION_STATE: '/api/pdf/extraction/reset-batch-state/',

    PAUSE_EXTRACTION_TASK: (taskId) => `/api/pdf/extraction/pause/${taskId}/`,
    RESUME_EXTRACTION_TASK: (taskId) => `/api/pdf/extraction/resume/${taskId}/`,
    STOP_EXTRACTION_TASK: (taskId) => `/api/pdf/extraction/stop/${taskId}/`,
    SINGLE_TASK_SEARCH: '/api/pdf/extraction/single/search/',
    SINGLE_TASK_ENQUEUE: '/api/pdf/extraction/single/enqueue/',
    SINGLE_TASK_STATUS: '/api/pdf/extraction/single/status/',
    SINGLE_TASK_CANCEL: '/api/pdf/extraction/single/cancel/',
    SINGLE_TASK_SEGMENTS: '/api/pdf/extraction/single/segments/',

    PREVIEW_SEARCH: '/api/pdf/extraction/preview/',
    START_FROM_DB: '/api/pdf/extraction/start-from-db/',
    CONFIRM_SAVE: '/api/pdf/extraction/confirm-save/',
    EXTRACTION_PROGRESS: (taskId) => `/api/pdf/extraction/progress/${taskId}/`,
    EXTRACTION_TASKS: '/api/review/extraction-tasks/',

    CLEANUP_STALE_TASKS: '/api/pdf/tasks/cleanup-stale/',
    FORCE_CLEANUP_ALL_RUNNING_TASKS: '/api/pdf/tasks/force-cleanup/',
    GET_RUNNING_TASKS_STATUS: '/api/pdf/tasks/running-status/',

    REVIEW_DASHBOARD: '/api/review/dashboard/',
    REVIEW_EXTRACTION_TASKS: '/api/review/extraction-tasks/',
    REVIEW_TASK_DETAILS: (taskId) => `/api/review/extraction-tasks/${taskId}/`,
    DELETE_TASK: (taskId) => `/api/review/delete-task/${taskId}/`,

    METEORITE_SEARCH: '/api/meteorite/v2/approved/',
    METEORITE_OPTIONS: '/api/meteorite/meteorites/options/',
    PENDING_METEORITES: '/api/meteorite/v2/pending/',
    APPROVED_METEORITES: '/api/meteorite/v2/approved/',
    REJECTED_METEORITES: '/api/meteorite/v2/rejected/',
    APPROVE_METEORITE: (id) => `/api/meteorite/v2/pending/${id}/approve/`,
    REJECT_METEORITE: (id) => `/api/meteorite/v2/pending/${id}/reject/`,
    BATCH_APPROVE_METEORITE: () => '/api/meteorite/v2/pending/batch_approve/',
    BATCH_REJECT_METEORITE: () => '/api/meteorite/v2/pending/batch_reject/',
    APPROVE_ALL_METEORITE: () => '/api/meteorite/v2/pending/approve_all/',
    REJECT_ALL_METEORITE: () => '/api/meteorite/v2/pending/reject_all/',
    RESTORE_METEORITE: (id) => `/api/meteorite/v2/rejected/${id}/restore/`,
    PERMANENT_DELETE_METEORITE: (id) => `/api/meteorite/v2/rejected/${id}/permanent_delete/`,
    METEORITE_DETAIL: (id) => `/api/meteorite/v2/approved/${id}/`,

    PROCESSING_STATUS: '/api/pdf/documents/processing_status/',
    CANCEL_PROCESSING: '/api/pdf/documents/cancel_processing/',

    SYSTEM_HEALTH: '/api/pdf/health/',

    DIRECT_PROCESS: '/api/direct-processing/process/',
    DIRECT_PROCESS_STATUS: (taskId) => `/api/direct-processing/status/${taskId}/`,
    DIRECT_PROCESS_RESULT: (resultId) => `/api/direct-processing/result/${resultId}/`,
    DIRECT_PROCESS_DELETE: (resultId) => `/api/direct-processing/result/${resultId}/delete/`,
    DIRECT_PROCESS_BATCH: '/api/direct-processing/batch/',
    DIRECT_PROCESS_HISTORY: '/api/direct-processing/history/',
    DIRECT_PROCESS_STATISTICS: '/api/direct-processing/statistics/'
  }
}

export const REQUEST_CONFIG = {
  TIMEOUT: 300000,
  RETRY_COUNT: 3,
  RETRY_DELAY: 2000
}
