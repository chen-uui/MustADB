/**
 * 用户行为分析器
 * 负责分析用户行为模式、使用频率统计、偏好分析
 */
class UserBehaviorAnalyzer {
  constructor() {
    this.behaviorData = new Map()
    this.patterns = new Map()
    this.statistics = {
      totalSessions: 0,
      totalInteractions: 0,
      averageSessionDuration: 0,
      mostUsedFeatures: new Map(),
      userPreferences: new Map(),
      behaviorTrends: []
    }
    
    // 配置
    this.config = {
      enableRealTimeAnalysis: true,
      enablePatternRecognition: true,
      enablePreferenceLearning: true,
      analysisInterval: 60000, // 1分钟
      maxHistoryLength: 1000,
      patternThreshold: 0.7,
      preferenceWeight: 0.8
    }
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 分析定时器
    this.analysisTimer = null
    
    this.startAnalysis()
  }

  /**
   * 开始分析
   */
  startAnalysis() {
    if (this.config.enableRealTimeAnalysis && !this.analysisTimer) {
      this.analysisTimer = setInterval(() => {
        this.performRealTimeAnalysis()
      }, this.config.analysisInterval)
    }
  }

  /**
   * 停止分析
   */
  stopAnalysis() {
    if (this.analysisTimer) {
      clearInterval(this.analysisTimer)
      this.analysisTimer = null
    }
  }

  /**
   * 记录用户行为
   * @param {string} userId - 用户ID
   * @param {Object} behavior - 行为数据
   */
  recordBehavior(userId, behavior) {
    const behaviorEntry = {
      ...behavior,
      timestamp: new Date().toISOString(),
      sessionId: behavior.sessionId || this.generateSessionId(),
      userId: userId
    }

    // 存储行为数据
    if (!this.behaviorData.has(userId)) {
      this.behaviorData.set(userId, [])
    }
    
    const userBehaviors = this.behaviorData.get(userId)
    userBehaviors.push(behaviorEntry)
    
    // 限制历史长度
    if (userBehaviors.length > this.config.maxHistoryLength) {
      userBehaviors.splice(0, userBehaviors.length - this.config.maxHistoryLength)
    }

    // 更新统计信息
    this.updateStatistics(behaviorEntry)
    
    // 实时分析
    if (this.config.enableRealTimeAnalysis) {
      this.analyzeBehaviorPattern(userId, behaviorEntry)
    }

    this.emit('behavior_recorded', { userId, behavior: behaviorEntry })
  }

  /**
   * 分析用户行为模式
   * @param {string} userId - 用户ID
   * @param {Object} behavior - 行为数据
   */
  analyzeBehaviorPattern(userId, behavior) {
    const userBehaviors = this.behaviorData.get(userId) || []
    
    // 分析功能使用模式
    this.analyzeFeatureUsagePattern(userId, userBehaviors)
    
    // 分析时间模式
    this.analyzeTimePattern(userId, userBehaviors)
    
    // 分析工作流模式
    this.analyzeWorkflowPattern(userId, userBehaviors)
    
    // 分析偏好模式
    this.analyzePreferencePattern(userId, userBehaviors)
  }

  /**
   * 分析功能使用模式
   * @param {string} userId - 用户ID
   * @param {Array} behaviors - 行为列表
   */
  analyzeFeatureUsagePattern(userId, behaviors) {
    const featureUsage = new Map()
    
    behaviors.forEach(behavior => {
      if (behavior.type === 'feature_usage') {
        const feature = behavior.feature
        featureUsage.set(feature, (featureUsage.get(feature) || 0) + 1)
      }
    })

    // 计算使用频率
    const totalUsage = Array.from(featureUsage.values()).reduce((sum, count) => sum + count, 0)
    const usagePattern = new Map()
    
    for (const [feature, count] of featureUsage) {
      usagePattern.set(feature, count / totalUsage)
    }

    // 识别常用功能
    const frequentFeatures = Array.from(usagePattern.entries())
      .filter(([feature, frequency]) => frequency > 0.1)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)

