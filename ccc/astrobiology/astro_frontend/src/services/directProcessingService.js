import { apiMethods } from '@/utils/apiClient'
import { API_CONFIG } from '@/config/api'

class DirectProcessingService {
  async extractContent(documentId) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.EXTRACT_FROM_SELECTED_SEGMENTS, {
      document_id: documentId
    })
    return response.data
  }

  async stopTask(taskId) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.STOP_EXTRACTION_TASK(taskId))
    return response.data
  }

  async confirmSave(data) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.CONFIRM_SAVE, data)
    return response.data
  }

  async resumeTask(taskId) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.RESUME_EXTRACTION_TASK(taskId))
    return response.data
  }

  async pauseTask(taskId) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.PAUSE_EXTRACTION_TASK(taskId))
    return response.data
  }

  async startBatchExtraction(data) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.START_BATCH_EXTRACTION, data)
    return response.data
  }

  async getExtractionProgress(taskId) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.EXTRACTION_PROGRESS(taskId))
    return response.data
  }

  async resetBatchExtractionState() {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.RESET_BATCH_EXTRACTION_STATE)
    return response.data
  }

  async searchMeteoriteSegments(data) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.SEARCH_METEORITE_SEGMENTS, data)
    return response.data
  }

  async singleTaskSearch(data) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.SINGLE_TASK_SEARCH, data)
    return response.data
  }

  async singleTaskEnqueue(sessionId, segmentIds) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.SINGLE_TASK_ENQUEUE, {
      sessionId,
      segmentIds
    })
    return response.data
  }

  async singleTaskStatus(sessionId) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.SINGLE_TASK_STATUS, {
      params: { sessionId }
    })
    return response.data
  }

  async singleTaskCancel(sessionId) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.SINGLE_TASK_CANCEL, { sessionId })
    return response.data
  }

  async singleTaskSegments(sessionId, page = 1, pageSize = 50) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.SINGLE_TASK_SEGMENTS, {
      params: { sessionId, page, pageSize }
    })
    return response.data
  }

  async extractFromSelectedSegments(data) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.EXTRACT_FROM_SELECTED_SEGMENTS, data)
    return response.data
  }

  async getExtractionTasksList(params = {}) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.EXTRACTION_TASKS, { params })
    return response.data
  }

  async getExtractionTasks(params = {}) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.EXTRACTION_TASKS, { params })
    return response.data
  }

  async startExtraction(formData) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.START_FROM_DB, formData)
    return response.data
  }

  async getTaskDetails(taskId) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.REVIEW_TASK_DETAILS(taskId))
    return response.data
  }

  async deleteTask(taskId) {
    const response = await apiMethods.delete(API_CONFIG.ENDPOINTS.DELETE_TASK(taskId))
    return response.data
  }

  async previewSearch(searchParams) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.PREVIEW_SEARCH, searchParams)
    return response.data
  }

  async startFromDB(extractionData) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.START_FROM_DB, extractionData)
    return response.data
  }

  async cleanupStaleTasks() {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.CLEANUP_STALE_TASKS)
    return response.data
  }

  async forceCleanupAllRunningTasks() {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.FORCE_CLEANUP_ALL_RUNNING_TASKS)
    return response.data
  }

  async getRunningTasksStatus() {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.GET_RUNNING_TASKS_STATUS)
    return response.data
  }
}

const directProcessingService = new DirectProcessingService()

export { directProcessingService as DirectProcessingService }
export default directProcessingService
