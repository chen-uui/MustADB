/**
 * 上下文管理器
 * 负责管理对话的上下文信息，支持多轮对话
 */
class ContextManager {
  constructor() {
    this.context = {
      currentIntent: null,
      currentEntities: {},
      conversationHistory: [],
      userPreferences: {},
      sessionData: {},
      workflowState: null,
      lastAction: null,
      pendingActions: []
    }
    
    this.maxHistoryLength = 50 // 最大历史记录数
    this.contextTimeout = 30 * 60 * 1000 // 上下文超时时间（30分钟）
    this.lastUpdateTime = Date.now()
  }

  /**
   * 更新上下文
   * @param {string} intent - 当前意图
   * @param {Object} entities - 实体信息
   * @param {Object} additionalData - 额外数据
   */
  update(intent, entities, additionalData = {}) {
    this.lastUpdateTime = Date.now()
    
    // 更新当前意图和实体
    this.context.currentIntent = intent
    this.context.currentEntities = entities
    
    // 添加对话历史
    this.addToHistory({
      intent,
      entities,
      timestamp: new Date().toISOString(),
      ...additionalData
    })
    
    // 更新会话数据
    this.updateSessionData(intent, entities, additionalData)
    
    // 更新工作流状态
    this.updateWorkflowState(intent, entities)
    
    // 更新最后操作
    this.context.lastAction = {
      intent,
      entities,
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 获取当前上下文
   * @returns {Object} 当前上下文
   */
  getContext() {
    // 检查上下文是否超时
    if (this.isContextExpired()) {
      this.resetContext()
    }
    
    return {
      ...this.context,
      isExpired: this.isContextExpired(),
      lastUpdateTime: this.lastUpdateTime
    }
  }

  /**
   * 检查上下文是否过期
   * @returns {boolean} 是否过期
   */
  isContextExpired() {
    return Date.now() - this.lastUpdateTime > this.contextTimeout
  }

  /**
   * 重置上下文
   */
  resetContext() {
    this.context = {
      currentIntent: null,
      currentEntities: {},
      conversationHistory: [],
      userPreferences: this.context.userPreferences, // 保留用户偏好
      sessionData: {},
      workflowState: null,
      lastAction: null,
      pendingActions: []
    }
    this.lastUpdateTime = Date.now()
  }

  /**
   * 添加到对话历史
   * @param {Object} entry - 历史条目
   */
  addToHistory(entry) {
    this.context.conversationHistory.push(entry)
    
    // 限制历史记录长度
    if (this.context.conversationHistory.length > this.maxHistoryLength) {
      this.context.conversationHistory = this.context.conversationHistory.slice(-this.maxHistoryLength)
    }
  }

  /**
   * 更新会话数据
   * @param {string} intent - 意图
   * @param {Object} entities - 实体
   * @param {Object} additionalData - 额外数据
   */
  updateSessionData(intent, entities, additionalData) {
    // 根据意图更新会话数据
    switch (intent) {
      case 'search_meteorite':
        if (entities.meteoriteNames && entities.meteoriteNames.length > 0) {
          this.context.sessionData.lastSearchedMeteorite = entities.meteoriteNames[0]
        }
        break
        
      case 'upload_document':
        if (entities.fileNames && entities.fileNames.length > 0) {
          this.context.sessionData.lastUploadedFile = entities.fileNames[0]
        }
        break
        
      case 'analyze_document':
        this.context.sessionData.analysisRequested = true
        if (entities.fileNames && entities.fileNames.length > 0) {
          this.context.sessionData.targetDocument = entities.fileNames[0]
        }
        break
        
      case 'extract_data':
        this.context.sessionData.extractionRequested = true
        if (entities.minerals && entities.minerals.length > 0) {
          this.context.sessionData.targetMinerals = entities.minerals
        }
        if (entities.organicCompounds && entities.organicCompounds.length > 0) {
          this.context.sessionData.targetOrganicCompounds = entities.organicCompounds
        }
        break
        
      case 'intelligent_qa':
        this.context.sessionData.qaRequested = true
        break
        
      case 'generate_report':
        this.context.sessionData.reportRequested = true
        break
    }
    
    // 合并额外数据
    Object.assign(this.context.sessionData, additionalData)
  }

  /**
   * 更新工作流状态
   * @param {string} intent - 意图
   * @param {Object} entities - 实体
   */
  updateWorkflowState(intent, entities) {
    // 根据意图确定工作流状态
    switch (intent) {
      case 'meteorite_analysis':
        this.context.workflowState = {
          type: 'meteorite_analysis',
          status: 'started',
          steps: ['search_meteorite', 'analyze_document', 'extract_data', 'generate_report'],
          currentStep: 'search_meteorite',
          progress: 0
        }
        break
        
      case 'comprehensive_analysis':
        this.context.workflowState = {
          type: 'comprehensive_analysis',
          status: 'started',
          steps: ['upload_document', 'analyze_document', 'extract_data', 'generate_report'],
          currentStep: 'upload_document',
          progress: 0
        }
        break
        
      case 'upload_document':
        if (this.context.workflowState && this.context.workflowState.currentStep === 'upload_document') {
          this.context.workflowState.currentStep = 'analyze_document'
          this.context.workflowState.progress = 25
        }
        break
        
      case 'analyze_document':
        if (this.context.workflowState && this.context.workflowState.currentStep === 'analyze_document') {
          this.context.workflowState.currentStep = 'extract_data'
          this.context.workflowState.progress = 50
        }
        break
        
      case 'extract_data':
        if (this.context.workflowState && this.context.workflowState.currentStep === 'extract_data') {
          this.context.workflowState.currentStep = 'generate_report'
          this.context.workflowState.progress = 75
        }
        break
        
      case 'generate_report':
        if (this.context.workflowState && this.context.workflowState.currentStep === 'generate_report') {
          this.context.workflowState.status = 'completed'
          this.context.workflowState.progress = 100
        }
        break
    }
  }

  /**
   * 获取相关历史
   * @param {string} intent - 意图
   * @param {number} limit - 限制数量
   * @returns {Array} 相关历史记录
   */
  getRelevantHistory(intent, limit = 5) {
    return this.context.conversationHistory
      .filter(entry => entry.intent === intent)
      .slice(-limit)
  }

  /**
   * 获取会话摘要
   * @returns {Object} 会话摘要
   */
  getSessionSummary() {
    const summary = {
      totalInteractions: this.context.conversationHistory.length,
      intents: {},
      entities: {},
      workflowStatus: this.context.workflowState,
      lastAction: this.context.lastAction,
      sessionDuration: Date.now() - this.lastUpdateTime
    }
    
    // 统计意图
    this.context.conversationHistory.forEach(entry => {
      summary.intents[entry.intent] = (summary.intents[entry.intent] || 0) + 1
    })
    
    // 统计实体
    this.context.conversationHistory.forEach(entry => {
      if (entry.entities) {
        Object.keys(entry.entities).forEach(entityType => {
          if (entry.entities[entityType] && entry.entities[entityType].length > 0) {
            summary.entities[entityType] = summary.entities[entityType] || []
            summary.entities[entityType].push(...entry.entities[entityType])
          }
        })
      }
    })
    
    // 去重实体
    Object.keys(summary.entities).forEach(entityType => {
      summary.entities[entityType] = [...new Set(summary.entities[entityType])]
    })
    
    return summary
  }

  /**
   * 设置用户偏好
   * @param {Object} preferences - 用户偏好
   */
  setUserPreferences(preferences) {
    this.context.userPreferences = {
      ...this.context.userPreferences,
      ...preferences
    }
  }

  /**
   * 获取用户偏好
   * @returns {Object} 用户偏好
   */
  getUserPreferences() {
    return this.context.userPreferences
  }

  /**
   * 添加待处理操作
   * @param {Object} action - 操作信息
   */
  addPendingAction(action) {
    this.context.pendingActions.push({
      ...action,
      timestamp: new Date().toISOString()
    })
  }

  /**
   * 获取待处理操作
   * @returns {Array} 待处理操作列表
   */
  getPendingActions() {
    return this.context.pendingActions
  }

  /**
   * 清除待处理操作
   * @param {string} actionId - 操作ID
   */
  clearPendingAction(actionId) {
    this.context.pendingActions = this.context.pendingActions.filter(
      action => action.id !== actionId
    )
  }

  /**
   * 检查是否有相关上下文
   * @param {string} intent - 意图
   * @returns {boolean} 是否有相关上下文
   */
  hasRelevantContext(intent) {
    const relevantHistory = this.getRelevantHistory(intent, 1)
    return relevantHistory.length > 0
  }

  /**
   * 获取上下文建议
   * @returns {Array} 建议列表
   */
  getContextSuggestions() {
    const suggestions = []
    
    // 基于工作流状态提供建议
    if (this.context.workflowState) {
      const { currentStep, progress } = this.context.workflowState
      
      switch (currentStep) {
        case 'upload_document':
          suggestions.push('请上传要分析的文档')
          break
        case 'analyze_document':
          suggestions.push('文档正在分析中，请稍候')
          break
        case 'extract_data':
          suggestions.push('正在提取数据，您可以询问相关问题')
          break
        case 'generate_report':
          suggestions.push('正在生成报告，即将完成')
          break
      }
    }
    
    // 基于会话历史提供建议
    if (this.context.sessionData.lastSearchedMeteorite) {
      suggestions.push(`您刚才搜索了${this.context.sessionData.lastSearchedMeteorite}陨石`)
    }
    
    if (this.context.sessionData.lastUploadedFile) {
      suggestions.push(`您刚才上传了${this.context.sessionData.lastUploadedFile}文件`)
    }
    
    return suggestions
  }

  /**
   * 导出上下文
   * @returns {Object} 上下文数据
   */
  exportContext() {
    return {
      ...this.context,
      lastUpdateTime: this.lastUpdateTime,
      exportTime: new Date().toISOString()
    }
  }

  /**
   * 导入上下文
   * @param {Object} contextData - 上下文数据
   */
  importContext(contextData) {
    this.context = contextData.context || this.context
    this.lastUpdateTime = contextData.lastUpdateTime || Date.now()
  }
}

export default ContextManager