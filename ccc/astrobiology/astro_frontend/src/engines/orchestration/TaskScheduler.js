/**
 * 任务调度器
 * 负责管理任务队列、依赖关系解析、并行/串行执行控制
 */
class TaskScheduler {
  constructor() {
    this.taskQueue = []
    this.runningTasks = new Map()
    this.completedTasks = new Map()
    this.failedTasks = new Map()
    
    // 配置
    this.config = {
      maxConcurrentTasks: 3,
      taskTimeout: 300000, // 5分钟
      retryDelay: 5000,
      maxRetries: 3,
      enableParallelExecution: true,
      enableDependencyResolution: true
    }
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 统计信息
    this.stats = {
      totalTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
      runningTasks: 0,
      queuedTasks: 0,
      averageExecutionTime: 0,
      totalExecutionTime: 0
    }
  }

  /**
   * 添加任务到队列
   * @param {Object} task - 任务定义
   * @returns {Promise} 任务执行Promise
   */
  async scheduleTask(task) {
    const taskId = task.id || this.generateTaskId()
    const scheduledTask = {
      ...task,
      id: taskId,
      status: 'queued',
      createdAt: new Date().toISOString(),
      scheduledAt: new Date().toISOString(),
      retryCount: 0,
      dependencies: task.dependencies || [],
      priority: task.priority || 0
    }

    this.taskQueue.push(scheduledTask)
    this.stats.totalTasks++
    this.stats.queuedTasks++
    
    this.emit('task_scheduled', { task: scheduledTask })
    
    // 尝试执行任务
    this.processQueue()
    
    return this.waitForTaskCompletion(taskId)
  }

  /**
   * 处理任务队列
   */
  async processQueue() {
    if (this.runningTasks.size >= this.config.maxConcurrentTasks) {
      return
    }

    // 按优先级和创建时间排序
    this.taskQueue.sort((a, b) => {
      if (a.priority !== b.priority) {
        return b.priority - a.priority
      }
      return new Date(a.createdAt) - new Date(b.createdAt)
    })

    const tasksToExecute = []
    
    for (const task of this.taskQueue) {
      if (this.runningTasks.size >= this.config.maxConcurrentTasks) {
        break
      }

      // 检查依赖关系
      if (this.config.enableDependencyResolution) {
        if (this.areDependenciesMet(task)) {
          tasksToExecute.push(task)
        }
      } else {
        tasksToExecute.push(task)
      }
    }

    // 执行任务
    for (const task of tasksToExecute) {
      this.executeTask(task)
    }
  }

  /**
   * 检查依赖关系是否满足
   * @param {Object} task - 任务
   * @returns {boolean} 依赖关系是否满足
   */
  areDependenciesMet(task) {
    if (!task.dependencies || task.dependencies.length === 0) {
      return true
    }

    return task.dependencies.every(depId => {
      return this.completedTasks.has(depId)
    })
  }

  /**
   * 执行任务
   * @param {Object} task - 任务
   */
  async executeTask(task) {
    // 从队列中移除
    const taskIndex = this.taskQueue.findIndex(t => t.id === task.id)
    if (taskIndex > -1) {
      this.taskQueue.splice(taskIndex, 1)
      this.stats.queuedTasks--
    }

    // 添加到运行中任务
    task.status = 'running'
    task.startedAt = new Date().toISOString()
    this.runningTasks.set(task.id, task)
    this.stats.runningTasks++
    
    this.emit('task_started', { task })

    try {
      // 执行任务
      const result = await this.runTaskWithTimeout(task)
      
      // 任务成功完成
      task.status = 'completed'
      task.completedAt = new Date().toISOString()
      task.result = result
      task.executionTime = new Date(task.completedAt) - new Date(task.startedAt)
      
      this.completedTasks.set(task.id, task)
      this.stats.completedTasks++
      this.stats.runningTasks--
      this.stats.totalExecutionTime += task.executionTime
      this.stats.averageExecutionTime = this.stats.totalExecutionTime / this.stats.completedTasks
      
      this.runningTasks.delete(task.id)
      this.emit('task_completed', { task, result })
      
    } catch (error) {
      // 任务执行失败
      task.status = 'failed'
      task.failedAt = new Date().toISOString()
      task.error = error.message
      task.executionTime = new Date(task.failedAt) - new Date(task.startedAt)
      
      // 检查是否需要重试
      if (task.retryCount < this.config.maxRetries) {
        task.retryCount++
        task.status = 'queued'
        task.scheduledAt = new Date(Date.now() + this.config.retryDelay).toISOString()
        
        // 重新加入队列
        this.taskQueue.push(task)
        this.stats.queuedTasks++
        
        this.emit('task_retry', { task, error })
      } else {
        this.failedTasks.set(task.id, task)
        this.stats.failedTasks++
        this.emit('task_failed', { task, error })
      }
      
      this.stats.runningTasks--
      this.runningTasks.delete(task.id)
    }

    // 继续处理队列
    this.processQueue()
  }

