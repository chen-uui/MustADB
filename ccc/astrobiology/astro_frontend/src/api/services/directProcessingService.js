/**
 * 直接处理API服务
 * 完全重构版本 - 直接调用后端API，不依赖旧组件
 */

import { api } from '../client.js'
import { API_ENDPOINTS, FILE_SIZE_LIMITS, MIME_TYPES } from '../interfaces.js'

class DirectProcessingService {
  /**
   * 上传文件进行直接处理
   * @param {File} file - 文件对象
   * @param {Function} onProgress - 进度回调
   * @param {Object} options - 上传选项
   * @returns {Promise<Object>} 上传结果
   */
  async uploadFile(file, onProgress = null, options = {}) {
    this.validateFile(file)

    const uploadOptions = {
      timeout: 300000, // 5分钟超时
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress(percentCompleted)
        }
      },
      ...options
    }

    const formData = new FormData()
    formData.append('file', file)
    return await api.upload(API_ENDPOINTS.DIRECT_PROCESSING.UPLOAD, formData, uploadOptions)
  }

  /**
   * 开始处理文件
   * @param {Object} processData - 处理数据
   * @param {string} processData.file_id - 文件ID
   * @param {string} processData.analysis_focus - 分析重点
   * @param {string} processData.detail_level - 详细程度
   * @param {string} processData.output_format - 输出格式
   * @param {Object} processData.options - 处理选项
   * @returns {Promise<Object>} 处理结果
   */
  async processFile(processData) {
    return await api.post(API_ENDPOINTS.DIRECT_PROCESSING.PROCESS, processData, {
      cache: false
    })
  }

  /**
   * 获取处理状态
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 处理状态
   */
  async getProcessingStatus(taskId) {
    const url = API_ENDPOINTS.DIRECT_PROCESSING.STATUS.replace('{task_id}', taskId)
    return await api.get(url, {}, {
      cache: false
    })
  }

  /**
   * 获取处理结果
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 处理结果
   */
  async getProcessingResult(taskId) {
    const url = API_ENDPOINTS.DIRECT_PROCESSING.RESULT.replace('{result_id}', taskId)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 下载处理结果
   * @param {string} taskId - 任务ID
   * @param {string} filename - 文件名
   * @returns {Promise<Blob>} 下载文件
   */
  async downloadResult(taskId, filename = null) {
    const url = API_ENDPOINTS.DIRECT_PROCESSING.DOWNLOAD.replace('{task_id}', taskId)
    return await api.download(url, filename)
  }

  /**
   * 获取处理历史
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   * @param {string} params.status - 处理状态
   * @param {string} params.date_from - 开始日期
   * @param {string} params.date_to - 结束日期
   * @returns {Promise<Object>} 处理历史
   */
  async getProcessingHistory(params = {}) {
    return await api.get(API_ENDPOINTS.DIRECT_PROCESSING.HISTORY, params, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 删除处理任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteTask(taskId) {
    const url = API_ENDPOINTS.DIRECT_PROCESSING.DELETE.replace('{result_id}', taskId)
    return await api.delete(url, {
      cache: false
    })
  }

  /**
   * 批量删除处理任务
   * @param {Array<string>} taskIds - 任务ID数组
   * @returns {Promise<Array>} 删除结果数组
   */
  async deleteTasks(taskIds) {
    const deletePromises = taskIds.map(async (taskId) => {
      try {
        const result = await this.deleteTask(taskId)
        return { success: true, id: taskId, result }
      } catch (error) {
        return { success: false, id: taskId, error: error.message }
      }
    })

    return await Promise.all(deletePromises)
  }

  /**
   * 取消处理任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 取消结果
   */
  async cancelTask(taskId) {
    return await api.post(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}cancel/${taskId}/`, {}, {
      cache: false
    })
  }

  /**
   * 重新处理任务
   * @param {string} taskId - 任务ID
   * @param {Object} options - 重新处理选项
   * @returns {Promise<Object>} 重新处理结果
   */
  async reprocessTask(taskId, options = {}) {
    return await api.post(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}reprocess/${taskId}/`, options, {
      cache: false
    })
  }

  /**
   * 获取处理统计
   * @returns {Promise<Object>} 处理统计
   */
  async getProcessingStatistics() {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}statistics/`, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 获取处理配置
   * @returns {Promise<Object>} 处理配置
   */
  async getProcessingConfig() {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}config/`, {}, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 更新处理配置
   * @param {Object} config - 配置数据
   * @returns {Promise<Object>} 更新结果
   */
  async updateProcessingConfig(config) {
    return await api.patch(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}config/`, config, {
      cache: false
    })
  }

  /**
   * 获取支持的分析重点
   * @returns {Promise<Array>} 分析重点列表
   */
  async getAnalysisFocuses() {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}focuses/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000 // 30分钟缓存
    })
  }

  /**
   * 获取支持的详细程度
   * @returns {Promise<Array>} 详细程度列表
   */
  async getDetailLevels() {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}detail-levels/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 获取支持的输出格式
   * @returns {Promise<Array>} 输出格式列表
   */
  async getOutputFormats() {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}output-formats/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 获取处理模板
   * @param {string} templateType - 模板类型
   * @returns {Promise<Object>} 处理模板
   */
  async getProcessingTemplate(templateType) {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}templates/${templateType}/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 创建自定义处理模板
   * @param {Object} templateData - 模板数据
   * @returns {Promise<Object>} 创建结果
   */
  async createProcessingTemplate(templateData) {
    return await api.post(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}templates/`, templateData, {
      cache: false
    })
  }

  /**
   * 更新处理模板
   * @param {string} templateId - 模板ID
   * @param {Object} templateData - 模板数据
   * @returns {Promise<Object>} 更新结果
   */
  async updateProcessingTemplate(templateId, templateData) {
    return await api.patch(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}templates/${templateId}/`, templateData, {
      cache: false
    })
  }

  /**
   * 删除处理模板
   * @param {string} templateId - 模板ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteProcessingTemplate(templateId) {
    return await api.delete(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}templates/${templateId}/`, {
      cache: false
    })
  }

  /**
   * 导出处理历史
   * @param {Object} params - 导出参数
   * @param {string} params.format - 导出格式
   * @param {string} params.date_from - 开始日期
   * @param {string} params.date_to - 结束日期
   * @returns {Promise<Blob>} 导出文件
   */
  async exportProcessingHistory(params) {
    return await api.download(`${API_ENDPOINTS.DIRECT_PROCESSING.HISTORY}export/`, null, {
      params
    })
  }

  /**
   * 获取处理队列状态
   * @returns {Promise<Object>} 队列状态
   */
  async getQueueStatus() {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}queue-status/`, {}, {
      cache: true,
      cacheTTL: 30 * 1000 // 30秒缓存
    })
  }

  /**
   * 获取处理性能指标
   * @returns {Promise<Object>} 性能指标
   */
  async getPerformanceMetrics() {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}metrics/`, {}, {
      cache: true,
      cacheTTL: 1 * 60 * 1000 // 1分钟缓存
    })
  }

  /**
   * 验证文件
   * @param {File} file - 文件对象
   * @throws {Error} 文件验证失败
   */
  validateFile(file) {
    if (!file) {
      throw new Error('请选择文件')
    }

    // 检查文件类型
    const allowedTypes = Object.values(MIME_TYPES)
    if (!allowedTypes.includes(file.type)) {
      throw new Error('不支持的文件类型，请上传PDF、DOC、DOCX、TXT或RTF文件')
    }

    // 检查文件大小
    const maxSize = FILE_SIZE_LIMITS.PDF // 默认使用PDF限制
    if (file.size > maxSize) {
      throw new Error(`文件大小超过限制，最大允许${Math.round(maxSize / 1024 / 1024)}MB`)
    }

    // 检查文件名
    if (!file.name || file.name.trim() === '') {
      throw new Error('文件名不能为空')
    }
  }

  /**
   * 获取支持的文件类型
   * @returns {Array} 支持的文件类型
   */
  getSupportedFileTypes() {
    return [
      { type: 'pdf', mime: MIME_TYPES.PDF, extension: '.pdf', maxSize: FILE_SIZE_LIMITS.PDF },
      { type: 'doc', mime: MIME_TYPES.DOC, extension: '.doc', maxSize: FILE_SIZE_LIMITS.DOC },
      { type: 'docx', mime: MIME_TYPES.DOCX, extension: '.docx', maxSize: FILE_SIZE_LIMITS.DOCX },
      { type: 'txt', mime: MIME_TYPES.TXT, extension: '.txt', maxSize: FILE_SIZE_LIMITS.TXT },
      { type: 'rtf', mime: MIME_TYPES.RTF, extension: '.rtf', maxSize: FILE_SIZE_LIMITS.RTF }
    ]
  }

  /**
   * 获取处理进度
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 处理进度
   */
  async getProcessingProgress(taskId) {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}progress/${taskId}/`, {}, {
      cache: false
    })
  }

  /**
   * 获取处理日志
   * @param {string} taskId - 任务ID
   * @returns {Promise<Array>} 处理日志
   */
  async getProcessingLogs(taskId) {
    return await api.get(`${API_ENDPOINTS.DIRECT_PROCESSING.PROCESS}logs/${taskId}/`, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }
}

// 创建单例实例
const directProcessingService = new DirectProcessingService()

export default directProcessingService
export { DirectProcessingService }
