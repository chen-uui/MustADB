/**
 * 数据智能层核心类
 * 整合多源数据融合和智能分析
 */
import MultiSourceDataFusion from './MultiSourceDataFusion.js'
import IntelligentAnalysis from './IntelligentAnalysis.js'

class DataIntelligenceLayer {
  constructor() {
    this.dataFusion = new MultiSourceDataFusion()
    this.intelligentAnalysis = new IntelligentAnalysis()
    
    // 数据存储
    this.dataStore = new Map()
    this.dataIndex = new Map()
    
    // 配置
    this.config = {
      enableDataFusion: true,
      enableIntelligentAnalysis: true,
      enableRealTimeProcessing: true,
      enableDataIndexing: true,
      enableDataCaching: true,
      maxCacheSize: 1000,
      cacheExpiry: 10 * 60 * 1000, // 10分钟
      enableDataValidation: true,
      enableDataTransformation: true
    }
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 处理队列
    this.processingQueue = []
    this.isProcessing = false
    
    this.initializeEventHandlers()
  }

  /**
   * 初始化事件处理器
   */
  initializeEventHandlers() {
    // 监听数据融合事件
    this.dataFusion.on('data_fusion_completed', (data) => {
      this.handleDataFusionCompleted(data)
    })
    
    this.dataFusion.on('data_fusion_failed', (data) => {
      this.handleDataFusionFailed(data)
    })
    
    // 监听智能分析事件
    this.intelligentAnalysis.on('analysis_completed', (data) => {
      this.handleAnalysisCompleted(data)
    })
    
    this.intelligentAnalysis.on('analysis_failed', (data) => {
      this.handleAnalysisFailed(data)
    })
  }

  /**
   * 处理数据
   * @param {Object} data - 输入数据
   * @param {Object} options - 处理选项
   * @returns {Promise<Object>} 处理结果
   */
  async processData(data, options = {}) {
    const processingId = this.generateProcessingId()
    
    const processingRequest = {
      id: processingId,
      data,
      options,
      status: 'queued',
      startTime: Date.now(),
      steps: []
    }
    
    this.processingQueue.push(processingRequest)
    
    try {
      const result = await this.processDataInternal(processingRequest)
      return result
    } catch (error) {
      processingRequest.status = 'failed'
      processingRequest.error = error.message
      processingRequest.endTime = Date.now()
      this.emit('data_processing_failed', { processingRequest, error })
      throw error
    }
  }

  /**
   * 内部数据处理
   * @param {Object} processingRequest - 处理请求
   * @returns {Promise<Object>} 处理结果
   */
  async processDataInternal(processingRequest) {
    processingRequest.status = 'processing'
    this.isProcessing = true
    
    const result = {
      id: processingRequest.id,
      success: true,
      data: processingRequest.data,
      processedData: null,
      analysis: null,
      insights: null,
      metadata: {
        timestamp: new Date().toISOString(),
        processingTime: 0,
        steps: []
      },
      errors: [],
      warnings: []
    }

    try {
      // 1. 数据验证
      if (this.config.enableDataValidation) {
        const validationResult = await this.validateData(processingRequest.data)
        result.metadata.steps.push('validation')
        
        if (!validationResult.isValid) {
          result.errors.push(...validationResult.errors)
          result.warnings.push(...validationResult.warnings)
        }
      }
      
      // 2. 数据转换
      if (this.config.enableDataTransformation) {
        const transformedData = await this.transformData(processingRequest.data)
        result.processedData = transformedData
        result.metadata.steps.push('transformation')
      } else {
        result.processedData = processingRequest.data
      }
      
      // 3. 数据融合
      if (this.config.enableDataFusion) {
        const fusionResult = await this.performDataFusion(result.processedData, processingRequest.options)
        result.processedData = fusionResult.data
        result.metadata.steps.push('fusion')
        
        if (fusionResult.errors.length > 0) {
          result.errors.push(...fusionResult.errors)
        }
        if (fusionResult.warnings.length > 0) {
          result.warnings.push(...fusionResult.warnings)
        }
      }
      
      // 4. 智能分析
      if (this.config.enableIntelligentAnalysis) {
        const analysisResult = await this.performIntelligentAnalysis(result.processedData, processingRequest.options)
        result.analysis = analysisResult.analyses
        result.insights = analysisResult.insights
        result.metadata.steps.push('analysis')
        
        if (analysisResult.errors.length > 0) {
          result.errors.push(...analysisResult.errors)
        }
        if (analysisResult.warnings.length > 0) {
          result.warnings.push(...analysisResult.warnings)
        }
      }
      
      // 5. 数据索引
      if (this.config.enableDataIndexing) {
        await this.indexData(result.processedData, processingRequest.id)
        result.metadata.steps.push('indexing')
      }
      
      // 6. 数据缓存
      if (this.config.enableDataCaching) {
        await this.cacheData(result.processedData, processingRequest.id)
        result.metadata.steps.push('caching')
      }
      
      // 完成处理
      processingRequest.status = 'completed'
      processingRequest.endTime = Date.now()
      result.metadata.processingTime = processingRequest.endTime - processingRequest.startTime
      
      this.emit('data_processing_completed', { processingRequest, result })
      
      return result
      
    } catch (error) {
      processingRequest.status = 'failed'
      processingRequest.error = error.message
      processingRequest.endTime = Date.now()
      result.success = false
      result.errors.push(error.message)
      
      this.emit('data_processing_failed', { processingRequest, error })
      throw error
    } finally {
      this.isProcessing = false
      this.processNextInQueue()
    }
  }

