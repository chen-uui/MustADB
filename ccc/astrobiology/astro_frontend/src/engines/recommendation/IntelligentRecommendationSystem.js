/**
 * 智能推荐系统核心类
 * 整合用户行为分析、内容推荐、工作流推荐和个性化引擎
 */
import UserBehaviorAnalyzer from './UserBehaviorAnalyzer.js'
import ContentRecommender from './ContentRecommender.js'

class IntelligentRecommendationSystem {
  constructor() {
    this.userBehaviorAnalyzer = new UserBehaviorAnalyzer()
    this.contentRecommender = new ContentRecommender()
    
    // 工作流推荐器
    this.workflowRecommender = new WorkflowRecommender()
    
    // 个性化引擎
    this.personalizationEngine = new PersonalizationEngine()
    
    // 学习系统
    this.learningSystem = new LearningSystem()
    
    // 配置
    this.config = {
      enableBehaviorAnalysis: true,
      enableContentRecommendation: true,
      enableWorkflowRecommendation: true,
      enablePersonalization: true,
      enableLearning: true,
      maxRecommendations: 10,
      recommendationTimeout: 5000,
      enableRealTimeRecommendation: true,
      enableOfflineRecommendation: true
    }
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 推荐历史
    this.recommendationHistory = new Map()
    
    this.initializeEventHandlers()
  }

  /**
   * 初始化事件处理器
   */
  initializeEventHandlers() {
    // 监听用户行为分析事件
    this.userBehaviorAnalyzer.on('behavior_recorded', (data) => {
      this.handleBehaviorRecorded(data)
    })
    
    this.userBehaviorAnalyzer.on('pattern_detected', (data) => {
      this.handlePatternDetected(data)
    })
    
    // 监听内容推荐事件
    this.contentRecommender.on('interaction_recorded', (data) => {
      this.handleInteractionRecorded(data)
    })
    
    this.contentRecommender.on('recommendations_generated', (data) => {
      this.handleRecommendationsGenerated(data)
    })
  }

  /**
   * 获取推荐
   * @param {Object} context - 上下文
   * @returns {Promise<Object>} 推荐结果
   */
  async getRecommendations(context) {
    const { userId, currentState, currentTask, userPreferences } = context
    
    try {
      // 1. 分析用户行为
      const behaviorPattern = await this.userBehaviorAnalyzer.getUserBehaviorPattern(userId)
      
      // 2. 内容推荐
      const contentRecommendations = await this.contentRecommender.generateRecommendations(
        userId, 
        { currentState, currentTask }
      )
      
      // 3. 工作流推荐
      const workflowRecommendations = await this.workflowRecommender.recommend(
        behaviorPattern, 
        currentTask
      )
      
      // 4. 个性化调整
      const personalizedRecommendations = await this.personalizationEngine.personalize(
        contentRecommendations,
        workflowRecommendations,
        userPreferences
      )
      
      // 5. 记录用于学习
      this.learningSystem.record(context, personalizedRecommendations)
      
      // 6. 构建最终推荐结果
      const recommendations = {
        content: personalizedRecommendations.content || [],
        workflows: personalizedRecommendations.workflows || [],
        actions: personalizedRecommendations.actions || [],
        suggestions: personalizedRecommendations.suggestions || [],
        metadata: {
          userId,
          timestamp: new Date().toISOString(),
          behaviorPattern,
          personalizationApplied: true,
          learningEnabled: this.config.enableLearning
        }
      }
      
      // 7. 记录推荐历史
      this.recordRecommendationHistory(userId, recommendations)
      
      this.emit('recommendations_generated', { userId, recommendations })
      
      return recommendations
      
    } catch (error) {
      this.emit('recommendation_error', { userId, error })
      throw error
    }
  }

