/**
 * 任务编排引擎核心类
 * 整合工作流定义、任务调度和执行监控
 */
import WorkflowDefinition from './WorkflowDefinition.js'
import TaskScheduler from './TaskScheduler.js'
import ExecutionMonitor from './ExecutionMonitor.js'

class TaskOrchestrationEngine {
  constructor() {
    this.workflowDefinition = new WorkflowDefinition()
    this.taskScheduler = new TaskScheduler()
    this.executionMonitor = new ExecutionMonitor()
    
    // 工作流实例
    this.workflowInstances = new Map()
    
    // 配置
    this.config = {
      enableParallelExecution: true,
      enableDependencyResolution: true,
      enableRealTimeMonitoring: true,
      maxConcurrentWorkflows: 5,
      workflowTimeout: 30 * 60 * 1000, // 30分钟
      stepTimeout: 5 * 60 * 1000, // 5分钟
      retryCount: 3,
      retryDelay: 5000
    }
    
    // 事件监听器
    this.eventListeners = new Map()
    
    // 服务注册表
    this.serviceRegistry = new Map()
    
    this.initializeEventHandlers()
  }

  /**
   * 初始化事件处理器
   */
  initializeEventHandlers() {
    // 监听任务调度器事件
    this.taskScheduler.on('task_completed', (data) => {
      this.handleTaskCompleted(data)
    })
    
    this.taskScheduler.on('task_failed', (data) => {
      this.handleTaskFailed(data)
    })
    
    // 监听执行监控器事件
    this.executionMonitor.on('execution_completed', (data) => {
      this.handleExecutionCompleted(data)
    })
    
    this.executionMonitor.on('execution_failed', (data) => {
      this.handleExecutionFailed(data)
    })
  }

  /**
   * 执行工作流
   * @param {string} workflowId - 工作流ID
   * @param {Object} parameters - 参数
   * @param {Object} options - 选项
   * @returns {Promise<Object>} 执行结果
   */
  async executeWorkflow(workflowId, parameters = {}, options = {}) {
    // 获取工作流定义
    const workflowTemplate = this.workflowDefinition.getTemplate(workflowId)
    if (!workflowTemplate) {
      throw new Error(`工作流模板${workflowId}不存在`)
    }

    // 创建工作流实例
    const instanceId = this.generateInstanceId()
    const workflowInstance = {
      id: instanceId,
      templateId: workflowId,
      template: workflowTemplate,
      status: 'initializing',
      startTime: Date.now(),
      parameters: parameters,
      options: { ...this.config, ...options },
      steps: [],
      currentStep: null,
      progress: 0,
      result: null,
      error: null
    }

    this.workflowInstances.set(instanceId, workflowInstance)

    try {
      // 注册执行监控
      this.executionMonitor.registerExecution(instanceId, {
        steps: workflowTemplate.steps,
        config: workflowInstance.options
      })

      // 验证参数
      const validationResult = this.validateWorkflowParameters(workflowTemplate, parameters)
      if (!validationResult.isValid) {
        throw new Error(`参数验证失败: ${validationResult.errors.join(', ')}`)
      }

      // 初始化步骤
      workflowInstance.steps = this.initializeWorkflowSteps(workflowTemplate, parameters)
      workflowInstance.status = 'running'

      this.emit('workflow_started', { instanceId, workflowInstance })

      // 执行工作流步骤
      const result = await this.executeWorkflowSteps(workflowInstance)

      // 完成工作流
      workflowInstance.status = 'completed'
      workflowInstance.endTime = Date.now()
      workflowInstance.executionTime = workflowInstance.endTime - workflowInstance.startTime
      workflowInstance.result = result
      workflowInstance.progress = 100

      this.executionMonitor.completeExecution(instanceId, result)
      this.emit('workflow_completed', { instanceId, workflowInstance, result })

      return result

    } catch (error) {
      // 工作流执行失败
      workflowInstance.status = 'failed'
      workflowInstance.endTime = Date.now()
      workflowInstance.executionTime = workflowInstance.endTime - workflowInstance.startTime
      workflowInstance.error = error.message

      this.executionMonitor.failExecution(instanceId, error)
      this.emit('workflow_failed', { instanceId, workflowInstance, error })

      throw error
    }
  }