  /**
   * 处理队列中的下一个请求
   */
  processNextInQueue() {
    if (this.processingQueue.length > 0 && !this.isProcessing) {
      const nextRequest = this.processingQueue.shift()
      this.processDataInternal(nextRequest)
    }
  }

  /**
   * 验证数据
   * @param {Object} data - 数据
   * @returns {Promise<Object>} 验证结果
   */
  async validateData(data) {
    const validation = {
      isValid: true,
      errors: [],
      warnings: []
    }

    // 基本验证
    if (!data || typeof data !== 'object') {
      validation.isValid = false
      validation.errors.push('数据必须是非空对象')
      return validation
    }

    // 检查数据大小
    const dataSize = JSON.stringify(data).length
    if (dataSize > 10 * 1024 * 1024) { // 10MB
      validation.warnings.push('数据大小超过10MB，可能影响处理性能')
    }

    // 检查数据完整性
    if (Array.isArray(data)) {
      if (data.length === 0) {
        validation.warnings.push('数据数组为空')
      }
    }

    return validation
  }

  /**
   * 转换数据
   * @param {Object} data - 原始数据
   * @returns {Promise<Object>} 转换后的数据
   */
  async transformData(data) {
    // 这里应该实现数据转换逻辑
    // 例如：格式标准化、数据类型转换、字段映射等
    return data
  }

  /**
   * 执行数据融合
   * @param {Object} data - 数据
   * @param {Object} options - 选项
   * @returns {Promise<Object>} 融合结果
   */
  async performDataFusion(data, options) {
    const fusionOptions = {
      method: options.fusionMethod || 'merge',
      sources: options.dataSources || ['default'],
      ...options.fusionOptions
    }
    
    return await this.dataFusion.fuseData(fusionOptions.sources, fusionOptions)
  }

  /**
   * 执行智能分析
   * @param {Object} data - 数据
   * @param {Object} options - 选项
   * @returns {Promise<Object>} 分析结果
   */
  async performIntelligentAnalysis(data, options) {
    const analysisOptions = {
      analysisTypes: options.analysisTypes || ['correlation', 'trend', 'anomaly'],
      ...options.analysisOptions
    }
    
    return await this.intelligentAnalysis.performAnalysis(data, analysisOptions.analysisTypes, analysisOptions)
  }

  /**
   * 索引数据
   * @param {Object} data - 数据
   * @param {string} dataId - 数据ID
   */
  async indexData(data, dataId) {
    // 创建数据索引
    const index = {
      id: dataId,
      timestamp: new Date().toISOString(),
      dataType: this.detectDataType(data),
      size: JSON.stringify(data).length,
      keywords: this.extractKeywords(data),
      metadata: this.extractMetadata(data)
    }
    
    this.dataIndex.set(dataId, index)
    
    // 更新关键词索引
    index.keywords.forEach(keyword => {
      if (!this.dataIndex.has(keyword)) {
        this.dataIndex.set(keyword, new Set())
      }
      this.dataIndex.get(keyword).add(dataId)
    })
  }