  /**
   * 处理行为记录
   * @param {Object} data - 行为数据
   */
  handleBehaviorRecorded(data) {
    const { userId, behavior } = data
    
    // 记录到内容推荐器
    if (behavior.type === 'content_interaction') {
      this.contentRecommender.recordInteraction(
        userId,
        behavior.contentId,
        behavior.interactionType,
        behavior.metadata
      )
    }
    
    // 记录到学习系统
    if (this.config.enableLearning) {
      this.learningSystem.recordBehavior(userId, behavior)
    }
  }

  /**
   * 处理模式检测
   * @param {Object} data - 模式数据
   */
  handlePatternDetected(data) {
    const { userId, pattern } = data
    
    // 更新个性化引擎
    if (this.config.enablePersonalization) {
      this.personalizationEngine.updateUserPattern(userId, pattern)
    }
    
    // 触发实时推荐
    if (this.config.enableRealTimeRecommendation) {
      this.triggerRealTimeRecommendation(userId, pattern)
    }
  }

  /**
   * 处理交互记录
   * @param {Object} data - 交互数据
   */
  handleInteractionRecorded(data) {
    const { userId, contentId, type, metadata } = data
    
    // 记录到用户行为分析器
    this.userBehaviorAnalyzer.recordBehavior(userId, {
      type: 'content_interaction',
      contentId,
      interactionType: type,
      metadata,
      timestamp: new Date().toISOString()
    })
  }

  /**
   * 处理推荐生成
   * @param {Object} data - 推荐数据
   */
  handleRecommendationsGenerated(data) {
    const { userId, recommendations } = data
    
    // 记录推荐历史
    this.recordRecommendationHistory(userId, recommendations)
  }

  /**
   * 触发实时推荐
   * @param {string} userId - 用户ID
   * @param {Object} pattern - 行为模式
   */
  async triggerRealTimeRecommendation(userId, pattern) {
    try {
      const context = {
        userId,
        currentState: 'real_time',
        currentTask: null,
        userPreferences: this.personalizationEngine.getUserPreferences(userId),
        pattern
      }
      
      const recommendations = await this.getRecommendations(context)
      
      this.emit('real_time_recommendation', { userId, recommendations })
      
    } catch (error) {
      console.error('Real-time recommendation failed:', error)
    }
  }

  /**
   * 记录推荐历史
   * @param {string} userId - 用户ID
   * @param {Object} recommendations - 推荐结果
   */
  recordRecommendationHistory(userId, recommendations) {
    if (!this.recommendationHistory.has(userId)) {
      this.recommendationHistory.set(userId, [])
    }
    
    const history = this.recommendationHistory.get(userId)
    history.push({
      ...recommendations,
      timestamp: new Date().toISOString()
    })
    
    // 限制历史长度
    if (history.length > 100) {
      history.splice(0, history.length - 100)
    }
  }

  /**
   * 获取用户推荐历史
   * @param {string} userId - 用户ID
   * @returns {Array} 推荐历史
   */
  getUserRecommendationHistory(userId) {
    return this.recommendationHistory.get(userId) || []
  }

  /**
   * 获取用户画像
   * @param {string} userId - 用户ID
   * @returns {Object} 用户画像
   */
  getUserProfile(userId) {
    return {
      behaviorPattern: this.userBehaviorAnalyzer.getUserBehaviorPattern(userId),
      preferences: this.personalizationEngine.getUserPreferences(userId),
      contentProfile: this.contentRecommender.getUserProfile(userId),
      statistics: this.userBehaviorAnalyzer.getStatistics()
    }
  }

  /**
   * 更新用户偏好
   * @param {string} userId - 用户ID
   * @param {Object} preferences - 偏好设置
   */
  updateUserPreferences(userId, preferences) {
    this.personalizationEngine.setUserPreferences(userId, preferences)
    this.emit('user_preferences_updated', { userId, preferences })
  }