  /**
   * 带超时的任务执行
   * @param {Object} task - 任务
   * @returns {Promise} 执行结果
   */
  async runTaskWithTimeout(task) {
    const timeout = task.timeout || this.config.taskTimeout
    
    return new Promise(async (resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`任务${task.id}执行超时`))
      }, timeout)

      try {
        const result = await this.executeTaskFunction(task)
        clearTimeout(timeoutId)
        resolve(result)
      } catch (error) {
        clearTimeout(timeoutId)
        reject(error)
      }
    })
  }

  /**
   * 执行任务函数
   * @param {Object} task - 任务
   * @returns {Promise} 执行结果
   */
  async executeTaskFunction(task) {
    // 这里应该调用实际的任务执行器
    // 暂时模拟执行
    if (task.executor && typeof task.executor === 'function') {
      return await task.executor(task)
    }
    
    // 模拟异步执行
    await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500))
    
    return {
      taskId: task.id,
      status: 'success',
      data: task.parameters || {},
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 等待任务完成
   * @param {string} taskId - 任务ID
   * @returns {Promise} 任务结果
   */
  waitForTaskCompletion(taskId) {
    return new Promise((resolve, reject) => {
      const checkTask = () => {
        if (this.completedTasks.has(taskId)) {
          const task = this.completedTasks.get(taskId)
          resolve(task.result)
        } else if (this.failedTasks.has(taskId)) {
          const task = this.failedTasks.get(taskId)
          reject(new Error(task.error))
        } else {
          // 继续等待
          setTimeout(checkTask, 100)
        }
      }
      
      checkTask()
    })
  }

  /**
   * 暂停任务
   * @param {string} taskId - 任务ID
   * @returns {boolean} 是否成功暂停
   */
  pauseTask(taskId) {
    const task = this.runningTasks.get(taskId)
    if (task) {
      task.status = 'paused'
      task.pausedAt = new Date().toISOString()
      this.emit('task_paused', { task })
      return true
    }
    return false
  }

  /**
   * 恢复任务
   * @param {string} taskId - 任务ID
   * @returns {boolean} 是否成功恢复
   */
  resumeTask(taskId) {
    const task = this.runningTasks.get(taskId)
    if (task && task.status === 'paused') {
      task.status = 'running'
      task.resumedAt = new Date().toISOString()
      this.emit('task_resumed', { task })
      return true
    }
    return false
  }

  /**
   * 取消任务
   * @param {string} taskId - 任务ID
   * @returns {boolean} 是否成功取消
   */
  cancelTask(taskId) {
    // 从队列中移除
    const queueIndex = this.taskQueue.findIndex(t => t.id === taskId)
    if (queueIndex > -1) {
      const task = this.taskQueue.splice(queueIndex, 1)[0]
      task.status = 'cancelled'
      task.cancelledAt = new Date().toISOString()
      this.stats.queuedTasks--
      this.emit('task_cancelled', { task })
      return true
    }

    // 取消运行中的任务
    const runningTask = this.runningTasks.get(taskId)
    if (runningTask) {
      runningTask.status = 'cancelled'
      runningTask.cancelledAt = new Date().toISOString()
      this.runningTasks.delete(taskId)
      this.stats.runningTasks--
      this.emit('task_cancelled', { task: runningTask })
      return true
    }

    return false
  }

  /**
   * 获取任务状态
   * @param {string} taskId - 任务ID
   * @returns {Object|null} 任务状态
   */
  getTaskStatus(taskId) {
    if (this.runningTasks.has(taskId)) {
      return this.runningTasks.get(taskId)
    }
    if (this.completedTasks.has(taskId)) {
      return this.completedTasks.get(taskId)
    }
    if (this.failedTasks.has(taskId)) {
      return this.failedTasks.get(taskId)
    }
    
    const queuedTask = this.taskQueue.find(t => t.id === taskId)
    return queuedTask || null
  }

  /**
   * 获取所有任务状态
   * @returns {Object} 所有任务状态
   */
  getAllTaskStatus() {
    return {
      queued: this.taskQueue,
      running: Array.from(this.runningTasks.values()),
      completed: Array.from(this.completedTasks.values()),
      failed: Array.from(this.failedTasks.values()),
      stats: this.stats
    }
  }

  /**
   * 清理已完成的任务
   * @param {number} maxAge - 最大保留时间（毫秒）
   */
  cleanupCompletedTasks(maxAge = 24 * 60 * 60 * 1000) { // 24小时
    const cutoffTime = new Date(Date.now() - maxAge)
    
    for (const [taskId, task] of this.completedTasks) {
      if (new Date(task.completedAt) < cutoffTime) {
        this.completedTasks.delete(taskId)
      }
    }
    
    for (const [taskId, task] of this.failedTasks) {
      if (new Date(task.failedAt) < cutoffTime) {
        this.failedTasks.delete(taskId)
      }
    }
  }

  /**
   * 生成任务ID
   * @returns {string} 任务ID
   */
  generateTaskId() {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
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
   * 获取统计信息
   * @returns {Object} 统计信息
   */
  getStats() {
    return { ...this.stats }
  }

  /**
   * 重置统计信息
   */
  resetStats() {
    this.stats = {
      totalTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
      runningTasks: 0,
      queuedTasks: 0,
      averageExecutionTime: 0,
      totalExecutionTime: 0
    }
  }

  /**
   * 清理资源
   */
  destroy() {
    this.taskQueue = []
    this.runningTasks.clear()
    this.completedTasks.clear()
    this.failedTasks.clear()
    this.eventListeners.clear()
    this.resetStats()
    this.emit('scheduler_destroyed')
  }
}

export default TaskScheduler