  /**
   * 缓存数据
   * @param {Object} data - 数据
   * @param {string} dataId - 数据ID
   */
  async cacheData(data, dataId) {
    // 检查缓存大小限制
    if (this.dataStore.size >= this.config.maxCacheSize) {
      this.cleanupOldCache()
    }
    
    this.dataStore.set(dataId, {
      data,
      timestamp: Date.now(),
      accessCount: 0
    })
  }

  /**
   * 清理旧缓存
   */
  cleanupOldCache() {
    const now = Date.now()
    const entries = Array.from(this.dataStore.entries())
    
    // 按访问次数和时间排序，删除最少使用的条目
    entries.sort((a, b) => {
      const aScore = a[1].accessCount + (now - a[1].timestamp) / 1000
      const bScore = b[1].accessCount + (now - b[1].timestamp) / 1000
      return aScore - bScore
    })
    
    // 删除前10%的条目
    const deleteCount = Math.floor(entries.length * 0.1)
    for (let i = 0; i < deleteCount; i++) {
      this.dataStore.delete(entries[i][0])
    }
  }

  /**
   * 检测数据类型
   * @param {Object} data - 数据
   * @returns {string} 数据类型
   */
  detectDataType(data) {
    if (Array.isArray(data)) {
      return 'array'
    }
    if (typeof data === 'object') {
      return 'object'
    }
    return typeof data
  }

  /**
   * 提取关键词
   * @param {Object} data - 数据
   * @returns {Array} 关键词列表
   */
  extractKeywords(data) {
    const keywords = []
    
    const extractFromObject = (obj, prefix = '') => {
      Object.keys(obj).forEach(key => {
        const value = obj[key]
        const fullKey = prefix ? `${prefix}.${key}` : key
        
        keywords.push(fullKey)
        
        if (typeof value === 'string' && value.length > 2) {
          keywords.push(value.toLowerCase())
        } else if (typeof value === 'object' && value !== null) {
          extractFromObject(value, fullKey)
        }
      })
    }
    
    extractFromObject(data)
    return [...new Set(keywords)]
  }

  /**
   * 提取元数据
   * @param {Object} data - 数据
   * @returns {Object} 元数据
   */
  extractMetadata(data) {
    return {
      dataType: this.detectDataType(data),
      size: JSON.stringify(data).length,
      depth: this.calculateObjectDepth(data),
      fieldCount: this.countFields(data),
      hasNestedObjects: this.hasNestedObjects(data)
    }
  }

  /**
   * 计算对象深度
   * @param {Object} obj - 对象
   * @returns {number} 深度
   */
  calculateObjectDepth(obj) {
    if (typeof obj !== 'object' || obj === null) {
      return 0
    }
    
    let maxDepth = 0
    Object.values(obj).forEach(value => {
      const depth = this.calculateObjectDepth(value)
      maxDepth = Math.max(maxDepth, depth)
    })
    
    return maxDepth + 1
  }

  /**
   * 计算字段数量
   * @param {Object} obj - 对象
   * @returns {number} 字段数量
   */
  countFields(obj) {
    if (typeof obj !== 'object' || obj === null) {
      return 0
    }
    
    let count = Object.keys(obj).length
    Object.values(obj).forEach(value => {
      count += this.countFields(value)
    })
    
    return count
  }

  /**
   * 检查是否有嵌套对象
   * @param {Object} obj - 对象
   * @returns {boolean} 是否有嵌套对象
   */
  hasNestedObjects(obj) {
    if (typeof obj !== 'object' || obj === null) {
      return false
    }
    
    return Object.values(obj).some(value => 
      typeof value === 'object' && value !== null
    )
  }

