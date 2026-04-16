/**
 * 统一RAG工作台API接口定义
 * 完全重构版本 - 不依赖任何旧组件
 */

// API基础配置
import { API_CONFIG as MAIN_API_CONFIG, REQUEST_CONFIG as MAIN_REQUEST_CONFIG } from '@/config/api'

export const API_CONFIG = {
  BASE_URL: MAIN_API_CONFIG.BASE_URL || '',
  TIMEOUT: MAIN_REQUEST_CONFIG.TIMEOUT ?? 30000,
  RETRY_ATTEMPTS: MAIN_REQUEST_CONFIG.RETRY_COUNT ?? 3,
  RETRY_DELAY: MAIN_REQUEST_CONFIG.RETRY_DELAY ?? 1000
}

// API端点定义
export const API_ENDPOINTS = {
  // 陨石搜索相关
  METEORITE: {
    SEARCH: '/api/meteorite/meteorites/',
    DETAIL: '/api/meteorite/meteorites/{id}/',
    REVIEW_PENDING: '/api/meteorite/review/pending/',
    REVIEW_DETAILS: '/api/meteorite/review/details/{id}/',
    REVIEW_SUBMIT: '/api/meteorite/review/submit/',
    REVIEW_BATCH: '/api/meteorite/review/batch/',
    REVIEW_STATISTICS: '/api/meteorite/review/statistics/',
    REVIEW_HISTORY: '/api/meteorite/review/history/{id}/',
    REVIEW_DASHBOARD: '/api/meteorite/review/dashboard/',
    EXTRACTION_TASKS: '/api/meteorite/extraction/tasks/',
    EXTRACTION_TASK_DETAIL: '/api/meteorite/extraction/task/{task_id}/',
    STOP_TASK: '/api/meteorite/stop-task/{task_id}/'
  },

  // 文档管理相关
  DOCUMENT: {
    LIST: '/api/pdf/documents/',
    UPLOAD: '/api/pdf/documents/',
    DETAIL: '/api/pdf/documents/{id}/',
    DELETE: '/api/pdf/documents/{id}/',
    PROCESS: '/api/pdf/documents/{id}/process/',
    STATUS: '/api/pdf/documents/{id}/status/',
    CHUNKS: '/api/pdf/chunks/',
    WEAVIATE_PDFS: '/api/pdf/weaviate-pdfs/'
  },

  // 智能问答相关
  QA: {
    ASK: '/api/pdf/qa/ask/',
    ASK_OPTIMIZED: '/api/pdf/qa/ask_optimized/',
    DEMO: '/api/pdf/qa/demo/',
    PREVIEW_SEARCH: '/api/pdf/qa/preview-search/',
    RESET_BATCH: '/api/pdf/qa/reset-batch/',
    PROGRESS: '/api/pdf/qa/progress/'
  },

  // 数据提取相关
  EXTRACTION: {
    TASKS: '/api/pdf/extraction/tasks/',
    START_FROM_DB: '/api/pdf/extraction/start-from-db/',
    START_BATCH: '/api/pdf/extraction/start-batch/',
    CONFIRM_SAVE: '/api/pdf/extraction/confirm-save/',
    SEARCH_SEGMENTS: '/api/pdf/extraction/search-segments/',
    EXTRACT_SEGMENTS: '/api/pdf/extraction/extract-segments/',
    PROGRESS: '/api/pdf/extraction/progress/{task_id}/',
    PAUSE: '/api/pdf/extraction/pause/{task_id}/',
    RESUME: '/api/pdf/extraction/resume/{task_id}/',
    STOP: '/api/pdf/extraction/stop/{task_id}/',
    TASK_STATUS: '/api/pdf/extraction/task-status/{task_id}/',
    CLEANUP_STALE: '/api/pdf/extraction/cleanup-stale/',
    FORCE_CLEANUP: '/api/pdf/extraction/force-cleanup/',
    RUNNING_STATUS: '/api/pdf/extraction/running-status/'
  },

  // 直接处理相关
  DIRECT_PROCESSING: {
    UPLOAD: '/api/direct-processing/process/',
    PROCESS: '/api/direct-processing/process/',
    STATUS: '/api/direct-processing/status/{task_id}/',
    RESULT: '/api/direct-processing/result/{result_id}/',
    DOWNLOAD: '/api/direct-processing/download/{result_id}/',
    HISTORY: '/api/direct-processing/history/',
    DELETE: '/api/direct-processing/result/{result_id}/delete/'
  },

  // 分析结果相关
  ANALYSIS: {
    RESULTS: '/api/analysis/results/',
    RESULT_DETAIL: '/api/analysis/results/{id}/',
    EXPORT: '/api/analysis/export/{id}/',
    REPORT: '/api/analysis/report/{id}/',
    STATISTICS: '/api/analysis/statistics/',
    VISUALIZATION: '/api/analysis/visualization/{id}/'
  },

  // 认证相关
  AUTH: {
    LOGIN: '/api/pdf/auth/login/',
    REGISTER: '/api/pdf/auth/register/',
    LOGOUT: '/api/pdf/auth/logout/',
    USER_INFO: '/api/pdf/auth/user-info/',
    UPDATE_PROFILE: '/api/pdf/auth/update-profile/',
    CHANGE_PASSWORD: '/api/pdf/auth/change-password/'
  },

  // 系统相关
  SYSTEM: {
    HEALTH: '/api/pdf/health/',
    HEALTH_QUICK: '/api/pdf/health/quick/',
    METRICS: '/api/pdf/metrics/'
  }
}