  /**
   * 验证工作流参数
   * @param {Object} workflowTemplate - 工作流模板
   * @param {Object} parameters - 参数
   * @returns {Object} 验证结果
   */
  validateWorkflowParameters(workflowTemplate, parameters) {
    const validation = {
      isValid: true,
      errors: [],
      warnings: []
    }

    // 检查必需参数
    if (workflowTemplate.conditions?.start?.required) {
      for (const requiredParam of workflowTemplate.conditions.start.required) {
        if (!parameters[requiredParam]) {
          validation.isValid = false
          validation.errors.push(`缺少必需参数: ${requiredParam}`)
        }
      }
    }

    return validation
  }

  /**
   * 初始化工作流步骤
   * @param {Object} workflowTemplate - 工作流模板
   * @param {Object} parameters - 参数
   * @returns {Array} 步骤列表
   */
  initializeWorkflowSteps(workflowTemplate, parameters) {
    return workflowTemplate.steps.map(stepTemplate => ({
      ...stepTemplate,
      status: 'pending',
      startTime: null,
      endTime: null,
      executionTime: 0,
      retryCount: 0,
      result: null,
      error: null,
      parameters: this.resolveStepParameters(stepTemplate, parameters)
    }))
  }

  /**
   * 解析步骤参数
   * @param {Object} stepTemplate - 步骤模板
   * @param {Object} parameters - 参数
   * @returns {Object} 解析后的参数
   */
  resolveStepParameters(stepTemplate, parameters) {
    const resolvedParameters = {}

    if (stepTemplate.parameters) {
      for (const [key, paramDef] of Object.entries(stepTemplate.parameters)) {
        if (paramDef.source) {
          // 从其他步骤的结果中获取参数
          const [stepId, resultPath] = paramDef.source.split('.')
          // 这里需要实现参数解析逻辑
          resolvedParameters[key] = parameters[key] || paramDef.default
        } else {
          resolvedParameters[key] = parameters[key] || paramDef.default
        }
      }
    }

    return resolvedParameters
  }

  /**
   * 执行工作流步骤
   * @param {Object} workflowInstance - 工作流实例
   * @returns {Promise<Object>} 执行结果
   */
  async executeWorkflowSteps(workflowInstance) {
    const { steps } = workflowInstance
    const results = {}

    // 按依赖关系排序步骤
    const sortedSteps = this.sortStepsByDependencies(steps)

    for (const step of sortedSteps) {
      try {
        // 更新当前步骤
        workflowInstance.currentStep = step.id
        this.executionMonitor.updateExecutionStatus(workflowInstance.id, {
          currentStep: step.id,
          completedSteps: steps.filter(s => s.status === 'completed').length
        })

        // 执行步骤
        const stepResult = await this.executeStep(step, workflowInstance)
        
        step.status = 'completed'
        step.endTime = Date.now()
        step.executionTime = step.endTime - step.startTime
        step.result = stepResult
        
        results[step.id] = stepResult

        this.emit('step_completed', { 
          instanceId: workflowInstance.id, 
          step, 
          result: stepResult 
        })

      } catch (error) {
        step.status = 'failed'
        step.endTime = Date.now()
        step.executionTime = step.endTime - step.startTime
        step.error = error.message

        this.emit('step_failed', { 
          instanceId: workflowInstance.id, 
          step, 
          error 
        })

        // 如果步骤是必需的，停止工作流
        if (step.required) {
          throw error
        }
      }
    }

    return results
  }

  /**
   * 按依赖关系排序步骤
   * @param {Array} steps - 步骤列表
   * @returns {Array} 排序后的步骤列表
   */
  sortStepsByDependencies(steps) {
    const sorted = []
    const visited = new Set()
    const visiting = new Set()

    const visit = (step) => {
      if (visiting.has(step.id)) {
        throw new Error(`循环依赖检测到: ${step.id}`)
      }
      if (visited.has(step.id)) {
        return
      }

      visiting.add(step.id)

      // 先访问依赖的步骤
      if (step.dependencies) {
        for (const depId of step.dependencies) {
          const depStep = steps.find(s => s.id === depId)
          if (depStep) {
            visit(depStep)
          }
        }
      }

      visiting.delete(step.id)
      visited.add(step.id)
      sorted.push(step)
    }

    for (const step of steps) {
      if (!visited.has(step.id)) {
        visit(step)
      }
    }

    return sorted
  }

