/**
 * 内容推荐器
 * 负责基于内容的推荐算法
 */
class ContentRecommender {
  constructor() {
    this.contentDatabase = new Map()
    this.contentFeatures = new Map()
    this.userProfiles = new Map()
    
    // 配置
    this.config = {
      enableContentBasedRecommendation: true,
      enableCollaborativeFiltering: true,
      enableHybridRecommendation: true,
      maxRecommendations: 10,
      similarityThreshold: 0.3,
      diversityWeight: 0.2,
      noveltyWeight: 0.1,
      popularityWeight: 0.3
    }
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 推荐缓存
    this.recommendationCache = new Map()
    this.cacheExpiry = 5 * 60 * 1000 // 5分钟
  }

  /**
   * 添加内容
   * @param {string} contentId - 内容ID
   * @param {Object} content - 内容数据
   * @param {Object} features - 内容特征
   */
  addContent(contentId, content, features = {}) {
    this.contentDatabase.set(contentId, {
      ...content,
      id: contentId,
      addedAt: new Date().toISOString(),
      popularity: 0,
      rating: 0,
      viewCount: 0
    })
    
    this.contentFeatures.set(contentId, {
      ...features,
      id: contentId,
      lastUpdated: new Date().toISOString()
    })
    
    this.emit('content_added', { contentId, content, features })
  }

  /**
   * 更新内容特征
   * @param {string} contentId - 内容ID
   * @param {Object} features - 新特征
   */
  updateContentFeatures(contentId, features) {
    if (this.contentFeatures.has(contentId)) {
      const existingFeatures = this.contentFeatures.get(contentId)
      this.contentFeatures.set(contentId, {
        ...existingFeatures,
        ...features,
        lastUpdated: new Date().toISOString()
      })
      
      this.emit('content_features_updated', { contentId, features })
    }
  }

  /**
   * 记录用户交互
   * @param {string} userId - 用户ID
   * @param {string} contentId - 内容ID
   * @param {string} interactionType - 交互类型
   * @param {Object} metadata - 元数据
   */
  recordInteraction(userId, contentId, interactionType, metadata = {}) {
    const interaction = {
      userId,
      contentId,
      type: interactionType,
      timestamp: new Date().toISOString(),
      metadata
    }
    
    // 更新内容统计
    if (this.contentDatabase.has(contentId)) {
      const content = this.contentDatabase.get(contentId)
      content.viewCount++
      
      if (interactionType === 'like' || interactionType === 'rating') {
        content.rating = this.calculateAverageRating(contentId, interactionType, metadata.rating)
      }
      
      content.popularity = this.calculatePopularity(contentId)
    }
    
    // 更新用户画像
    this.updateUserProfile(userId, contentId, interactionType, metadata)
    
    // 清除相关推荐缓存
    this.clearRecommendationCache(userId)
    
    this.emit('interaction_recorded', interaction)
  }

  /**
   * 更新用户画像
   * @param {string} userId - 用户ID
   * @param {string} contentId - 内容ID
   * @param {string} interactionType - 交互类型
   * @param {Object} metadata - 元数据
   */
  updateUserProfile(userId, contentId, interactionType, metadata) {
    if (!this.userProfiles.has(userId)) {
      this.userProfiles.set(userId, {
        id: userId,
        preferences: new Map(),
        interactionHistory: [],
        lastUpdated: new Date().toISOString()
      })
    }
    
    const profile = this.userProfiles.get(userId)
    
    // 添加交互历史
    profile.interactionHistory.push({
      contentId,
      type: interactionType,
      timestamp: new Date().toISOString(),
      metadata
    })
    
    // 限制历史长度
    if (profile.interactionHistory.length > 1000) {
      profile.interactionHistory = profile.interactionHistory.slice(-1000)
    }
    
    // 更新偏好
    if (this.contentFeatures.has(contentId)) {
      const features = this.contentFeatures.get(contentId)
      this.updateUserPreferences(profile, features, interactionType, metadata)
    }
    
    profile.lastUpdated = new Date().toISOString()
  }

