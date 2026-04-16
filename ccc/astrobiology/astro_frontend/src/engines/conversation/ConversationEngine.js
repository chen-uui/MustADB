/**
 * 对话引擎核心类
 * 整合自然语言理解、意图识别、实体提取、上下文管理和响应生成
 */
import NLUProcessor from './NLUProcessor.js'
import IntentRecognizer from './IntentRecognizer.js'
import EntityExtractor from './EntityExtractor.js'
import ContextManager from './ContextManager.js'
import ResponseGenerator from './ResponseGenerator.js'

class ConversationEngine {
  constructor() {
    this.nluProcessor = new NLUProcessor()
    this.intentRecognizer = new IntentRecognizer()
    this.entityExtractor = new EntityExtractor()
    this.contextManager = new ContextManager()
    this.responseGenerator = new ResponseGenerator()
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 处理状态
    this.isProcessing = false
    this.processingQueue = []
    
    // 配置
    this.config = {
      maxRetries: 3,
      timeout: 30000, // 30秒超时
      enableContext: true,
      enableSuggestions: true,
      enableActions: true
    }
  }

  /**
   * 处理用户输入
   * @param {string} userInput - 用户输入
   * @param {Object} options - 处理选项
   * @returns {Promise<Object>} 处理结果
   */
  async processInput(userInput, options = {}) {
    if (this.isProcessing) {
      // 如果正在处理，加入队列
      return new Promise((resolve, reject) => {
        this.processingQueue.push({ userInput, options, resolve, reject })
      })
    }
    
    this.isProcessing = true
    
    try {
      const result = await this.processInputInternal(userInput, options)
      this.isProcessing = false
      
      // 处理队列中的下一个请求
      this.processNextInQueue()
      
      return result
    } catch (error) {
      this.isProcessing = false
      this.processNextInQueue()
      throw error
    }
  }

  /**
   * 内部处理逻辑
   * @param {string} userInput - 用户输入
   * @param {Object} options - 处理选项
   * @returns {Promise<Object>} 处理结果
   */
  async processInputInternal(userInput, options = {}) {
    const startTime = Date.now()
    
    try {
      // 1. 自然语言理解
      this.emit('nlu_start', { userInput })
      const nluResult = await this.nluProcessor.process(userInput)
      this.emit('nlu_complete', { nluResult })
      
      // 2. 实体提取
      this.emit('entity_extraction_start', { nluResult })
      const entities = await this.entityExtractor.extract(nluResult)
      this.emit('entity_extraction_complete', { entities })
      
      // 3. 意图识别
      this.emit('intent_recognition_start', { nluResult, entities })
      const intentResult = await this.intentRecognizer.recognize(nluResult)
      this.emit('intent_recognition_complete', { intentResult })
      
      // 4. 更新上下文
      if (this.config.enableContext) {
        this.emit('context_update_start', { intentResult, entities })
        this.contextManager.update(
          intentResult.primaryIntent,
          entities,
          {
            ...intentResult.context,
            ...options.additionalData
          }
        )
        this.emit('context_update_complete')
      }
      
      // 5. 生成响应
      this.emit('response_generation_start', { intentResult, entities })
      const response = await this.responseGenerator.generate(
        intentResult.primaryIntent,
        entities,
        this.contextManager.getContext(),
        {
          ...intentResult.context,
          ...options.additionalData,
          processingTime: Date.now() - startTime
        }
      )
      this.emit('response_generation_complete', { response })
      
      // 6. 构建最终结果
      const result = {
        success: true,
        input: userInput,
        nlu: nluResult,
        entities: entities,
        intent: intentResult,
        context: this.contextManager.getContext(),
        response: response,
        processingTime: Date.now() - startTime,
        timestamp: new Date().toISOString()
      }
      
      this.emit('processing_complete', { result })
      
      return result
      
    } catch (error) {
      this.emit('processing_error', { error, userInput })
      
      // 生成错误响应
      const errorResponse = this.responseGenerator.generateErrorResponse(error, 'unknown')
      
      return {
        success: false,
        input: userInput,
        error: error.message,
        response: errorResponse,
        processingTime: Date.now() - startTime,
        timestamp: new Date().toISOString()
      }
    }
  }

