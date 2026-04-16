/**
 * 执行监控器
 * 负责实时状态监控、进度跟踪、错误处理和重试
 */
class ExecutionMonitor {
  constructor() {
    this.monitors = new Map()
    this.globalStats = {
      totalExecutions: 0,
      successfulExecutions: 0,
      failedExecutions: 0,
      averageExecutionTime: 0,
      totalExecutionTime: 0,
      lastExecutionTime: null,
      uptime: Date.now()
    }
    
    // 配置
    this.config = {
      monitoringInterval: 1000, // 1秒
      maxRetries: 3,
      retryDelay: 5000,
      enableRealTimeMonitoring: true,
      enableProgressTracking: true,
      enableErrorHandling: true,
      enablePerformanceMetrics: true
    }
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 监控定时器
    this.monitoringTimer = null
    
    // 性能指标
    this.performanceMetrics = {
      cpuUsage: 0,
      memoryUsage: 0,
      networkLatency: 0,
      responseTime: 0,
      throughput: 0
    }
    
    this.startMonitoring()
  }

  /**
   * 开始监控
   */
  startMonitoring() {
    if (this.config.enableRealTimeMonitoring && !this.monitoringTimer) {
      this.monitoringTimer = setInterval(() => {
        this.updateGlobalStats()
        this.updatePerformanceMetrics()
        this.checkForStuckExecutions()
      }, this.config.monitoringInterval)
    }
  }

  /**
   * 停止监控
   */
  stopMonitoring() {
    if (this.monitoringTimer) {
      clearInterval(this.monitoringTimer)
      this.monitoringTimer = null
    }
  }

  /**
   * 注册执行监控
   * @param {string} executionId - 执行ID
   * @param {Object} executionInfo - 执行信息
   * @returns {Object} 监控对象
   */
  registerExecution(executionId, executionInfo) {
    const monitor = {
      id: executionId,
      status: 'registered',
      startTime: Date.now(),
      lastUpdateTime: Date.now(),
      progress: 0,
      currentStep: null,
      steps: executionInfo.steps || [],
      totalSteps: executionInfo.steps?.length || 0,
      completedSteps: 0,
      failedSteps: 0,
      retryCount: 0,
      errors: [],
      warnings: [],
      metrics: {
        executionTime: 0,
        stepTimes: {},
        memoryUsage: [],
        cpuUsage: [],
        networkRequests: 0,
        dataProcessed: 0
      },
      config: {
        ...this.config,
        ...executionInfo.config
      }
    }

    this.monitors.set(executionId, monitor)
    this.globalStats.totalExecutions++
    
    this.emit('execution_registered', { executionId, monitor })
    
    return monitor
  }

  /**
   * 更新执行状态
   * @param {string} executionId - 执行ID
   * @param {Object} update - 更新信息
   */
  updateExecutionStatus(executionId, update) {
    const monitor = this.monitors.get(executionId)
    if (!monitor) {
      console.warn(`Monitor not found for execution ${executionId}`)
      return
    }

    const previousStatus = monitor.status
    const previousProgress = monitor.progress

    // 更新状态
    Object.assign(monitor, update)
    monitor.lastUpdateTime = Date.now()

    // 计算进度
    if (update.currentStep) {
      monitor.currentStep = update.currentStep
      monitor.completedSteps = update.completedSteps || monitor.completedSteps
      monitor.progress = this.calculateProgress(monitor)
    }

    // 更新指标
    if (update.stepTime) {
      monitor.metrics.stepTimes[update.currentStep] = update.stepTime
    }

    if (update.memoryUsage) {
      monitor.metrics.memoryUsage.push({
        timestamp: Date.now(),
        usage: update.memoryUsage
      })
    }

    if (update.cpuUsage) {
      monitor.metrics.cpuUsage.push({
        timestamp: Date.now(),
        usage: update.cpuUsage
      })
    }

    // 触发事件
    if (previousStatus !== monitor.status) {
      this.emit('execution_status_changed', { executionId, monitor, previousStatus })
    }

    if (previousProgress !== monitor.progress) {
      this.emit('execution_progress_updated', { executionId, monitor, previousProgress })
    }

    this.emit('execution_updated', { executionId, monitor })
  }

  /**
   * 完成执行
   * @param {string} executionId - 执行ID
   * @param {Object} result - 执行结果
   */
  completeExecution(executionId, result) {
    const monitor = this.monitors.get(executionId)
    if (!monitor) {
      console.warn(`Monitor not found for execution ${executionId}`)
      return
    }

    monitor.status = 'completed'
    monitor.endTime = Date.now()
    monitor.executionTime = monitor.endTime - monitor.startTime
    monitor.progress = 100
    monitor.result = result

    this.globalStats.successfulExecutions++
    this.globalStats.totalExecutionTime += monitor.executionTime
    this.globalStats.averageExecutionTime = this.globalStats.totalExecutionTime / this.globalStats.successfulExecutions
    this.globalStats.lastExecutionTime = new Date().toISOString()

    this.emit('execution_completed', { executionId, monitor, result })
  }