  /**
   * 更新用户偏好
   * @param {Object} profile - 用户画像
   * @param {Object} features - 内容特征
   * @param {string} interactionType - 交互类型
   * @param {Object} metadata - 元数据
   */
  updateUserPreferences(profile, features, interactionType, metadata) {
    const weight = this.getInteractionWeight(interactionType, metadata)
    
    Object.keys(features).forEach(feature => {
      if (feature === 'id' || feature === 'lastUpdated') return
      
      const featureValue = features[feature]
      const currentPreference = profile.preferences.get(feature) || 0
      const newPreference = currentPreference + (featureValue * weight)
      
      profile.preferences.set(feature, newPreference)
    })
  }

  /**
   * 获取交互权重
   * @param {string} interactionType - 交互类型
   * @param {Object} metadata - 元数据
   * @returns {number} 权重
   */
  getInteractionWeight(interactionType, metadata) {
    const weights = {
      'view': 0.1,
      'like': 0.5,
      'dislike': -0.3,
      'rating': metadata.rating ? metadata.rating / 5 : 0.3,
      'share': 0.8,
      'download': 0.6,
      'bookmark': 0.7
    }
    
    return weights[interactionType] || 0.2
  }

  /**
   * 计算平均评分
   * @param {string} contentId - 内容ID
   * @param {string} interactionType - 交互类型
   * @param {number} rating - 评分
   * @returns {number} 平均评分
   */
  calculateAverageRating(contentId, interactionType, rating) {
    // 这里应该从数据库获取历史评分数据
    // 暂时返回当前评分
    return rating || 0
  }

  /**
   * 计算内容流行度
   * @param {string} contentId - 内容ID
   * @returns {number} 流行度
   */
  calculatePopularity(contentId) {
    const content = this.contentDatabase.get(contentId)
    if (!content) return 0
    
    // 基于查看次数、评分、时间衰减计算流行度
    const timeDecay = Math.exp(-0.1 * this.getDaysSinceAdded(contentId))
    return (content.viewCount * 0.1 + content.rating * 0.5) * timeDecay
  }

  /**
   * 获取内容添加天数
   * @param {string} contentId - 内容ID
   * @returns {number} 天数
   */
  getDaysSinceAdded(contentId) {
    const content = this.contentDatabase.get(contentId)
    if (!content) return 0
    
    const addedDate = new Date(content.addedAt)
    const now = new Date()
    return (now - addedDate) / (1000 * 60 * 60 * 24)
  }

  /**
   * 生成内容推荐
   * @param {string} userId - 用户ID
   * @param {Object} context - 上下文
   * @returns {Promise<Array>} 推荐结果
   */
  async generateRecommendations(userId, context = {}) {
    // 检查缓存
    const cacheKey = `${userId}_${JSON.stringify(context)}`
    if (this.recommendationCache.has(cacheKey)) {
      const cached = this.recommendationCache.get(cacheKey)
      if (Date.now() - cached.timestamp < this.cacheExpiry) {
        return cached.recommendations
      }
    }
    
    const recommendations = []
    
    // 基于内容的推荐
    if (this.config.enableContentBasedRecommendation) {
      const contentBasedRecs = await this.generateContentBasedRecommendations(userId, context)
      recommendations.push(...contentBasedRecs)
    }
    
    // 协同过滤推荐
    if (this.config.enableCollaborativeFiltering) {
      const collaborativeRecs = await this.generateCollaborativeRecommendations(userId, context)
      recommendations.push(...collaborativeRecs)
    }
    
    // 混合推荐
    if (this.config.enableHybridRecommendation) {
      const hybridRecs = await this.generateHybridRecommendations(userId, context)
      recommendations.push(...hybridRecs)
    }
    
    // 去重和排序
    const uniqueRecommendations = this.deduplicateRecommendations(recommendations)
    const sortedRecommendations = this.sortRecommendations(uniqueRecommendations, userId, context)
    
    // 限制推荐数量
    const finalRecommendations = sortedRecommendations.slice(0, this.config.maxRecommendations)
    
    // 缓存结果
    this.recommendationCache.set(cacheKey, {
      recommendations: finalRecommendations,
      timestamp: Date.now()
    })
    
    this.emit('recommendations_generated', { userId, recommendations: finalRecommendations })
    
    return finalRecommendations
  }