  /**
   * 执行单个步骤
   * @param {Object} step - 步骤
   * @param {Object} workflowInstance - 工作流实例
   * @returns {Promise<Object>} 步骤结果
   */
  async executeStep(step, workflowInstance) {
    step.status = 'running'
    step.startTime = Date.now()

    this.emit('step_started', { 
      instanceId: workflowInstance.id, 
      step 
    })

    // 获取执行器
    const executor = this.serviceRegistry.get(step.executor)
    if (!executor) {
      throw new Error(`执行器${step.executor}未注册`)
    }

    // 创建任务
    const task = {
      id: `${workflowInstance.id}_${step.id}`,
      type: step.type,
      executor: step.executor,
      parameters: step.parameters,
      timeout: step.timeout || this.config.stepTimeout,
      retryCount: step.retryCount || this.config.retryCount,
      retryDelay: step.retryDelay || this.config.retryDelay
    }

    // 调度任务
    const result = await this.taskScheduler.scheduleTask(task)
    
    return result
  }

  /**
   * 注册服务
   * @param {string} serviceName - 服务名称
   * @param {Object} service - 服务对象
   */
  registerService(serviceName, service) {
    this.serviceRegistry.set(serviceName, service)
    this.emit('service_registered', { serviceName, service })
  }

  /**
   * 取消工作流
   * @param {string} instanceId - 实例ID
   * @returns {boolean} 是否成功取消
   */
  cancelWorkflow(instanceId) {
    const workflowInstance = this.workflowInstances.get(instanceId)
    if (!workflowInstance) {
      return false
    }

    workflowInstance.status = 'cancelled'
    workflowInstance.endTime = Date.now()
    workflowInstance.executionTime = workflowInstance.endTime - workflowInstance.startTime

    // 取消所有相关任务
    for (const step of workflowInstance.steps) {
      if (step.status === 'running') {
        this.taskScheduler.cancelTask(`${instanceId}_${step.id}`)
      }
    }

    this.emit('workflow_cancelled', { instanceId, workflowInstance })
    return true
  }

  /**
   * 获取工作流状态
   * @param {string} instanceId - 实例ID
   * @returns {Object|null} 工作流状态
   */
  getWorkflowStatus(instanceId) {
    const workflowInstance = this.workflowInstances.get(instanceId)
    if (!workflowInstance) {
      return null
    }

    const executionStatus = this.executionMonitor.getExecutionStatus(instanceId)
    
    return {
      ...workflowInstance,
      executionStatus
    }
  }

  /**
   * 获取所有工作流状态
   * @returns {Array} 所有工作流状态
   */
  getAllWorkflowStatus() {
    return Array.from(this.workflowInstances.values()).map(instance => 
      this.getWorkflowStatus(instance.id)
    )
  }

  /**
   * 处理任务完成
   * @param {Object} data - 任务数据
   */
  handleTaskCompleted(data) {
    this.emit('task_completed', data)
  }

  /**
   * 处理任务失败
   * @param {Object} data - 任务数据
   */
  handleTaskFailed(data) {
    this.emit('task_failed', data)
  }

  /**
   * 处理执行完成
   * @param {Object} data - 执行数据
   */
  handleExecutionCompleted(data) {
    this.emit('execution_completed', data)
  }

  /**
   * 处理执行失败
   * @param {Object} data - 执行数据
   */
  handleExecutionFailed(data) {
    this.emit('execution_failed', data)
  }

  /**
   * 生成实例ID
   * @returns {string} 实例ID
   */
  generateInstanceId() {
    return `workflow_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
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
    this.taskScheduler.updateConfig(newConfig)
    this.executionMonitor.updateConfig(newConfig)
    this.emit('config_updated', { config: this.config })
  }

  /**
   * 获取统计信息
   * @returns {Object} 统计信息
   */
  getStats() {
    return {
      workflowInstances: this.workflowInstances.size,
      taskScheduler: this.taskScheduler.getStats(),
      executionMonitor: this.executionMonitor.getGlobalStats(),
      performanceMetrics: this.executionMonitor.getPerformanceMetrics()
    }
  }

  /**
   * 清理资源
   */
  destroy() {
    this.taskScheduler.destroy()
    this.executionMonitor.destroy()
    this.workflowInstances.clear()
    this.serviceRegistry.clear()
    this.eventListeners.clear()
    this.emit('engine_destroyed')
  }
}

export default TaskOrchestrationEngine