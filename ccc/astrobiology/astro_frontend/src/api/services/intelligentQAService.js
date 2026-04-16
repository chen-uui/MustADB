/**
 * 智能问答API服务
 * 完全重构版本 - 直接调用后端API，不依赖旧组件
 */

import { api } from '../client.js'
import { API_ENDPOINTS } from '../interfaces.js'

class IntelligentQAService {
  /**
   * 提交问题
   * @param {Object} questionData - 问题数据
   * @param {string} questionData.question - 问题内容
   * @param {number} questionData.document_id - 文档ID（可选）
   * @param {Object} questionData.context - 上下文信息（可选）
   * @param {Object} questionData.options - 问答选项（可选）
   * @returns {Promise<Object>} 问答结果
   */
  async askQuestion(questionData) {
    return await api.post(API_ENDPOINTS.QA.ASK, questionData, {
      cache: false,
      timeout: 60000 // 1分钟超时
    })
  }

  /**
   * 优化版问答
   * @param {Object} questionData - 问题数据
   * @returns {Promise<Object>} 问答结果
   */
  async askQuestionOptimized(questionData) {
    return await api.post(API_ENDPOINTS.QA.ASK_OPTIMIZED, questionData, {
      cache: false,
      timeout: 60000
    })
  }

  /**
   * 获取问答演示
   * @param {Object} params - 演示参数
   * @returns {Promise<Object>} 演示结果
   */
  async getQADemo(params = {}) {
    return await api.get(API_ENDPOINTS.QA.DEMO, params, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 预览搜索
   * @param {Object} searchParams - 搜索参数
   * @param {string} searchParams.query - 搜索关键词
   * @param {number} searchParams.document_id - 文档ID（可选）
   * @returns {Promise<Object>} 预览搜索结果
   */
  async previewSearch(searchParams) {
    return await api.post(API_ENDPOINTS.QA.PREVIEW_SEARCH, searchParams, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 重置批量提取状态
   * @returns {Promise<Object>} 重置结果
   */
  async resetBatchExtractionState() {
    return await api.post(API_ENDPOINTS.QA.RESET_BATCH, {}, {
      cache: false
    })
  }

  /**
   * 获取提取进度
   * @param {Object} params - 查询参数
   * @returns {Promise<Object>} 提取进度
   */
  async getExtractionProgress(params = {}) {
    return await api.get(API_ENDPOINTS.QA.PROGRESS, params, {
      cache: false
    })
  }

  /**
   * 获取问答历史
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   * @param {number} params.document_id - 文档ID（可选）
   * @param {string} params.date_from - 开始日期（可选）
   * @param {string} params.date_to - 结束日期（可选）
   * @returns {Promise<Object>} 问答历史
   */
  async getQAHistory(params = {}) {
    return await api.get(`${API_ENDPOINTS.QA.ASK}history/`, params, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 搜索问答历史
   * @param {Object} searchParams - 搜索参数
   * @param {string} searchParams.query - 搜索关键词
   * @param {number} searchParams.document_id - 文档ID（可选）
   * @returns {Promise<Object>} 搜索结果
   */
  async searchQAHistory(searchParams) {
    return await api.get(`${API_ENDPOINTS.QA.ASK}search/`, searchParams, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 获取问答统计
   * @returns {Promise<Object>} 问答统计
   */
  async getQAStatistics() {
    return await api.get(`${API_ENDPOINTS.QA.ASK}statistics/`, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 导出问答历史
   * @param {Object} params - 导出参数
   * @param {string} params.format - 导出格式
   * @param {number} params.document_id - 文档ID（可选）
   * @param {string} params.date_from - 开始日期（可选）
   * @param {string} params.date_to - 结束日期（可选）
   * @returns {Promise<Blob>} 导出文件
   */
  async exportQAHistory(params) {
    return await api.download(`${API_ENDPOINTS.QA.ASK}export/`, null, {
      params
    })
  }

  /**
   * 删除问答记录
   * @param {number} qaId - 问答记录ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteQARecord(qaId) {
    return await api.delete(`${API_ENDPOINTS.QA.ASK}${qaId}/`, {
      cache: false
    })
  }

  /**
   * 批量删除问答记录
   * @param {Array<number>} qaIds - 问答记录ID数组
   * @returns {Promise<Array>} 删除结果数组
   */
  async deleteQARecords(qaIds) {
    const deletePromises = qaIds.map(async (qaId) => {
      try {
        const result = await this.deleteQARecord(qaId)
        return { success: true, id: qaId, result }
      } catch (error) {
        return { success: false, id: qaId, error: error.message }
      }
    })

    return await Promise.all(deletePromises)
  }

  /**
   * 评价问答质量
   * @param {number} qaId - 问答记录ID
   * @param {Object} rating - 评价数据
   * @param {number} rating.score - 评分（1-5）
   * @param {string} rating.feedback - 反馈意见（可选）
   * @returns {Promise<Object>} 评价结果
   */
  async rateQA(qaId, rating) {
    return await api.post(`${API_ENDPOINTS.QA.ASK}${qaId}/rate/`, rating, {
      cache: false
    })
  }

  /**
   * 获取相关文档
   * @param {string} question - 问题内容
   * @param {Object} options - 选项
   * @param {number} options.limit - 限制数量
   * @param {number} options.threshold - 相似度阈值
   * @returns {Promise<Array>} 相关文档列表
   */
  async getRelatedDocuments(question, options = {}) {
    return await api.post(`${API_ENDPOINTS.QA.ASK}related-documents/`, {
      question,
      ...options
    }, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 获取问题建议
   * @param {number} documentId - 文档ID
   * @param {Object} options - 选项
   * @param {number} options.limit - 建议数量
   * @returns {Promise<Array>} 问题建议列表
   */
  async getQuestionSuggestions(documentId, options = {}) {
    return await api.get(`${API_ENDPOINTS.QA.ASK}suggestions/`, {
      document_id: documentId,
      ...options
    }, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 获取上下文信息
   * @param {number} qaId - 问答记录ID
   * @returns {Promise<Object>} 上下文信息
   */
  async getContext(qaId) {
    return await api.get(`${API_ENDPOINTS.QA.ASK}${qaId}/context/`, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 更新上下文
   * @param {number} qaId - 问答记录ID
   * @param {Object} context - 上下文数据
   * @returns {Promise<Object>} 更新结果
   */
  async updateContext(qaId, context) {
    return await api.patch(`${API_ENDPOINTS.QA.ASK}${qaId}/context/`, context, {
      cache: false
    })
  }

  /**
   * 获取AI状态
   * @returns {Promise<Object>} AI状态
   */
  async getAIStatus() {
    return await api.get(`${API_ENDPOINTS.QA.ASK}ai-status/`, {}, {
      cache: true,
      cacheTTL: 30 * 1000 // 30秒缓存
    })
  }

  /**
   * 测试AI连接
   * @returns {Promise<Object>} 连接测试结果
   */
  async testAIConnection() {
    return await api.get(`${API_ENDPOINTS.QA.ASK}test-connection/`, {}, {
      cache: false
    })
  }

  /**
   * 获取问答配置
   * @returns {Promise<Object>} 问答配置
   */
  async getQAConfig() {
    return await api.get(`${API_ENDPOINTS.QA.ASK}config/`, {}, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 更新问答配置
   * @param {Object} config - 配置数据
   * @returns {Promise<Object>} 更新结果
   */
  async updateQAConfig(config) {
    return await api.patch(`${API_ENDPOINTS.QA.ASK}config/`, config, {
      cache: false
    })
  }
}

// 创建单例实例
const intelligentQAService = new IntelligentQAService()

export default intelligentQAService
export { IntelligentQAService }