  /**
   * 生成基于内容的推荐
   * @param {string} userId - 用户ID
   * @param {Object} context - 上下文
   * @returns {Promise<Array>} 推荐结果
   */
  async generateContentBasedRecommendations(userId, context) {
    const userProfile = this.userProfiles.get(userId)
    if (!userProfile) return []
    
    const recommendations = []
    
    for (const [contentId, content] of this.contentDatabase) {
      // 跳过用户已经交互过的内容
      if (this.hasUserInteracted(userId, contentId)) continue
      
      const features = this.contentFeatures.get(contentId)
      if (!features) continue
      
      const similarity = this.calculateContentSimilarity(userProfile.preferences, features)
      
      if (similarity > this.config.similarityThreshold) {
        recommendations.push({
          contentId,
          score: similarity,
          type: 'content_based',
          reason: '基于内容相似性',
          metadata: {
            similarity,
            features: Object.keys(features).filter(k => k !== 'id' && k !== 'lastUpdated')
          }
        })
      }
    }
    
    return recommendations
  }

  /**
   * 生成协同过滤推荐
   * @param {string} userId - 用户ID
   * @param {Object} context - 上下文
   * @returns {Promise<Array>} 推荐结果
   */
  async generateCollaborativeRecommendations(userId, context) {
    const userProfile = this.userProfiles.get(userId)
    if (!userProfile) return []
    
    const recommendations = []
    const similarUsers = this.findSimilarUsers(userId)
    
    for (const similarUser of similarUsers) {
      const similarUserProfile = this.userProfiles.get(similarUser.userId)
      if (!similarUserProfile) continue
      
      // 找到相似用户喜欢但当前用户未交互的内容
      for (const interaction of similarUserProfile.interactionHistory) {
        if (interaction.type === 'like' || interaction.type === 'rating') {
          if (!this.hasUserInteracted(userId, interaction.contentId)) {
            recommendations.push({
              contentId: interaction.contentId,
              score: similarUser.similarity * this.getInteractionWeight(interaction.type, interaction.metadata),
              type: 'collaborative',
              reason: `相似用户${similarUser.userId}喜欢`,
              metadata: {
                similarUser: similarUser.userId,
                similarity: similarUser.similarity,
                interactionType: interaction.type
              }
            })
          }
        }
      }
    }
    
    return recommendations
  }

  /**
   * 生成混合推荐
   * @param {string} userId - 用户ID
   * @param {Object} context - 上下文
   * @returns {Promise<Array>} 推荐结果
   */
  async generateHybridRecommendations(userId, context) {
    const recommendations = []
    
    // 基于流行度的推荐
    const popularContent = Array.from(this.contentDatabase.values())
      .sort((a, b) => b.popularity - a.popularity)
      .slice(0, 20)
    
    for (const content of popularContent) {
      if (!this.hasUserInteracted(userId, content.id)) {
        recommendations.push({
          contentId: content.id,
          score: content.popularity * this.config.popularityWeight,
          type: 'hybrid',
          reason: '热门内容',
          metadata: {
            popularity: content.popularity,
            viewCount: content.viewCount,
            rating: content.rating
          }
        })
      }
    }
    
    return recommendations
  }

  /**
   * 计算内容相似性
   * @param {Map} userPreferences - 用户偏好
   * @param {Object} contentFeatures - 内容特征
   * @returns {number} 相似性分数
   */
  calculateContentSimilarity(userPreferences, contentFeatures) {
    let similarity = 0
    let totalWeight = 0
    
    for (const [feature, preference] of userPreferences) {
      if (contentFeatures[feature] !== undefined) {
        const featureValue = contentFeatures[feature]
        const weight = Math.abs(preference)
        
        similarity += preference * featureValue * weight
        totalWeight += weight
      }
    }
    
    return totalWeight > 0 ? similarity / totalWeight : 0
  }