  /**
   * 搜索数据
   * @param {string} query - 搜索查询
   * @param {Object} options - 搜索选项
   * @returns {Array} 搜索结果
   */
  searchData(query, options = {}) {
    const results = []
    const queryLower = query.toLowerCase()
    
    for (const [dataId, index] of this.dataIndex) {
      if (typeof index === 'object' && index.keywords) {
        const matchScore = this.calculateMatchScore(index.keywords, queryLower)
        
        if (matchScore > 0) {
          results.push({
            dataId,
            score: matchScore,
            metadata: index.metadata,
            timestamp: index.timestamp
          })
        }
      }
    }
    
    // 按匹配分数排序
    results.sort((a, b) => b.score - a.score)
    
    // 限制结果数量
    const limit = options.limit || 10
    return results.slice(0, limit)
  }

  /**
   * 计算匹配分数
   * @param {Array} keywords - 关键词列表
   * @param {string} query - 查询字符串
   * @returns {number} 匹配分数
   */
  calculateMatchScore(keywords, query) {
    let score = 0
    
    keywords.forEach(keyword => {
      if (keyword.includes(query)) {
        score += 1
      }
      if (keyword === query) {
        score += 2
      }
    })
    
    return score
  }

  /**
   * 获取数据
   * @param {string} dataId - 数据ID
   * @returns {Object|null} 数据
   */
  getData(dataId) {
    const cached = this.dataStore.get(dataId)
    if (cached) {
      cached.accessCount++
      return cached.data
    }
    return null
  }

  /**
   * 处理数据融合完成
   * @param {Object} data - 融合数据
   */
  handleDataFusionCompleted(data) {
    this.emit('data_fusion_completed', data)
  }

  /**
   * 处理数据融合失败
   * @param {Object} data - 失败数据
   */
  handleDataFusionFailed(data) {
    this.emit('data_fusion_failed', data)
  }

  /**
   * 处理分析完成
   * @param {Object} data - 分析数据
   */
  handleAnalysisCompleted(data) {
    this.emit('analysis_completed', data)
  }

  /**
   * 处理分析失败
   * @param {Object} data - 失败数据
   */
  handleAnalysisFailed(data) {
    this.emit('analysis_failed', data)
  }

  /**
   * 生成处理ID
   * @returns {string} 处理ID
   */
  generateProcessingId() {
    return `processing_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * 获取系统统计
   * @returns {Object} 系统统计
   */
  getSystemStats() {
    return {
      dataStore: {
        size: this.dataStore.size,
        maxSize: this.config.maxCacheSize
      },
      dataIndex: {
        size: this.dataIndex.size
      },
      processingQueue: {
        length: this.processingQueue.length,
        isProcessing: this.isProcessing
      },
      dataFusion: {
        dataSources: this.dataFusion.dataSources.size,
        transformers: this.dataFusion.dataTransformers.size,
        validators: this.dataFusion.dataValidators.size
      },
      intelligentAnalysis: {
        analysisEngines: this.intelligentAnalysis.analysisEngines.size,
        analysisResults: this.intelligentAnalysis.analysisResults.size,
        analysisHistory: this.intelligentAnalysis.analysisHistory.length
      }
    }
  }

  /**
   * 添加事件监听器
   * @param {string} event - 事件名称
   * @param {Function} listener - 监听器函数
   */
  on(event, listener) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, [])
    }
    this.eventListeners.get(event).push(listener)
  }

  /**
   * 移除事件监听器
   * @param {string} event - 事件名称
   * @param {Function} listener - 监听器函数
   */
  off(event, listener) {
    if (this.eventListeners.has(event)) {
      const listeners = this.eventListeners.get(event)
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }

  /**
   * 触发事件
   * @param {string} event - 事件名称
   * @param {Object} data - 事件数据
   */
  emit(event, data) {
    if (this.eventListeners.has(event)) {
      this.eventListeners.get(event).forEach(listener => {
        try {
          listener(data)
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error)
        }
      })
    }
  }

  /**
   * 更新配置
   * @param {Object} newConfig - 新配置
   */
  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig }
    this.dataFusion.updateConfig(newConfig)
    this.intelligentAnalysis.updateConfig(newConfig)
    this.emit('config_updated', { config: this.config })
  }

  /**
   * 清理资源
   */
  destroy() {
    this.dataFusion.destroy()
    this.intelligentAnalysis.destroy()
    this.dataStore.clear()
    this.dataIndex.clear()
    this.processingQueue = []
    this.eventListeners.clear()
    this.emit('data_intelligence_destroyed')
  }
}

export default DataIntelligenceLayer