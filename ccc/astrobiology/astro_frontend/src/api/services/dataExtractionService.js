/**
 * 数据提取API服务
 * 完全重构版本 - 直接调用后端API，不依赖旧组件
 */

import { api } from '../client.js'
import { API_ENDPOINTS, EXTRACTION_STATUS } from '../interfaces.js'

class DataExtractionService {
  /**
   * 获取提取任务列表
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   * @param {string} params.status - 任务状态
   * @param {string} params.document_id - 文档ID
   * @returns {Promise<Object>} 任务列表
   */
  async getExtractionTasks(params = {}) {
    return await api.get(API_ENDPOINTS.EXTRACTION.TASKS, params, {
      cache: true,
      cacheTTL: 1 * 60 * 1000 // 1分钟缓存
    })
  }

  /**
   * 从数据库开始提取
   * @param {Object} extractionData - 提取数据
   * @param {number} extractionData.document_id - 文档ID
   * @param {string} extractionData.extraction_type - 提取类型
   * @param {Object} extractionData.options - 提取选项
   * @returns {Promise<Object>} 提取结果
   */
  async startExtractionFromDB(extractionData) {
    return await api.post(API_ENDPOINTS.EXTRACTION.START_FROM_DB, extractionData, {
      cache: false
    })
  }

  /**
   * 开始批量提取
   * @param {Object} batchData - 批量提取数据
   * @param {Array<number>} batchData.document_ids - 文档ID数组
   * @param {string} batchData.extraction_type - 提取类型
   * @param {Object} batchData.options - 提取选项
   * @returns {Promise<Object>} 批量提取结果
   */
  async startBatchExtraction(batchData) {
    return await api.post(API_ENDPOINTS.EXTRACTION.START_BATCH, batchData, {
      cache: false
    })
  }

  /**
   * 确认并保存提取结果
   * @param {Object} saveData - 保存数据
   * @param {string} saveData.task_id - 任务ID
   * @param {Object} saveData.extracted_data - 提取的数据
   * @param {Object} saveData.validation_results - 验证结果
   * @returns {Promise<Object>} 保存结果
   */
  async confirmAndSaveExtraction(saveData) {
    return await api.post(API_ENDPOINTS.EXTRACTION.CONFIRM_SAVE, saveData, {
      cache: false
    })
  }

  /**
   * 搜索陨石段落
   * @param {Object} searchParams - 搜索参数
   * @param {string} searchParams.query - 搜索关键词
   * @param {number} searchParams.document_id - 文档ID
   * @param {Object} searchParams.options - 搜索选项
   * @returns {Promise<Object>} 搜索结果
   */
  async searchMeteoriteSegments(searchParams) {
    return await api.post(API_ENDPOINTS.EXTRACTION.SEARCH_SEGMENTS, searchParams, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 从选定段落提取数据
   * @param {Object} extractionData - 提取数据
   * @param {Array<string>} extractionData.segment_ids - 段落ID数组
   * @param {string} extractionData.extraction_type - 提取类型
   * @param {Object} extractionData.options - 提取选项
   * @returns {Promise<Object>} 提取结果
   */
  async extractFromSelectedSegments(extractionData) {
    return await api.post(API_ENDPOINTS.EXTRACTION.EXTRACT_SEGMENTS, extractionData, {
      cache: false
    })
  }

  /**
   * 获取提取进度
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 提取进度
   */
  async getExtractionProgress(taskId) {
    const url = API_ENDPOINTS.EXTRACTION.PROGRESS.replace('{task_id}', taskId)
    return await api.get(url, {}, {
      cache: false
    })
  }

  /**
   * 暂停提取任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 暂停结果
   */
  async pauseExtractionTask(taskId) {
    const url = API_ENDPOINTS.EXTRACTION.PAUSE.replace('{task_id}', taskId)
    return await api.post(url, {}, {
      cache: false
    })
  }

  /**
   * 恢复提取任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 恢复结果
   */
  async resumeExtractionTask(taskId) {
    const url = API_ENDPOINTS.EXTRACTION.RESUME.replace('{task_id}', taskId)
    return await api.post(url, {}, {
      cache: false
    })
  }

  /**
   * 停止提取任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 停止结果
   */
  async stopExtractionTask(taskId) {
    const url = API_ENDPOINTS.EXTRACTION.STOP.replace('{task_id}', taskId)
    return await api.post(url, {}, {
      cache: false
    })
  }

  /**
   * 获取任务状态
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 任务状态
   */
  async getTaskStatus(taskId) {
    const url = API_ENDPOINTS.EXTRACTION.TASK_STATUS.replace('{task_id}', taskId)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 30 * 1000 // 30秒缓存
    })
  }

