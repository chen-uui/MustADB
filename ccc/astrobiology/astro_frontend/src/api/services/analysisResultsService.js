/**
 * 分析结果API服务
 * 完全重构版本 - 直接调用后端API，不依赖旧组件
 */

import { api } from '../client.js'
import { API_ENDPOINTS, EXPORT_FORMATS } from '../interfaces.js'

class AnalysisResultsService {
  /**
   * 获取分析结果列表
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   * @param {string} params.status - 结果状态
   * @param {string} params.type - 结果类型
   * @param {string} params.date_from - 开始日期
   * @param {string} params.date_to - 结束日期
   * @returns {Promise<Object>} 结果列表
   */
  async getAnalysisResults(params = {}) {
    return await api.get(API_ENDPOINTS.ANALYSIS.RESULTS, params, {
      cache: true,
      cacheTTL: 2 * 60 * 1000 // 2分钟缓存
    })
  }

  /**
   * 获取分析结果详情
   * @param {number} id - 结果ID
   * @returns {Promise<Object>} 结果详情
   */
  async getAnalysisResultDetail(id) {
    const url = API_ENDPOINTS.ANALYSIS.RESULT_DETAIL.replace('{id}', id)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 导出分析结果
   * @param {number} id - 结果ID
   * @param {string} format - 导出格式
   * @param {string} filename - 文件名
   * @returns {Promise<Blob>} 导出文件
   */
  async exportAnalysisResult(id, format = EXPORT_FORMATS.JSON, filename = null) {
    const url = API_ENDPOINTS.ANALYSIS.EXPORT.replace('{id}', id)
    return await api.download(url, filename, {
      params: { format }
    })
  }

  /**
   * 生成分析报告
   * @param {number} id - 结果ID
   * @param {Object} reportOptions - 报告选项
   * @param {string} reportOptions.template - 报告模板
   * @param {string} reportOptions.format - 报告格式
   * @param {Object} reportOptions.customization - 自定义选项
   * @returns {Promise<Object>} 报告生成结果
   */
  async generateAnalysisReport(id, reportOptions = {}) {
    const url = API_ENDPOINTS.ANALYSIS.REPORT.replace('{id}', id)
    return await api.post(url, reportOptions, {
      cache: false
    })
  }

  /**
   * 获取分析统计
   * @returns {Promise<Object>} 分析统计
   */
  async getAnalysisStatistics() {
    return await api.get(API_ENDPOINTS.ANALYSIS.STATISTICS, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 获取数据可视化
   * @param {number} id - 结果ID
   * @param {Object} visualizationOptions - 可视化选项
   * @param {string} visualizationOptions.chart_type - 图表类型
   * @param {Object} visualizationOptions.config - 图表配置
   * @returns {Promise<Object>} 可视化数据
   */
  async getDataVisualization(id, visualizationOptions = {}) {
    const url = API_ENDPOINTS.ANALYSIS.VISUALIZATION.replace('{id}', id)
    return await api.post(url, visualizationOptions, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 搜索分析结果
   * @param {Object} searchParams - 搜索参数
   * @param {string} searchParams.query - 搜索关键词
   * @param {string} searchParams.type - 结果类型
   * @param {string} searchParams.status - 结果状态
   * @returns {Promise<Object>} 搜索结果
   */
  async searchAnalysisResults(searchParams) {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.RESULTS}search/`, searchParams, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 删除分析结果
   * @param {number} id - 结果ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteAnalysisResult(id) {
    const url = API_ENDPOINTS.ANALYSIS.RESULT_DETAIL.replace('{id}', id)
    return await api.delete(url, {
      cache: false
    })
  }

  /**
   * 批量删除分析结果
   * @param {Array<number>} ids - 结果ID数组
   * @returns {Promise<Array>} 删除结果数组
   */
  async deleteAnalysisResults(ids) {
    const deletePromises = ids.map(async (id) => {
      try {
        const result = await this.deleteAnalysisResult(id)
        return { success: true, id, result }
      } catch (error) {
        return { success: false, id, error: error.message }
      }
    })

    return await Promise.all(deletePromises)
  }

  /**
   * 获取结果类型列表
   * @returns {Promise<Array>} 结果类型列表
   */
  async getResultTypes() {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.RESULTS}types/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000 // 30分钟缓存
    })
  }

  /**
   * 获取结果状态列表
   * @returns {Promise<Array>} 结果状态列表
   */
  async getResultStatuses() {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.RESULTS}statuses/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 获取报告模板列表
   * @returns {Promise<Array>} 报告模板列表
   */
  async getReportTemplates() {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.REPORT}templates/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 获取报告模板详情
   * @param {string} templateId - 模板ID
   * @returns {Promise<Object>} 模板详情
   */
  async getReportTemplate(templateId) {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.REPORT}templates/${templateId}/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 创建自定义报告模板
   * @param {Object} templateData - 模板数据
   * @returns {Promise<Object>} 创建结果
   */
  async createReportTemplate(templateData) {
    return await api.post(`${API_ENDPOINTS.ANALYSIS.REPORT}templates/`, templateData, {
      cache: false
    })
  }

  /**
   * 更新报告模板
   * @param {string} templateId - 模板ID
   * @param {Object} templateData - 模板数据
   * @returns {Promise<Object>} 更新结果
   */
  async updateReportTemplate(templateId, templateData) {
    return await api.patch(`${API_ENDPOINTS.ANALYSIS.REPORT}templates/${templateId}/`, templateData, {
      cache: false
    })
  }

  /**
   * 删除报告模板
   * @param {string} templateId - 模板ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteReportTemplate(templateId) {
    return await api.delete(`${API_ENDPOINTS.ANALYSIS.REPORT}templates/${templateId}/`, {
      cache: false
    })
  }

  /**
   * 获取可视化图表类型
   * @returns {Promise<Array>} 图表类型列表
   */
  async getChartTypes() {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.VISUALIZATION}chart-types/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 获取可视化配置
   * @param {string} chartType - 图表类型
   * @returns {Promise<Object>} 可视化配置
   */
  async getVisualizationConfig(chartType) {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.VISUALIZATION}config/${chartType}/`, {}, {
      cache: true,
      cacheTTL: 30 * 60 * 1000
    })
  }

  /**
   * 比较分析结果
   * @param {Array<number>} resultIds - 结果ID数组
   * @param {Object} comparisonOptions - 比较选项
   * @returns {Promise<Object>} 比较结果
   */
  async compareAnalysisResults(resultIds, comparisonOptions = {}) {
    return await api.post(`${API_ENDPOINTS.ANALYSIS.RESULTS}compare/`, {
      result_ids: resultIds,
      ...comparisonOptions
    }, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 获取趋势分析
   * @param {Object} trendParams - 趋势参数
   * @param {string} trendParams.metric - 指标
   * @param {string} trendParams.period - 时间周期
   * @param {string} trendParams.date_from - 开始日期
   * @param {string} trendParams.date_to - 结束日期
   * @returns {Promise<Object>} 趋势分析结果
   */
  async getTrendAnalysis(trendParams) {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.RESULTS}trend/`, trendParams, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 获取相关性分析
   * @param {number} id - 结果ID
   * @param {Object} correlationOptions - 相关性选项
   * @returns {Promise<Object>} 相关性分析结果
   */
  async getCorrelationAnalysis(id, correlationOptions = {}) {
    return await api.post(`${API_ENDPOINTS.ANALYSIS.RESULTS}${id}/correlation/`, correlationOptions, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 获取异常检测结果
   * @param {number} id - 结果ID
   * @param {Object} anomalyOptions - 异常检测选项
   * @returns {Promise<Object>} 异常检测结果
   */
  async getAnomalyDetection(id, anomalyOptions = {}) {
    return await api.post(`${API_ENDPOINTS.ANALYSIS.RESULTS}${id}/anomaly/`, anomalyOptions, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 获取预测分析
   * @param {number} id - 结果ID
   * @param {Object} predictionOptions - 预测选项
   * @returns {Promise<Object>} 预测分析结果
   */
  async getPredictionAnalysis(id, predictionOptions = {}) {
    return await api.post(`${API_ENDPOINTS.ANALYSIS.RESULTS}${id}/prediction/`, predictionOptions, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 导出分析历史
   * @param {Object} params - 导出参数
   * @param {string} params.format - 导出格式
   * @param {string} params.date_from - 开始日期
   * @param {string} params.date_to - 结束日期
   * @returns {Promise<Blob>} 导出文件
   */
  async exportAnalysisHistory(params) {
    return await api.download(`${API_ENDPOINTS.ANALYSIS.RESULTS}export-history/`, null, {
      params
    })
  }

  /**
   * 获取分析配置
   * @returns {Promise<Object>} 分析配置
   */
  async getAnalysisConfig() {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.RESULTS}config/`, {}, {
      cache: true,
      cacheTTL: 10 * 60 * 1000
    })
  }

  /**
   * 更新分析配置
   * @param {Object} config - 配置数据
   * @returns {Promise<Object>} 更新结果
   */
  async updateAnalysisConfig(config) {
    return await api.patch(`${API_ENDPOINTS.ANALYSIS.RESULTS}config/`, config, {
      cache: false
    })
  }

  /**
   * 获取分析性能指标
   * @returns {Promise<Object>} 性能指标
   */
  async getAnalysisMetrics() {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.RESULTS}metrics/`, {}, {
      cache: true,
      cacheTTL: 1 * 60 * 1000 // 1分钟缓存
    })
  }

  /**
   * 获取分析历史
   * @param {Object} params - 查询参数
   * @returns {Promise<Object>} 分析历史
   */
  async getAnalysisHistory(params = {}) {
    return await api.get(`${API_ENDPOINTS.ANALYSIS.RESULTS}history/`, params, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 重新分析结果
   * @param {number} id - 结果ID
   * @param {Object} options - 重新分析选项
   * @returns {Promise<Object>} 重新分析结果
   */
  async reanalyzeResult(id, options = {}) {
    return await api.post(`${API_ENDPOINTS.ANALYSIS.RESULTS}${id}/reanalyze/`, options, {
      cache: false
    })
  }

  /**
   * 分享分析结果
   * @param {number} id - 结果ID
   * @param {Object} shareOptions - 分享选项
   * @returns {Promise<Object>} 分享结果
   */
  async shareAnalysisResult(id, shareOptions = {}) {
    return await api.post(`${API_ENDPOINTS.ANALYSIS.RESULTS}${id}/share/`, shareOptions, {
      cache: false
    })
  }

  /**
   * 获取分享链接
   * @param {number} id - 结果ID
   * @param {Object} linkOptions - 链接选项
   * @returns {Promise<Object>} 分享链接
   */
  async getShareLink(id, linkOptions = {}) {
    return await api.post(`${API_ENDPOINTS.ANALYSIS.RESULTS}${id}/share-link/`, linkOptions, {
      cache: false
    })
  }
}

// 创建单例实例
const analysisResultsService = new AnalysisResultsService()

export default analysisResultsService
export { AnalysisResultsService }