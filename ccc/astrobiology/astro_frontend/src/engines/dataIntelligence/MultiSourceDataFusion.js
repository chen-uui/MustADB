/**
 * 多源数据融合模块
 * 负责整合来自不同来源的数据，进行格式转换和一致性检查
 */
class MultiSourceDataFusion {
  constructor() {
    this.dataSources = new Map()
    this.dataTransformers = new Map()
    this.dataValidators = new Map()
    
    // 配置
    this.config = {
      enableRealTimeSync: true,
      enableDataValidation: true,
      enableFormatConversion: true,
      syncInterval: 30000, // 30秒
      maxRetryAttempts: 3,
      retryDelay: 5000,
      enableCaching: true,
      cacheExpiry: 5 * 60 * 1000 // 5分钟
    }
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 数据缓存
    this.dataCache = new Map()
    
    // 同步定时器
    this.syncTimer = null
    
    this.initializeDefaultTransformers()
    this.initializeDefaultValidators()
    this.startDataSync()
  }

  /**
   * 初始化默认数据转换器
   */
  initializeDefaultTransformers() {
    // 陨石数据转换器
    this.dataTransformers.set('meteorite_data', {
      transform: (data) => {
        return {
          id: data.id || data.meteorite_id,
          name: data.name || data.meteorite_name,
          type: data.type || data.meteorite_type,
          classification: data.classification || data.class,
          composition: data.composition || {},
          location: data.location || data.fall_location,
          date: data.date || data.fall_date,
          mass: data.mass || data.weight,
          source: 'meteorite_database'
        }
      }
    })
    
    // 文档数据转换器
    this.dataTransformers.set('document_data', {
      transform: (data) => {
        return {
          id: data.id || data.document_id,
          title: data.title || data.filename,
          content: data.content || data.text,
          metadata: data.metadata || {},
          type: data.type || 'pdf',
          size: data.size || data.file_size,
          uploadDate: data.upload_date || data.created_at,
          source: 'document_management'
        }
      }
    })
    
    // 分析结果转换器
    this.dataTransformers.set('analysis_result', {
      transform: (data) => {
        return {
          id: data.id || data.result_id,
          documentId: data.document_id,
          analysisType: data.analysis_type || data.type,
          results: data.results || data.data,
          confidence: data.confidence || data.score,
          timestamp: data.timestamp || data.created_at,
          source: 'analysis_engine'
        }
      }
    })
  }

  /**
   * 初始化默认数据验证器
   */
  initializeDefaultValidators() {
    // 陨石数据验证器
    this.dataValidators.set('meteorite_data', {
      validate: (data) => {
        const errors = []
        
        if (!data.name) errors.push('缺少陨石名称')
        if (!data.type) errors.push('缺少陨石类型')
        if (data.mass && data.mass < 0) errors.push('质量不能为负数')
        
        return {
          isValid: errors.length === 0,
          errors
        }
      }
    })
    
    // 文档数据验证器
    this.dataValidators.set('document_data', {
      validate: (data) => {
        const errors = []
        
        if (!data.title) errors.push('缺少文档标题')
        if (!data.content) errors.push('缺少文档内容')
        if (data.size && data.size <= 0) errors.push('文档大小无效')
        
        return {
          isValid: errors.length === 0,
          errors
        }
      }
    })
  }

  /**
   * 注册数据源
   * @param {string} sourceId - 数据源ID
   * @param {Object} sourceConfig - 数据源配置
   */
  registerDataSource(sourceId, sourceConfig) {
    this.dataSources.set(sourceId, {
      ...sourceConfig,
      id: sourceId,
      lastSync: null,
      status: 'inactive',
      errorCount: 0
    })
    
    this.emit('data_source_registered', { sourceId, sourceConfig })
  }

  /**
   * 添加数据转换器
   * @param {string} dataType - 数据类型
   * @param {Object} transformer - 转换器
   */
  addDataTransformer(dataType, transformer) {
    this.dataTransformers.set(dataType, transformer)
    this.emit('transformer_added', { dataType, transformer })
  }

  /**
   * 添加数据验证器
   * @param {string} dataType - 数据类型
   * @param {Object} validator - 验证器
   */
  addDataValidator(dataType, validator) {
    this.dataValidators.set(dataType, validator)
    this.emit('validator_added', { dataType, validator })
  }