  /**
   * 执行失败
   * @param {string} executionId - 执行ID
   * @param {Error} error - 错误信息
   */
  failExecution(executionId, error) {
    const monitor = this.monitors.get(executionId)
    if (!monitor) {
      console.warn(`Monitor not found for execution ${executionId}`)
      return
    }

    monitor.status = 'failed'
    monitor.endTime = Date.now()
    monitor.executionTime = monitor.endTime - monitor.startTime
    monitor.errors.push({
      message: error.message,
      stack: error.stack,
      timestamp: new Date().toISOString()
    })

    this.globalStats.failedExecutions++

    // 检查是否需要重试
    if (monitor.retryCount < monitor.config.maxRetries) {
      monitor.retryCount++
      monitor.status = 'retrying'
      monitor.retryScheduledAt = Date.now() + monitor.config.retryDelay
      
      this.emit('execution_retry_scheduled', { executionId, monitor, retryCount: monitor.retryCount })
      
      // 安排重试
      setTimeout(() => {
        this.emit('execution_retry', { executionId, monitor })
      }, monitor.config.retryDelay)
    } else {
      this.emit('execution_failed', { executionId, monitor, error })
    }
  }

  /**
   * 计算进度
   * @param {Object} monitor - 监控对象
   * @returns {number} 进度百分比
   */
  calculateProgress(monitor) {
    if (monitor.totalSteps === 0) {
      return 0
    }

    const stepProgress = (monitor.completedSteps / monitor.totalSteps) * 100
    
    // 如果有当前步骤，添加部分进度
    if (monitor.currentStep && monitor.stepProgress) {
      const stepWeight = 100 / monitor.totalSteps
      const currentStepProgress = (monitor.stepProgress / 100) * stepWeight
      return Math.min(stepProgress + currentStepProgress, 100)
    }

    return Math.min(stepProgress, 100)
  }

  /**
   * 更新全局统计
   */
  updateGlobalStats() {
    const now = Date.now()
    this.globalStats.uptime = now - this.globalStats.uptime
    
    // 更新运行中的执行数量
    const runningExecutions = Array.from(this.monitors.values()).filter(
      monitor => monitor.status === 'running' || monitor.status === 'retrying'
    ).length
    
    this.globalStats.runningExecutions = runningExecutions
  }

  /**
   * 更新性能指标
   */
  updatePerformanceMetrics() {
    if (!this.config.enablePerformanceMetrics) {
      return
    }

    // 模拟性能指标更新（实际项目中应该从系统API获取）
    this.performanceMetrics.cpuUsage = Math.random() * 100
    this.performanceMetrics.memoryUsage = Math.random() * 100
    this.performanceMetrics.networkLatency = Math.random() * 100
    this.performanceMetrics.responseTime = Math.random() * 1000
    this.performanceMetrics.throughput = Math.random() * 1000

    this.emit('performance_metrics_updated', { metrics: this.performanceMetrics })
  }

  /**
   * 检查卡住的执行
   */
  checkForStuckExecutions() {
    const now = Date.now()
    const stuckThreshold = 5 * 60 * 1000 // 5分钟

    for (const [executionId, monitor] of this.monitors) {
      if (monitor.status === 'running' && (now - monitor.lastUpdateTime) > stuckThreshold) {
        monitor.status = 'stuck'
        monitor.stuckAt = now
        
        this.emit('execution_stuck', { executionId, monitor })
        
        // 尝试恢复
        this.attemptRecovery(executionId, monitor)
      }
    }
  }

  /**
   * 尝试恢复执行
   * @param {string} executionId - 执行ID
   * @param {Object} monitor - 监控对象
   */
  attemptRecovery(executionId, monitor) {
    // 这里可以实现恢复逻辑
    // 例如：重新启动执行、跳过卡住的步骤等
    
    this.emit('execution_recovery_attempted', { executionId, monitor })
  }

  /**
   * 获取执行状态
   * @param {string} executionId - 执行ID
   * @returns {Object|null} 执行状态
   */
  getExecutionStatus(executionId) {
    return this.monitors.get(executionId) || null
  }

  /**
   * 获取所有执行状态
   * @returns {Array} 所有执行状态
   */
  getAllExecutionStatus() {
    return Array.from(this.monitors.values())
  }

  /**
   * 获取全局统计
   * @returns {Object} 全局统计
   */
  getGlobalStats() {
    return { ...this.globalStats }
  }

  /**
   * 获取性能指标
   * @returns {Object} 性能指标
   */
  getPerformanceMetrics() {
    return { ...this.performanceMetrics }
  }

  /**
   * 清理旧的监控数据
   * @param {number} maxAge - 最大保留时间（毫秒）
   */
  cleanupOldMonitors(maxAge = 24 * 60 * 60 * 1000) { // 24小时
    const cutoffTime = Date.now() - maxAge
    
    for (const [executionId, monitor] of this.monitors) {
      if (monitor.endTime && monitor.endTime < cutoffTime) {
        this.monitors.delete(executionId)
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
    
    if (newConfig.enableRealTimeMonitoring !== undefined) {
      if (newConfig.enableRealTimeMonitoring) {
        this.startMonitoring()
      } else {
        this.stopMonitoring()
      }
    }
    
    this.emit('config_updated', { config: this.config })
  }

  /**
   * 导出监控数据
   * @returns {Object} 监控数据
   */
  exportData() {
    return {
      monitors: Array.from(this.monitors.entries()),
      globalStats: this.globalStats,
      performanceMetrics: this.performanceMetrics,
      config: this.config,
      exportTime: new Date().toISOString()
    }
  }

  /**
   * 清理资源
   */
  destroy() {
    this.stopMonitoring()
    this.monitors.clear()
    this.eventListeners.clear()
    this.globalStats = {
      totalExecutions: 0,
      successfulExecutions: 0,
      failedExecutions: 0,
      averageExecutionTime: 0,
      totalExecutionTime: 0,
      lastExecutionTime: null,
      uptime: Date.now()
    }
    this.emit('monitor_destroyed')
  }
}

export default ExecutionMonitor