    this.patterns.set(`${userId}_feature_usage`, {
      type: 'feature_usage',
      pattern: usagePattern,
      frequentFeatures,
      confidence: this.calculatePatternConfidence(behaviors.length)
    })
  }

  /**
   * 分析时间模式
   * @param {string} userId - 用户ID
   * @param {Array} behaviors - 行为列表
   */
  analyzeTimePattern(userId, behaviors) {
    const timePattern = {
      hourly: new Map(),
      daily: new Map(),
      weekly: new Map()
    }

    behaviors.forEach(behavior => {
      const date = new Date(behavior.timestamp)
      const hour = date.getHours()
      const day = date.getDay()
      const week = Math.floor(date.getDate() / 7)

      timePattern.hourly.set(hour, (timePattern.hourly.get(hour) || 0) + 1)
      timePattern.daily.set(day, (timePattern.daily.get(day) || 0) + 1)
      timePattern.weekly.set(week, (timePattern.weekly.get(week) || 0) + 1)
    })

    // 识别活跃时间段
    const activeHours = Array.from(timePattern.hourly.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([hour, count]) => hour)

    const activeDays = Array.from(timePattern.daily.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)
      .map(([day, count]) => day)

    this.patterns.set(`${userId}_time_pattern`, {
      type: 'time_pattern',
      pattern: timePattern,
      activeHours,
      activeDays,
      confidence: this.calculatePatternConfidence(behaviors.length)
    })
  }

  /**
   * 分析工作流模式
   * @param {string} userId - 用户ID
   * @param {Array} behaviors - 行为列表
   */
  analyzeWorkflowPattern(userId, behaviors) {
    const workflowSequences = []
    let currentSequence = []

    behaviors.forEach(behavior => {
      if (behavior.type === 'workflow_step') {
        currentSequence.push(behavior.step)
      } else if (behavior.type === 'workflow_complete') {
        if (currentSequence.length > 0) {
          workflowSequences.push([...currentSequence])
          currentSequence = []
        }
      }
    })

    // 分析常见工作流序列
    const sequenceCounts = new Map()
    workflowSequences.forEach(sequence => {
      const key = sequence.join('->')
      sequenceCounts.set(key, (sequenceCounts.get(key) || 0) + 1)
    })

    const commonSequences = Array.from(sequenceCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)

    this.patterns.set(`${userId}_workflow_pattern`, {
      type: 'workflow_pattern',
      sequences: workflowSequences,
      commonSequences,
      confidence: this.calculatePatternConfidence(workflowSequences.length)
    })
  }

  /**
   * 分析偏好模式
   * @param {string} userId - 用户ID
   * @param {Array} behaviors - 行为列表
   */
  analyzePreferencePattern(userId, behaviors) {
    const preferences = {
      features: new Map(),
      workflows: new Map(),
      settings: new Map(),
      content: new Map()
    }

    behaviors.forEach(behavior => {
      if (behavior.type === 'preference_change') {
        const category = behavior.category
        const value = behavior.value
        
        if (preferences[category]) {
          preferences[category].set(value, (preferences[category].get(value) || 0) + 1)
        }
      }
    })

    // 计算偏好权重
    const preferenceWeights = new Map()
    Object.keys(preferences).forEach(category => {
      const categoryPrefs = preferences[category]
      const total = Array.from(categoryPrefs.values()).reduce((sum, count) => sum + count, 0)
      
      if (total > 0) {
        for (const [value, count] of categoryPrefs) {
          const weight = count / total
          preferenceWeights.set(`${category}_${value}`, weight)
        }
      }
    })

    this.patterns.set(`${userId}_preference_pattern`, {
      type: 'preference_pattern',
      preferences,
      weights: preferenceWeights,
      confidence: this.calculatePatternConfidence(behaviors.length)
    })
  }

  /**
   * 计算模式置信度
   * @param {number} sampleSize - 样本大小
   * @returns {number} 置信度
   */
  calculatePatternConfidence(sampleSize) {
    if (sampleSize < 10) return 0.3
    if (sampleSize < 50) return 0.6
    if (sampleSize < 100) return 0.8
    return 0.9
  }

  /**
   * 更新统计信息
   * @param {Object} behavior - 行为数据
   */
  updateStatistics(behavior) {
    this.statistics.totalInteractions++
    
    if (behavior.type === 'session_start') {
      this.statistics.totalSessions++
    }
    
    if (behavior.type === 'feature_usage') {
      const feature = behavior.feature
      this.statistics.mostUsedFeatures.set(
        feature, 
        (this.statistics.mostUsedFeatures.get(feature) || 0) + 1
      )
    }
  }

  /**
   * 执行实时分析
   */
  performRealTimeAnalysis() {
    // 分析行为趋势
    this.analyzeBehaviorTrends()
    
    // 更新用户偏好
    this.updateUserPreferences()
    
    // 检测异常行为
    this.detectAnomalousBehavior()
  }

  /**
   * 分析行为趋势
   */
  analyzeBehaviorTrends() {
    const now = Date.now()
    const oneHourAgo = now - 60 * 60 * 1000
    const oneDayAgo = now - 24 * 60 * 60 * 1000
    
    const recentBehaviors = []
    const dailyBehaviors = []
    
    for (const [userId, behaviors] of this.behaviorData) {
      behaviors.forEach(behavior => {
        const timestamp = new Date(behavior.timestamp).getTime()
        
        if (timestamp > oneHourAgo) {
          recentBehaviors.push(behavior)
        }
        
        if (timestamp > oneDayAgo) {
          dailyBehaviors.push(behavior)
        }
      })
    }
    
    // 计算趋势
    const trends = {
      hourly: recentBehaviors.length,
      daily: dailyBehaviors.length,
      trend: this.calculateTrend(recentBehaviors.length, dailyBehaviors.length / 24)
    }
    
    this.statistics.behaviorTrends.push({
      timestamp: new Date().toISOString(),
      trends
    })
    
    // 限制趋势历史长度
    if (this.statistics.behaviorTrends.length > 100) {
      this.statistics.behaviorTrends.splice(0, this.statistics.behaviorTrends.length - 100)
    }
  }

  /**
   * 计算趋势
   * @param {number} current - 当前值
   * @param {number} previous - 之前的值
   * @returns {string} 趋势方向
   */
  calculateTrend(current, previous) {
    if (current > previous * 1.2) return 'increasing'
    if (current < previous * 0.8) return 'decreasing'
    return 'stable'
  }

  /**
   * 更新用户偏好
   */
  updateUserPreferences() {
    for (const [userId, behaviors] of this.behaviorData) {
      const preferencePattern = this.patterns.get(`${userId}_preference_pattern`)
      if (preferencePattern) {
        this.statistics.userPreferences.set(userId, preferencePattern.weights)
      }
    }
  }

  /**
   * 检测异常行为
   */
  detectAnomalousBehavior() {
    // 检测异常使用模式
    for (const [userId, behaviors] of this.behaviorData) {
      const recentBehaviors = behaviors.filter(behavior => {
        const timestamp = new Date(behavior.timestamp).getTime()
        return timestamp > Date.now() - 60 * 60 * 1000 // 最近1小时
      })
      
      if (recentBehaviors.length > 100) { // 异常高频使用
        this.emit('anomalous_behavior_detected', {
          userId,
          type: 'high_frequency',
          behaviors: recentBehaviors
        })
      }
    }
  }

  /**
   * 获取用户行为模式
   * @param {string} userId - 用户ID
   * @returns {Object} 行为模式
   */
  getUserBehaviorPattern(userId) {
    const patterns = {}
    
    for (const [key, pattern] of this.patterns) {
      if (key.startsWith(`${userId}_`)) {
        const patternType = key.replace(`${userId}_`, '')
        patterns[patternType] = pattern
      }
    }
    
    return patterns
  }

  /**
   * 获取用户偏好
   * @param {string} userId - 用户ID
   * @returns {Object} 用户偏好
   */
  getUserPreferences(userId) {
    return this.statistics.userPreferences.get(userId) || new Map()
  }

  /**
   * 获取统计信息
   * @returns {Object} 统计信息
   */
  getStatistics() {
    return {
      ...this.statistics,
      totalUsers: this.behaviorData.size,
      totalPatterns: this.patterns.size
    }
  }

  /**
   * 生成会话ID
   * @returns {string} 会话ID
   */
  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
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
    
    if (newConfig.enableRealTimeAnalysis !== undefined) {
      if (newConfig.enableRealTimeAnalysis) {
        this.startAnalysis()
      } else {
        this.stopAnalysis()
      }
    }
    
    this.emit('config_updated', { config: this.config })
  }

  /**
   * 清理资源
   */
  destroy() {
    this.stopAnalysis()
    this.behaviorData.clear()
    this.patterns.clear()
    this.eventListeners.clear()
    this.emit('analyzer_destroyed')
  }
}

export default UserBehaviorAnalyzer