  /**
   * 融合数据
   * @param {Array} dataSources - 数据源列表
   * @param {Object} options - 融合选项
   * @returns {Promise<Object>} 融合结果
   */
  async fuseData(dataSources, options = {}) {
    const fusionResult = {
      success: true,
      data: {},
      metadata: {
        sources: dataSources,
        timestamp: new Date().toISOString(),
        fusionMethod: options.method || 'merge',
        validationEnabled: this.config.enableDataValidation,
        transformationEnabled: this.config.enableFormatConversion
      },
      errors: [],
      warnings: []
    }

    try {
      // 1. 从各个数据源获取数据
      const sourceData = await this.fetchDataFromSources(dataSources)
      
      // 2. 转换数据格式
      if (this.config.enableFormatConversion) {
        sourceData.forEach((data, index) => {
          const sourceId = dataSources[index]
          const transformedData = this.transformData(data, sourceId)
          sourceData[index] = transformedData
        })
      }
      
      // 3. 验证数据
      if (this.config.enableDataValidation) {
        const validationResults = this.validateData(sourceData, dataSources)
        fusionResult.errors.push(...validationResults.errors)
        fusionResult.warnings.push(...validationResults.warnings)
      }
      
      // 4. 执行数据融合
      const fusedData = this.performDataFusion(sourceData, options)
      fusionResult.data = fusedData
      
      // 5. 缓存结果
      if (this.config.enableCaching) {
        this.cacheFusionResult(dataSources, fusedData)
      }
      
      this.emit('data_fusion_completed', fusionResult)
      
    } catch (error) {
      fusionResult.success = false
      fusionResult.errors.push(error.message)
      this.emit('data_fusion_failed', { error, fusionResult })
    }

    return fusionResult
  }

  /**
   * 从数据源获取数据
   * @param {Array} dataSources - 数据源列表
   * @returns {Promise<Array>} 数据列表
   */
  async fetchDataFromSources(dataSources) {
    const sourceData = []
    
    for (const sourceId of dataSources) {
      try {
        const data = await this.fetchDataFromSource(sourceId)
        sourceData.push(data)
      } catch (error) {
        console.error(`Failed to fetch data from source ${sourceId}:`, error)
        sourceData.push(null)
      }
    }
    
    return sourceData
  }

  /**
   * 从单个数据源获取数据
   * @param {string} sourceId - 数据源ID
   * @returns {Promise<Object>} 数据
   */
  async fetchDataFromSource(sourceId) {
    const source = this.dataSources.get(sourceId)
    if (!source) {
      throw new Error(`数据源${sourceId}不存在`)
    }

    // 检查缓存
    if (this.config.enableCaching) {
      const cachedData = this.getCachedData(sourceId)
      if (cachedData) {
        return cachedData
      }
    }

    // 从数据源获取数据
    const data = await source.fetchData()
    
    // 更新数据源状态
    source.lastSync = new Date().toISOString()
    source.status = 'active'
    source.errorCount = 0
    
    // 缓存数据
    if (this.config.enableCaching) {
      this.cacheData(sourceId, data)
    }
    
    return data
  }

  /**
   * 转换数据格式
   * @param {Object} data - 原始数据
   * @param {string} sourceId - 数据源ID
   * @returns {Object} 转换后的数据
   */
  transformData(data, sourceId) {
    const source = this.dataSources.get(sourceId)
    if (!source || !source.dataType) {
      return data
    }

    const transformer = this.dataTransformers.get(source.dataType)
    if (!transformer) {
      return data
    }

    try {
      return transformer.transform(data)
    } catch (error) {
      console.error(`Data transformation failed for source ${sourceId}:`, error)
      return data
    }
  }

  /**
   * 验证数据
   * @param {Array} dataList - 数据列表
   * @param {Array} dataSources - 数据源列表
   * @returns {Object} 验证结果
   */
  validateData(dataList, dataSources) {
    const validationResult = {
      errors: [],
      warnings: []
    }

    dataList.forEach((data, index) => {
      if (!data) {
        validationResult.errors.push(`数据源${dataSources[index]}返回空数据`)
        return
      }

      const source = this.dataSources.get(dataSources[index])
      if (!source || !source.dataType) {
        return
      }

      const validator = this.dataValidators.get(source.dataType)
      if (!validator) {
        return
      }

      try {
        const result = validator.validate(data)
        if (!result.isValid) {
          validationResult.errors.push(...result.errors.map(error => 
            `${dataSources[index]}: ${error}`
          ))
        }
      } catch (error) {
        validationResult.errors.push(`数据源${dataSources[index]}验证失败: ${error.message}`)
      }
    })

    return validationResult
  }