  /**
   * 查找相似用户
   * @param {string} userId - 用户ID
   * @returns {Array} 相似用户列表
   */
  findSimilarUsers(userId) {
    const userProfile = this.userProfiles.get(userId)
    if (!userProfile) return []
    
    const similarUsers = []
    
    for (const [otherUserId, otherProfile] of this.userProfiles) {
      if (otherUserId === userId) continue
      
      const similarity = this.calculateUserSimilarity(userProfile, otherProfile)
      
      if (similarity > this.config.similarityThreshold) {
        similarUsers.push({
          userId: otherUserId,
          similarity
        })
      }
    }
    
    return similarUsers.sort((a, b) => b.similarity - a.similarity).slice(0, 10)
  }

  /**
   * 计算用户相似性
   * @param {Object} userProfile1 - 用户画像1
   * @param {Object} userProfile2 - 用户画像2
   * @returns {number} 相似性分数
   */
  calculateUserSimilarity(userProfile1, userProfile2) {
    let similarity = 0
    let totalWeight = 0
    
    // 基于偏好计算相似性
    for (const [feature, preference1] of userProfile1.preferences) {
      const preference2 = userProfile2.preferences.get(feature)
      if (preference2 !== undefined) {
        const weight = Math.abs(preference1) + Math.abs(preference2)
        similarity += preference1 * preference2 * weight
        totalWeight += weight
      }
    }
    
    return totalWeight > 0 ? similarity / totalWeight : 0
  }

  /**
   * 检查用户是否已交互
   * @param {string} userId - 用户ID
   * @param {string} contentId - 内容ID
   * @returns {boolean} 是否已交互
   */
  hasUserInteracted(userId, contentId) {
    const profile = this.userProfiles.get(userId)
    if (!profile) return false
    
    return profile.interactionHistory.some(interaction => 
      interaction.contentId === contentId
    )
  }

  /**
   * 去重推荐结果
   * @param {Array} recommendations - 推荐列表
   * @returns {Array} 去重后的推荐列表
   */
  deduplicateRecommendations(recommendations) {
    const seen = new Set()
    return recommendations.filter(rec => {
      if (seen.has(rec.contentId)) {
        return false
      }
      seen.add(rec.contentId)
      return true
    })
  }

  /**
   * 排序推荐结果
   * @param {Array} recommendations - 推荐列表
   * @param {string} userId - 用户ID
   * @param {Object} context - 上下文
   * @returns {Array} 排序后的推荐列表
   */
  sortRecommendations(recommendations, userId, context) {
    return recommendations.sort((a, b) => {
      // 主要按分数排序
      if (a.score !== b.score) {
        return b.score - a.score
      }
      
      // 次要按类型排序
      const typeOrder = { 'content_based': 3, 'collaborative': 2, 'hybrid': 1 }
      return typeOrder[b.type] - typeOrder[a.type]
    })
  }

  /**
   * 清除推荐缓存
   * @param {string} userId - 用户ID
   */
  clearRecommendationCache(userId) {
    for (const [key, value] of this.recommendationCache) {
      if (key.startsWith(`${userId}_`)) {
        this.recommendationCache.delete(key)
      }
    }
  }

  /**
   * 获取用户画像
   * @param {string} userId - 用户ID
   * @returns {Object|null} 用户画像
   */
  getUserProfile(userId) {
    return this.userProfiles.get(userId) || null
  }

  /**
   * 获取内容信息
   * @param {string} contentId - 内容ID
   * @returns {Object|null} 内容信息
   */
  getContent(contentId) {
    return this.contentDatabase.get(contentId) || null
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
    this.emit('config_updated', { config: this.config })
  }

  /**
   * 清理资源
   */
  destroy() {
    this.contentDatabase.clear()
    this.contentFeatures.clear()
    this.userProfiles.clear()
    this.recommendationCache.clear()
    this.eventListeners.clear()
    this.emit('recommender_destroyed')
  }
}

export default ContentRecommender