  /**
   * 清理过期任务
   * @returns {Promise<Object>} 清理结果
   */
  async cleanupStaleTasks() {
    return await api.post(API_ENDPOINTS.EXTRACTION.CLEANUP_STALE, {}, {
      cache: false
    })
  }

  /**
   * 强制清理所有运行中的任务
   * @returns {Promise<Object>} 清理结果
   */
  async forceCleanupAllRunningTasks() {
    return await api.post(API_ENDPOINTS.EXTRACTION.FORCE_CLEANUP, {}, {
      cache: false
    })
  }

  /**
   * 获取运行中任务状态
   * @returns {Promise<Object>} 运行中任务状态
   */
  async getRunningTasksStatus() {
    return await api.get(API_ENDPOINTS.EXTRACTION.RUNNING_STATUS, {}, {
      cache: true,
      cacheTTL: 30 * 1000
    })
  }

  /**
   * 获取提取结果
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 提取结果
   */
  async getExtractionResult(taskId) {
    return await api.get(`${API_ENDPOINTS.EXTRACTION.TASKS}${taskId}/result/`, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 验证提取结果
   * @param {string} taskId - 任务ID
   * @param {Object} validationData - 验证数据
   * @returns {Promise<Object>} 验证结果
   */
  async validateExtractionResult(taskId, validationData) {
    return await api.post(`${API_ENDPOINTS.EXTRACTION.TASKS}${taskId}/validate/`, validationData, {
      cache: false
    })
  }

  /**
   * 导出提取结果
   * @param {string} taskId - 任务ID
   * @param {string} format - 导出格式
   * @returns {Promise<Blob>} 导出文件
   */
  async exportExtractionResult(taskId, format = 'json') {
    return await api.download(`${API_ENDPOINTS.EXTRACTION.TASKS}${taskId}/export/`, null, {
      params: { format }
    })
  }

  /**
   * 获取提取统计
   * @returns {Promise<Object>} 提取统计
   */
  async getExtractionStatistics() {
    return await api.get(`${API_ENDPOINTS.EXTRACTION.TASKS}statistics/`, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 获取提取配置
   * @returns {Promise<Object>} 提取配置
   */
  async getExtractionConfig() {
    return await api.get(`${API_ENDPOINTS.EXTRACTION.TASKS}config/`, {}, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 更新提取配置
   * @param {Object} config - 配置数据
   * @returns {Promise<Object>} 更新结果
   */
  async updateExtractionConfig(config) {
    return await api.patch(`${API_ENDPOINTS.EXTRACTION.TASKS}config/`, config, {
      cache: false
    })
  }

  /**
   * 获取支持的提取类型
   * @returns {Promise<Array>} 提取类型列表
   */
  async getSupportedExtractionTypes() {
    return await api.get(`${API_ENDPOINTS.EXTRACTION.TASKS}types/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000 // 30分钟缓存
    })
  }

  /**
   * 获取提取模板
   * @param {string} extractionType - 提取类型
   * @returns {Promise<Object>} 提取模板
   */
  async getExtractionTemplate(extractionType) {
    return await api.get(`${API_ENDPOINTS.EXTRACTION.TASKS}templates/${extractionType}/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 创建自定义提取模板
   * @param {Object} templateData - 模板数据
   * @returns {Promise<Object>} 创建结果
   */
  async createExtractionTemplate(templateData) {
    return await api.post(`${API_ENDPOINTS.EXTRACTION.TASKS}templates/`, templateData, {
      cache: false
    })
  }

  /**
   * 更新提取模板
   * @param {string} templateId - 模板ID
   * @param {Object} templateData - 模板数据
   * @returns {Promise<Object>} 更新结果
   */
  async updateExtractionTemplate(templateId, templateData) {
    return await api.patch(`${API_ENDPOINTS.EXTRACTION.TASKS}templates/${templateId}/`, templateData, {
      cache: false
    })
  }

  /**
   * 删除提取模板
   * @param {string} templateId - 模板ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteExtractionTemplate(templateId) {
    return await api.delete(`${API_ENDPOINTS.EXTRACTION.TASKS}templates/${templateId}/`, {
      cache: false
    })
  }

  /**
   * 获取提取历史
   * @param {Object} params - 查询参数
   * @returns {Promise<Object>} 提取历史
   */
  async getExtractionHistory(params = {}) {
    return await api.get(`${API_ENDPOINTS.EXTRACTION.TASKS}history/`, params, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 重新运行提取任务
   * @param {string} taskId - 任务ID
   * @param {Object} options - 重新运行选项
   * @returns {Promise<Object>} 重新运行结果
   */
  async rerunExtractionTask(taskId, options = {}) {
    return await api.post(`${API_ENDPOINTS.EXTRACTION.TASKS}${taskId}/rerun/`, options, {
      cache: false
    })
  }
}

// 创建单例实例
const dataExtractionService = new DataExtractionService()

export default dataExtractionService
export { DataExtractionService }