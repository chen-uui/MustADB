/**
 * 请求缓存工具
 * 用于避免重复的API请求，提升性能
 */

class RequestCache {
  constructor(maxSize = 50, ttl = 5 * 60 * 1000) {
    this.cache = new Map()
    this.maxSize = maxSize
    this.ttl = ttl // 默认5分钟过期
  }

  /**
   * 生成缓存key
   */
  generateKey(url, params = {}) {
    const sortedParams = Object.keys(params)
      .sort()
      .map(key => `${key}=${JSON.stringify(params[key])}`)
      .join('&')
    return `${url}?${sortedParams}`
  }

  /**
   * 获取缓存
   */
  get(url, params = {}) {
    const key = this.generateKey(url, params)
    const cached = this.cache.get(key)
    
    if (!cached) {
      return null
    }

    // 检查是否过期
    if (Date.now() - cached.timestamp > this.ttl) {
      this.cache.delete(key)
      return null
    }

    return cached.data
  }

  /**
   * 设置缓存
   */
  set(url, params = {}, data) {
    const key = this.generateKey(url, params)
    
    // 如果缓存已满，删除最旧的
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      this.cache.delete(firstKey)
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now()
    })
  }

  /**
   * 清除缓存
   */
  clear() {
    this.cache.clear()
  }

  /**
   * 删除特定URL的缓存
   */
  delete(url, params = {}) {
    const key = this.generateKey(url, params)
    this.cache.delete(key)
  }
}

// 导出单例
export default new RequestCache()