  /**
   * 处理队列中的下一个请求
   */
  processNextInQueue() {
    if (this.processingQueue.length > 0) {
      const { userInput, options, resolve, reject } = this.processingQueue.shift()
      
      this.processInputInternal(userInput, options)
        .then(resolve)
        .catch(reject)
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
   * 获取当前上下文
   * @returns {Object} 当前上下文
   */
  getContext() {
    return this.contextManager.getContext()
  }

  /**
   * 重置上下文
   */
  resetContext() {
    this.contextManager.resetContext()
    this.emit('context_reset')
  }

  /**
   * 设置用户偏好
   * @param {Object} preferences - 用户偏好
   */
  setUserPreferences(preferences) {
    this.contextManager.setUserPreferences(preferences)
    this.emit('preferences_updated', { preferences })
  }

  /**
   * 获取用户偏好
   * @returns {Object} 用户偏好
   */
  getUserPreferences() {
    return this.contextManager.getUserPreferences()
  }

  /**
   * 获取会话摘要
   * @returns {Object} 会话摘要
   */
  getSessionSummary() {
    return this.contextManager.getSessionSummary()
  }

  /**
   * 导出会话状态
   * @returns {Object} 会话状态
   */
  exportSession() {
    return {
      context: this.contextManager.exportContext(),
      config: this.config,
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 导入会话状态
   * @param {Object} sessionData - 会话数据
   */
  importSession(sessionData) {
    if (sessionData.context) {
      this.contextManager.importContext(sessionData.context)
    }
    if (sessionData.config) {
      this.config = { ...this.config, ...sessionData.config }
    }
    this.emit('session_imported', { sessionData })
  }

  /**
   * 更新配置
   * @param {Object} newConfig - 新配置
   */
  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig }
    this.emit('config_updated', { config: this.config })
  }

  /**
   * 获取处理状态
   * @returns {Object} 处理状态
   */
  getProcessingStatus() {
    return {
      isProcessing: this.isProcessing,
      queueLength: this.processingQueue.length,
      context: this.contextManager.getContext(),
      config: this.config
    }
  }

  /**
   * 清理资源
   */
  destroy() {
    this.eventListeners.clear()
    this.processingQueue = []
    this.isProcessing = false
    this.contextManager.resetContext()
    this.emit('engine_destroyed')
  }

  /**
   * 批量处理输入
   * @param {Array} inputs - 输入数组
   * @param {Object} options - 处理选项
   * @returns {Promise<Array>} 处理结果数组
   */
  async processBatch(inputs, options = {}) {
    const results = []
    
    for (const input of inputs) {
      try {
        const result = await this.processInput(input, options)
        results.push(result)
      } catch (error) {
        results.push({
          success: false,
          input,
          error: error.message,
          timestamp: new Date().toISOString()
        })
      }
    }
    
    return results
  }

  /**
   * 获取建议
   * @param {Object} context - 上下文
   * @returns {Array} 建议列表
   */
  getSuggestions(context = null) {
    const currentContext = context || this.contextManager.getContext()
    return this.contextManager.getContextSuggestions()
  }

  /**
   * 验证输入
   * @param {string} input - 输入文本
   * @returns {Object} 验证结果
   */
  validateInput(input) {
    const validation = {
      isValid: true,
      errors: [],
      warnings: []
    }
    
    if (!input || typeof input !== 'string') {
      validation.isValid = false
      validation.errors.push('输入必须是非空字符串')
    }
    
    if (input && input.length > 1000) {
      validation.warnings.push('输入文本过长，可能影响处理效果')
    }
    
    if (input && input.length < 2) {
      validation.warnings.push('输入文本过短，可能无法准确理解意图')
    }
    
    return validation
  }
}

export default ConversationEngine