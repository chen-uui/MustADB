/**
 * 统一RAG服务
 * 提供简化的RAG功能接口
 */
import { apiMethods } from '@/utils/apiClient'
import { getApiErrorMessage } from '@/utils/apiError'

class UnifiedRAGService {
  constructor() {
    this.baseURL = '/api/pdf/unified'
  }

  /**
   * 执行搜索 - 使用优化后的混合搜索
   * @param {Object} params - 搜索参数
   * @param {string} params.query - 查询词
   * @param {number} params.limit - 结果数量限制 (默认20)
   * @param {boolean} params.use_hybrid - 使用混合搜索 (默认true)
   * @param {boolean} params.use_rerank - 使用重排序 (默认true)
   * @param {boolean} params.use_aggregation - 使用文档级聚合 (默认true)
   * @returns {Promise<Object>} 搜索结果
   */
  async search(params) {
    try {
      // 添加优化选项
      const optimizedParams = {
        query: params.query,
        limit: params.limit || 20,
        use_hybrid: params.use_hybrid !== false, // 默认true
        use_rerank: params.use_rerank !== false, // 默认true
        use_aggregation: params.use_aggregation !== false // 默认true
      }
      
      // apiMethods.post() 返回response对象，需要访问 .data
      const response = await apiMethods.post(`${this.baseURL}/search/`, optimizedParams, {
        timeout: 60000 // 1分钟超时
      })
      return response.data
    } catch (error) {
      console.error('搜索失败:', error)
      error.message = getApiErrorMessage(error, '搜索失败')
      throw error
    }
  }

  /**
   * 问答功能
   * @param {string} question - 问题
   * @param {Object} options - 选项
   * @param {string} options.strategy - 搜索策略 (auto, standard, multi-pass)
   * @param {number} options.top_k - 引用数量
   * @returns {Promise<Object>} 问答结果
   */
  async askQuestion(question, options = {}) {
    try {
      // apiMethods.post() 返回response对象，需要访问 .data
      const payload = {
        question,
        strategy: options.strategy || 'auto',
        top_k: options.top_k || 5
      }
      
      const response = await apiMethods.post(`${this.baseURL}/question/`, payload, {
        timeout: 120000 // 2分钟超时，问答可能需要更长时间
      })
      return response.data
    } catch (error) {
      console.error('问答失败:', error)
      error.message = getApiErrorMessage(error, '问答失败')
      throw error
    }
  }

  /**
   * 提取陨石数据
   * @param {string} content - 内容
   * @returns {Promise<Object>} 提取结果
   */
  async extractMeteoriteData(content) {
    try {
      // apiMethods.post() 返回response对象，需要访问 .data
      const response = await apiMethods.post(`${this.baseURL}/extract/`, {
        content
      }, {
        timeout: 120000 // 2分钟超时
      })
      return response.data
    } catch (error) {
      console.error('数据提取失败:', error)
      error.message = getApiErrorMessage(error, '数据提取失败')
      throw error
    }
  }

  /**
   * 获取服务状态
   * @returns {Promise<Object>} 服务状态
   */
  async getServiceStatus() {
    try {
      // apiMethods.get() 返回response对象，需要访问 .data
      const response = await apiMethods.get(`${this.baseURL}/status/`, {
        params: {}
      })
      return response.data
    } catch (error) {
      console.error('状态检查失败:', error)
      error.message = getApiErrorMessage(error, '状态检查失败')
      throw error
    }
  }

  /**
   * 搜索陨石相关内容
   * @param {string} query - 查询词
   * @param {number} limit - 结果数量限制
   * @returns {Promise<Object>} 搜索结果
   */
  async searchMeteoriteContent(query, limit = 100) {
    return this.search({
      query,
      strategy: 'meteorite',
      limit
    })
  }

  /**
   * 综合搜索
   * @param {string} query - 查询词
   * @param {number} limit - 结果数量限制
   * @returns {Promise<Object>} 搜索结果
   */
  async comprehensiveSearch(query, limit = 100) {
    return this.search({
      query,
      strategy: 'comprehensive',
      limit
    })
  }
}

export default new UnifiedRAGService()