// API请求方法
export const HTTP_METHODS = {
  GET: 'GET',
  POST: 'POST',
  PUT: 'PUT',
  PATCH: 'PATCH',
  DELETE: 'DELETE'
}

// 响应状态码
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  INTERNAL_SERVER_ERROR: 500
}

// 错误类型
export const ERROR_TYPES = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  AUTHENTICATION_ERROR: 'AUTHENTICATION_ERROR',
  AUTHORIZATION_ERROR: 'AUTHORIZATION_ERROR',
  NOT_FOUND_ERROR: 'NOT_FOUND_ERROR',
  SERVER_ERROR: 'SERVER_ERROR',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR'
}

// 请求状态
export const REQUEST_STATUS = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error'
}

// 处理状态
export const PROCESSING_STATUS = {
  IDLE: 'idle',
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
}

// 文档状态
export const DOCUMENT_STATUS = {
  UPLOADING: 'uploading',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  DELETED: 'deleted'
}

// 提取任务状态
export const EXTRACTION_STATUS = {
  PENDING: 'pending',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
}

// 工作流步骤
export const WORKFLOW_STEPS = {
  DOCUMENT_UPLOAD: 'document_upload',
  DOCUMENT_PROCESSING: 'document_processing',
  DATA_EXTRACTION: 'data_extraction',
  RESULT_ANALYSIS: 'result_analysis',
  REPORT_GENERATION: 'report_generation'
}

// 工作流状态
export const WORKFLOW_STATUS = {
  NOT_STARTED: 'not_started',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled'
}

// 标签页类型
export const TAB_TYPES = {
  METEORITE_SEARCH: 'meteorite-search',
  DOCUMENT_MANAGEMENT: 'document-management',
  INTELLIGENT_QA: 'intelligent-qa',
  DATA_EXTRACTION: 'data-extraction',
  DIRECT_PROCESSING: 'direct-processing',
  ANALYSIS_RESULTS: 'analysis-results'
}

// 导出格式
export const EXPORT_FORMATS = {
  JSON: 'json',
  CSV: 'csv',
  PDF: 'pdf',
  EXCEL: 'excel',
  XML: 'xml'
}

// 文件类型
export const FILE_TYPES = {
  PDF: 'pdf',
  DOC: 'doc',
  DOCX: 'docx',
  TXT: 'txt',
  RTF: 'rtf'
}

// 支持的MIME类型
export const MIME_TYPES = {
  PDF: 'application/pdf',
  DOC: 'application/msword',
  DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  TXT: 'text/plain',
  RTF: 'application/rtf'
}

// 文件大小限制（字节）
export const FILE_SIZE_LIMITS = {
  PDF: 50 * 1024 * 1024, // 50MB
  DOC: 20 * 1024 * 1024, // 20MB
  DOCX: 20 * 1024 * 1024, // 20MB
  TXT: 10 * 1024 * 1024, // 10MB
  RTF: 10 * 1024 * 1024 // 10MB
}

// 分页配置
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100]
}

// 缓存配置
export const CACHE_CONFIG = {
  DEFAULT_TTL: 5 * 60 * 1000, // 5分钟
  LONG_TTL: 30 * 60 * 1000, // 30分钟
  SHORT_TTL: 1 * 60 * 1000 // 1分钟
}

// 重试配置
export const RETRY_CONFIG = {
  MAX_ATTEMPTS: 3,
  BASE_DELAY: 1000,
  MAX_DELAY: 10000,
  BACKOFF_FACTOR: 2
}

// 超时配置
export const TIMEOUT_CONFIG = {
  DEFAULT: 30000, // 30秒
  UPLOAD: 300000, // 5分钟
  PROCESSING: 600000, // 10分钟
  DOWNLOAD: 120000 // 2分钟
}