  /**
   * 获取系统统计
   * @returns {Object} 系统统计
   */
  getSystemStats() {
    return {
      behaviorAnalyzer: this.userBehaviorAnalyzer.getStatistics(),
      contentRecommender: {
        totalContent: this.contentRecommender.contentDatabase.size,
        totalUsers: this.contentRecommender.userProfiles.size
      },
      recommendationHistory: this.recommendationHistory.size,
      learningSystem: this.learningSystem.getStats()
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
    
    // 更新子组件配置
    this.userBehaviorAnalyzer.updateConfig(newConfig)
    this.contentRecommender.updateConfig(newConfig)
    
    this.emit('config_updated', { config: this.config })
  }

  /**
   * 清理资源
   */
  destroy() {
    this.userBehaviorAnalyzer.destroy()
    this.contentRecommender.destroy()
    this.workflowRecommender.destroy()
    this.personalizationEngine.destroy()
    this.learningSystem.destroy()
    
    this.recommendationHistory.clear()
    this.eventListeners.clear()
    
    this.emit('recommendation_system_destroyed')
  }
}

/**
 * 工作流推荐器
 */
class WorkflowRecommender {
  constructor() {
    this.workflowTemplates = new Map()
    this.userWorkflowHistory = new Map()
  }

  async recommend(behaviorPattern, currentTask) {
    // 基于行为模式推荐工作流
    const recommendations = []
    
    // 分析用户常用工作流
    const commonWorkflows = this.analyzeCommonWorkflows(behaviorPattern)
    
    // 基于当前任务推荐
    const taskBasedWorkflows = this.recommendByTask(currentTask)
    
    // 基于时间模式推荐
    const timeBasedWorkflows = this.recommendByTimePattern(behaviorPattern)
    
    recommendations.push(...commonWorkflows, ...taskBasedWorkflows, ...timeBasedWorkflows)
    
    return this.deduplicateAndRank(recommendations)
  }

  analyzeCommonWorkflows(behaviorPattern) {
    // 分析用户常用工作流模式
    return []
  }

  recommendByTask(currentTask) {
    // 基于当前任务推荐工作流
    return []
  }

  recommendByTimePattern(behaviorPattern) {
    // 基于时间模式推荐工作流
    return []
  }

  deduplicateAndRank(recommendations) {
    // 去重和排序
    return recommendations
  }

  destroy() {
    this.workflowTemplates.clear()
    this.userWorkflowHistory.clear()
  }
}

/**
 * 个性化引擎
 */
class PersonalizationEngine {
  constructor() {
    this.userPreferences = new Map()
    this.userPatterns = new Map()
  }

  async personalize(contentRecommendations, workflowRecommendations, userPreferences) {
    // 个性化调整推荐结果
    return {
      content: contentRecommendations,
      workflows: workflowRecommendations,
      actions: [],
      suggestions: []
    }
  }

  updateUserPattern(userId, pattern) {
    this.userPatterns.set(userId, pattern)
  }

  getUserPreferences(userId) {
    return this.userPreferences.get(userId) || new Map()
  }

  setUserPreferences(userId, preferences) {
    this.userPreferences.set(userId, preferences)
  }

  destroy() {
    this.userPreferences.clear()
    this.userPatterns.clear()
  }
}

/**
 * 学习系统
 */
class LearningSystem {
  constructor() {
    this.learningData = new Map()
    this.models = new Map()
  }

  record(context, recommendations) {
    // 记录学习数据
    const userId = context.userId
    if (!this.learningData.has(userId)) {
      this.learningData.set(userId, [])
    }
    
    this.learningData.get(userId).push({
      context,
      recommendations,
      timestamp: new Date().toISOString()
    })
  }

  recordBehavior(userId, behavior) {
    // 记录行为数据用于学习
  }

  getStats() {
    return {
      totalUsers: this.learningData.size,
      totalRecords: Array.from(this.learningData.values()).reduce((sum, records) => sum + records.length, 0)
    }
  }

  destroy() {
    this.learningData.clear()
    this.models.clear()
  }
}

export default IntelligentRecommendationSystem