  /**
   * 执行数据融合
   * @param {Array} sourceData - 源数据列表
   * @param {Object} options - 融合选项
   * @returns {Object} 融合后的数据
   */
  performDataFusion(sourceData, options) {
    const method = options.method || 'merge'
    
    switch (method) {
      case 'merge':
        return this.mergeData(sourceData)
      case 'join':
        return this.joinData(sourceData, options.joinKey)
      case 'aggregate':
        return this.aggregateData(sourceData, options.aggregationRules)
      default:
        return this.mergeData(sourceData)
    }
  }

  /**
   * 合并数据
   * @param {Array} sourceData - 源数据列表
   * @returns {Object} 合并后的数据
   */
  mergeData(sourceData) {
    const mergedData = {}
    
    sourceData.forEach((data, index) => {
      if (data) {
        Object.assign(mergedData, data)
      }
    })
    
    return mergedData
  }

  /**
   * 连接数据
   * @param {Array} sourceData - 源数据列表
   * @param {string} joinKey - 连接键
   * @returns {Object} 连接后的数据
   */
  joinData(sourceData, joinKey) {
    // 实现数据连接逻辑
    return sourceData.reduce((result, data) => {
      if (data && data[joinKey]) {
        result[data[joinKey]] = data
      }
      return result
    }, {})
  }

  /**
   * 聚合数据
   * @param {Array} sourceData - 源数据列表
   * @param {Object} aggregationRules - 聚合规则
   * @returns {Object} 聚合后的数据
   */
  aggregateData(sourceData, aggregationRules) {
    // 实现数据聚合逻辑
    const aggregatedData = {}
    
    if (aggregationRules) {
      Object.keys(aggregationRules).forEach(key => {
        const rule = aggregationRules[key]
        const values = sourceData.map(data => data && data[key]).filter(val => val !== undefined)
        
        if (values.length > 0) {
          switch (rule.type) {
            case 'sum':
              aggregatedData[key] = values.reduce((sum, val) => sum + val, 0)
              break
            case 'average':
              aggregatedData[key] = values.reduce((sum, val) => sum + val, 0) / values.length
              break
            case 'max':
              aggregatedData[key] = Math.max(...values)
              break
            case 'min':
              aggregatedData[key] = Math.min(...values)
              break
            case 'count':
              aggregatedData[key] = values.length
              break
            default:
              aggregatedData[key] = values[0]
          }
        }
      })
    }
    
    return aggregatedData
  }

  /**
   * 缓存数据
   * @param {string} sourceId - 数据源ID
   * @param {Object} data - 数据
   */
  cacheData(sourceId, data) {
    this.dataCache.set(sourceId, {
      data,
      timestamp: Date.now()
    })
  }

  /**
   * 获取缓存数据
   * @param {string} sourceId - 数据源ID
   * @returns {Object|null} 缓存数据
   */
  getCachedData(sourceId) {
    const cached = this.dataCache.get(sourceId)
    if (cached && (Date.now() - cached.timestamp) < this.config.cacheExpiry) {
      return cached.data
    }
    return null
  }

  /**
   * 缓存融合结果
   * @param {Array} dataSources - 数据源列表
   * @param {Object} fusedData - 融合数据
   */
  cacheFusionResult(dataSources, fusedData) {
    const cacheKey = dataSources.sort().join('_')
    this.dataCache.set(cacheKey, {
      data: fusedData,
      timestamp: Date.now()
    })
  }

  /**
   * 开始数据同步
   */
  startDataSync() {
    if (this.config.enableRealTimeSync && !this.syncTimer) {
      this.syncTimer = setInterval(() => {
        this.performDataSync()
      }, this.config.syncInterval)
    }
  }

  /**
   * 停止数据同步
   */
  stopDataSync() {
    if (this.syncTimer) {
      clearInterval(this.syncTimer)
      this.syncTimer = null
    }
  }

  /**
   * 执行数据同步
   */
  async performDataSync() {
    for (const [sourceId, source] of this.dataSources) {
      if (source.autoSync) {
        try {
          await this.fetchDataFromSource(sourceId)
          this.emit('data_sync_completed', { sourceId })
        } catch (error) {
          source.errorCount++
          source.status = 'error'
          this.emit('data_sync_failed', { sourceId, error })
        }
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
    
    if (newConfig.enableRealTimeSync !== undefined) {
      if (newConfig.enableRealTimeSync) {
        this.startDataSync()
      } else {
        this.stopDataSync()
      }
    }
    
    this.emit('config_updated', { config: this.config })
  }

  /**
   * 清理资源
   */
  destroy() {
    this.stopDataSync()
    this.dataSources.clear()
    this.dataTransformers.clear()
    this.dataValidators.clear()
    this.dataCache.clear()
    this.eventListeners.clear()
    this.emit('data_fusion_destroyed')
  }
}

export default MultiSourceDataFusion