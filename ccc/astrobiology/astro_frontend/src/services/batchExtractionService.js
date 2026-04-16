import { apiMethods as api } from '../utils/apiClient'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess } from '@/utils/apiResponse'

export class BatchExtractionService {
  /**
   * 启动批量提取任务
   * @param {Object} params - 提取参数
   * @param {Array} params.search_queries - 搜索关键词数组
   * @param {number} params.batch_size - 批次大小
   * @param {Object} params.extraction_options - 提取选项
   * @returns {Promise<Object>} 任务信息
   */
  static async startExtraction(params) {
    try {
      const response = ensureApiSuccess(await api.post('/pdf_processor/extraction/start-batch/', params), '启动批量提取失败')
      return {
        success: true,
        data: response
      }
    } catch (error) {
      return {
        success: false,
        error: getApiErrorMessage(error, '启动批量提取失败')
      }
    }
  }

  /**
   * 获取任务状态
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 任务状态信息
   */
  static async getTaskStatus(taskId) {
    try {
      return ensureApiSuccess(await api.get(`/pdf_processor/extraction/task-status/${taskId}/`), '获取任务状态失败')
    } catch (error) {
      throw new Error(getApiErrorMessage(error, '获取任务状态失败'))
    }
  }

  /**
   * 暂停任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 操作结果
   */
  static async pauseTask(taskId) {
    try {
      return ensureApiSuccess(await api.post(`/pdf_processor/extraction/pause/${taskId}/`), '暂停任务失败')
    } catch (error) {
      throw new Error(getApiErrorMessage(error, '暂停任务失败'))
    }
  }

  /**
   * 取消任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 操作结果
   */
  static async cancelTask(taskId) {
    try {
      return ensureApiSuccess(await api.post(`/pdf_processor/extraction/stop/${taskId}/`), '取消任务失败')
    } catch (error) {
      throw new Error(getApiErrorMessage(error, '取消任务失败'))
    }
  }

  /**
   * 确认并保存预览数据
   * @param {Object} params - 保存参数
   * @param {string} params.task_id - 任务ID
   * @param {Array} params.selected_data - 选中的数据
   * @returns {Promise<Object>} 保存结果
   */
  static async confirmAndSave(params) {
    try {
      const response = ensureApiSuccess(await api.post('/pdf_processor/extraction/confirm-and-save/', params), '确认保存失败')
      return {
        success: true,
        data: response
      }
    } catch (error) {
      return {
        success: false,
        error: getApiErrorMessage(error, '确认保存失败')
      }
    }
  }

  /**
   * 获取提取历史
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页大小
   * @returns {Promise<Object>} 历史记录
   */
  static async getExtractionHistory(params = {}) {
    try {
      const response = ensureApiSuccess(await api.get('/pdf_processor/extraction_history/', { params }), '获取提取历史失败')
      return {
        success: true,
        data: response
      }
    } catch (error) {
      return {
        success: false,
        error: getApiErrorMessage(error, '获取提取历史失败')
      }
    }
  }

  /**
   * 删除提取任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 删除结果
   */
  static async deleteTask(taskId) {
    try {
      const response = ensureApiSuccess(await api.delete(`/pdf_processor/task/${taskId}/`), '删除任务失败')
      return {
        success: true,
        data: response
      }
    } catch (error) {
      return {
        success: false,
        error: getApiErrorMessage(error, '删除任务失败')
      }
    }
  }

  /**
   * 获取系统统计信息
   * @returns {Promise<Object>} 统计信息
   */
  static async getSystemStats() {
    try {
      const response = ensureApiSuccess(await api.get('/pdf_processor/system_stats/'), '获取系统统计失败')
      return {
        success: true,
        data: response
      }
    } catch (error) {
      return {
        success: false,
        error: getApiErrorMessage(error, '获取系统统计失败')
      }
    }
  }
}

export default BatchExtractionService
