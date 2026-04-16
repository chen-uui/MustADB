/**
 * 陨石搜索API服务
 * 完全重构版本 - 直接调用后端API，不依赖旧组件
 */

import { api } from '../client.js'
import { API_ENDPOINTS, PAGINATION } from '../interfaces.js'

class MeteoriteSearchService {
  /**
   * 搜索陨石
   * @param {Object} params - 搜索参数
   * @param {string} params.name - 陨石名称
   * @param {string} params.classification - 分类
   * @param {string} params.discovery_location - 发现地点
   * @param {string} params.origin - 来源
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   * @returns {Promise<Object>} 搜索结果
   */
  async searchMeteorites(params = {}) {
    const searchParams = {
      page: params.page || 1,
      page_size: params.page_size || PAGINATION.DEFAULT_PAGE_SIZE
    }

    // 处理搜索参数
    if (params.name) {
      searchParams.search = params.name
    }
    
    // 处理精确过滤参数
    if (params.classification) {
      searchParams.classification = params.classification
    }
    if (params.discovery_location) {
      searchParams.discovery_location = params.discovery_location
    }
    if (params.origin) {
      searchParams.origin = params.origin
    }

    return await api.get(API_ENDPOINTS.METEORITE.SEARCH, searchParams, {
      cache: true,
      cacheTTL: 5 * 60 * 1000 // 5分钟缓存
    })
  }

  /**
   * 获取陨石详情
   * @param {number} id - 陨石ID
   * @returns {Promise<Object>} 陨石详情
   */
  async getMeteoriteDetail(id) {
    const url = API_ENDPOINTS.METEORITE.DETAIL.replace('{id}', id)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 10 * 60 * 1000 // 10分钟缓存
    })
  }

  /**
   * 获取待审核陨石列表
   * @param {Object} params - 查询参数
   * @returns {Promise<Object>} 待审核列表
   */
  async getPendingReviews(params = {}) {
    return await api.get(API_ENDPOINTS.METEORITE.REVIEW_PENDING, params, {
      cache: true,
      cacheTTL: 2 * 60 * 1000 // 2分钟缓存
    })
  }

  /**
   * 获取审核详情
   * @param {number} meteoriteId - 陨石ID
   * @returns {Promise<Object>} 审核详情
   */
  async getReviewDetails(meteoriteId) {
    const url = API_ENDPOINTS.METEORITE.REVIEW_DETAILS.replace('{id}', meteoriteId)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 提交审核
   * @param {Object} reviewData - 审核数据
   * @returns {Promise<Object>} 审核结果
   */
  async submitReview(reviewData) {
    return await api.post(API_ENDPOINTS.METEORITE.REVIEW_SUBMIT, reviewData, {
      cache: false
    })
  }

  /**
   * 批量审核
   * @param {Array} reviewData - 批量审核数据
   * @returns {Promise<Object>} 批量审核结果
   */
  async batchReview(reviewData) {
    return await api.post(API_ENDPOINTS.METEORITE.REVIEW_BATCH, reviewData, {
      cache: false
    })
  }

  /**
   * 获取审核统计
   * @returns {Promise<Object>} 审核统计
   */
  async getReviewStatistics() {
    return await api.get(API_ENDPOINTS.METEORITE.REVIEW_STATISTICS, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 获取审核历史
   * @param {number} meteoriteId - 陨石ID
   * @returns {Promise<Object>} 审核历史
   */
  async getReviewHistory(meteoriteId) {
    const url = API_ENDPOINTS.METEORITE.REVIEW_HISTORY.replace('{id}', meteoriteId)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 获取仪表板数据
   * @returns {Promise<Object>} 仪表板数据
   */
  async getDashboardData() {
    return await api.get(API_ENDPOINTS.METEORITE.REVIEW_DASHBOARD, {}, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 获取提取任务列表
   * @param {Object} params - 查询参数
   * @returns {Promise<Object>} 提取任务列表
   */
  async getExtractionTasks(params = {}) {
    return await api.get(API_ENDPOINTS.METEORITE.EXTRACTION_TASKS, params, {
      cache: true,
      cacheTTL: 1 * 60 * 1000 // 1分钟缓存
    })
  }

  /**
   * 获取提取任务详情
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 任务详情
   */
  async getExtractionTaskDetail(taskId) {
    const url = API_ENDPOINTS.METEORITE.EXTRACTION_TASK_DETAIL.replace('{task_id}', taskId)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 30 * 1000 // 30秒缓存
    })
  }

  /**
   * 停止任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 停止结果
   */
  async stopTask(taskId) {
    const url = API_ENDPOINTS.METEORITE.STOP_TASK.replace('{task_id}', taskId)
    return await api.post(url, {}, {
      cache: false
    })
  }

  /**
   * 高级搜索
   * @param {Object} searchCriteria - 搜索条件
   * @returns {Promise<Object>} 搜索结果
   */
  async advancedSearch(searchCriteria) {
    return await api.post(`${API_ENDPOINTS.METEORITE.SEARCH}advanced/`, searchCriteria, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 获取搜索建议
   * @param {string} query - 查询字符串
   * @returns {Promise<Array>} 搜索建议
   */
  async getSearchSuggestions(query) {
    return await api.get(`${API_ENDPOINTS.METEORITE.SEARCH}suggestions/`, {
      q: query,
      limit: 10
    }, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 获取陨石分类列表
   * @returns {Promise<Array>} 分类列表
   */
  async getClassifications() {
    return await api.get(`${API_ENDPOINTS.METEORITE.SEARCH}classifications/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000 // 30分钟缓存
    })
  }

  /**
   * 获取发现地点列表
   * @returns {Promise<Array>} 地点列表
   */
  async getFallLocations() {
    return await api.get(`${API_ENDPOINTS.METEORITE.SEARCH}locations/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 导出搜索结果
   * @param {Object} searchParams - 搜索参数
   * @param {string} format - 导出格式
   * @returns {Promise<Blob>} 导出文件
   */
  async exportSearchResults(searchParams, format = 'csv') {
    return await api.download(`${API_ENDPOINTS.METEORITE.SEARCH}export/`, null, {
      params: { ...searchParams, format }
    })
  }
}

// 创建单例实例
const meteoriteSearchService = new MeteoriteSearchService()

export default meteoriteSearchService
export { MeteoriteSearchService }