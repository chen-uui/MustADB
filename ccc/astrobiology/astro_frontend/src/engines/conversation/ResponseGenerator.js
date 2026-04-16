/**
 * 响应生成器
 * 负责生成智能响应和建议
 */
class ResponseGenerator {
  constructor() {
    // 响应模板
    this.responseTemplates = {
      search_meteorite: {
        success: "我找到了{meteoriteName}陨石的信息：{summary}。您想了解更多详情吗？",
        notFound: "抱歉，我没有找到{meteoriteName}陨石的信息。您可以尝试搜索其他陨石名称。",
        ambiguous: "我找到了多个可能的陨石：{meteoriteNames}。请指定您要查找的具体陨石。"
      },
      
      upload_document: {
        success: "文档{fileName}上传成功！我现在可以帮您分析这个文档。",
        error: "文档上传失败：{error}。请检查文件格式和大小。",
        processing: "文档{fileName}正在处理中，请稍候..."
      },
      
      analyze_document: {
        success: "文档分析完成！我发现了以下关键信息：{summary}",
        processing: "正在分析文档{fileName}，这可能需要几分钟时间...",
        error: "文档分析失败：{error}。请检查文档内容。"
      },
      
      extract_data: {
        success: "数据提取完成！我提取了以下数据：{data}",
        processing: "正在提取数据，请稍候...",
        error: "数据提取失败：{error}。请检查文档内容。"
      },
      
      intelligent_qa: {
        success: "根据文档内容，{answer}",
        processing: "正在分析您的问题，请稍候...",
        error: "无法回答您的问题：{error}。请尝试重新表述问题。"
      },
      
      view_results: {
        success: "以下是分析结果：{results}",
        notFound: "没有找到相关结果。请先进行分析。",
        error: "获取结果失败：{error}。"
      },
      
      generate_report: {
        success: "报告生成完成！{reportSummary}",
        processing: "正在生成报告，请稍候...",
        error: "报告生成失败：{error}。"
      },
      
      help: {
        general: "我是智能RAG工作台助手，可以帮您：\n1. 搜索陨石信息\n2. 上传和分析文档\n3. 提取数据\n4. 智能问答\n5. 生成报告\n\n请告诉我您需要什么帮助？",
        specific: "关于{topic}，我可以帮您：{helpContent}"
      },
      
      check_status: {
        idle: "系统当前处于空闲状态。",
        processing: "系统正在处理{currentTask}，进度：{progress}%",
        error: "系统遇到错误：{error}。"
      },
      
      unknown: {
        default: "抱歉，我没有理解您的意思。您可以尝试：\n1. 搜索陨石信息\n2. 上传文档进行分析\n3. 询问关于陨石的问题\n4. 查看分析结果\n\n或者输入'帮助'获取更多信息。"
      }
    }
    
    // 建议模板
    this.suggestionTemplates = {
      afterSearch: [
        "您想了解这个陨石的矿物组成吗？",
        "需要查看相关的文档吗？",
        "想了解更多关于这类陨石的信息吗？"
      ],
      
      afterUpload: [
        "现在可以分析这个文档了",
        "需要提取特定数据吗？",
        "想进行智能问答吗？"
      ],
      
      afterAnalysis: [
        "需要提取更多数据吗？",
        "想生成分析报告吗？",
        "有其他问题要问吗？"
      ],
      
      afterExtraction: [
        "数据提取完成，需要生成报告吗？",
        "想查看数据可视化吗？",
        "有其他分析需求吗？"
      ],
      
      afterQA: [
        "还有其他问题吗？",
        "需要查看更多相关信息吗？",
        "想生成问答报告吗？"
      ]
    }
    
    // 工作流建议
    this.workflowSuggestions = {
      meteorite_analysis: [
        "我将帮您分析陨石文档，包括：",
        "1. 搜索陨石基本信息",
        "2. 分析文档内容",
        "3. 提取关键数据",
        "4. 生成综合分析报告"
      ],
      
      comprehensive_analysis: [
        "我将为您进行全面分析，包括：",
        "1. 上传并处理文档",
        "2. 智能分析内容",
        "3. 提取结构化数据",
        "4. 生成详细报告"
      ]
    }
  }

  /**
   * 生成响应
   * @param {string} intent - 意图
   * @param {Object} entities - 实体
   * @param {Object} context - 上下文
   * @param {Object} additionalData - 额外数据
   * @returns {Object} 响应结果
   */
  async generate(intent, entities, context, additionalData = {}) {
    const response = {
      intent,
      message: '',
      suggestions: [],
      actions: [],
      data: additionalData,
      timestamp: new Date().toISOString()
    }
    
    // 生成主要消息
    response.message = this.generateMessage(intent, entities, context, additionalData)
    
    // 生成建议
    response.suggestions = this.generateSuggestions(intent, entities, context)
    
    // 生成操作建议
    response.actions = this.generateActions(intent, entities, context)
    
    return response
  }

  /**
   * 生成消息
   * @param {string} intent - 意图
   * @param {Object} entities - 实体
   * @param {Object} context - 上下文
   * @param {Object} additionalData - 额外数据
   * @returns {string} 消息内容
   */
  generateMessage(intent, entities, context, additionalData) {
    const template = this.responseTemplates[intent] || this.responseTemplates.unknown
    
    if (typeof template === 'string') {
      return this.fillTemplate(template, entities, additionalData)
    }
    
    // 根据状态选择模板
    let templateKey = 'success'
    if (additionalData.status === 'processing') {
      templateKey = 'processing'
    } else if (additionalData.status === 'error') {
      templateKey = 'error'
    } else if (additionalData.status === 'notFound') {
      templateKey = 'notFound'
    }
    
    const selectedTemplate = template[templateKey] || template.success || template.default
    
    return this.fillTemplate(selectedTemplate, entities, additionalData)
  }

  /**
   * 填充模板
   * @param {string} template - 模板字符串
   * @param {Object} entities - 实体
   * @param {Object} additionalData - 额外数据
   * @returns {string} 填充后的字符串
   */
  fillTemplate(template, entities, additionalData) {
    let result = template
    
    // 替换实体占位符
    Object.keys(entities).forEach(key => {
      const value = entities[key]
      if (Array.isArray(value) && value.length > 0) {
        result = result.replace(new RegExp(`{${key}}`, 'g'), value[0])
        result = result.replace(new RegExp(`{${key}s}`, 'g'), value.join('、'))
      } else if (value) {
        result = result.replace(new RegExp(`{${key}}`, 'g'), value)
      }
    })
    
    // 替换额外数据占位符
    Object.keys(additionalData).forEach(key => {
      const value = additionalData[key]
      if (value !== undefined && value !== null) {
        result = result.replace(new RegExp(`{${key}}`, 'g'), value)
      }
    })
    
    return result
  }

  /**
   * 生成建议
   * @param {string} intent - 意图
   * @param {Object} entities - 实体
   * @param {Object} context - 上下文
   * @returns {Array} 建议列表
   */
  generateSuggestions(intent, entities, context) {
    const suggestions = []
    
    // 基于意图生成建议
    switch (intent) {
      case 'search_meteorite':
        if (entities.meteoriteNames && entities.meteoriteNames.length > 0) {
          suggestions.push(...this.suggestionTemplates.afterSearch)
        }
        break
        
      case 'upload_document':
        suggestions.push(...this.suggestionTemplates.afterUpload)
        break
        
      case 'analyze_document':
        suggestions.push(...this.suggestionTemplates.afterAnalysis)
        break
        
      case 'extract_data':
        suggestions.push(...this.suggestionTemplates.afterExtraction)
        break
        
      case 'intelligent_qa':
        suggestions.push(...this.suggestionTemplates.afterQA)
        break
        
      case 'help':
        suggestions.push('您可以尝试以下操作：')
        suggestions.push('• 搜索陨石信息')
        suggestions.push('• 上传文档进行分析')
        suggestions.push('• 进行智能问答')
        suggestions.push('• 查看分析结果')
        break
    }
    
    // 基于上下文生成建议
    if (context.workflowState) {
      const workflowSuggestions = this.workflowSuggestions[context.workflowState.type]
      if (workflowSuggestions) {
        suggestions.unshift(...workflowSuggestions)
      }
    }
    
    // 基于会话历史生成建议
    if (context.sessionData.lastSearchedMeteorite) {
      suggestions.push(`继续分析${context.sessionData.lastSearchedMeteorite}陨石`)
    }
    
    if (context.sessionData.lastUploadedFile) {
      suggestions.push(`继续处理${context.sessionData.lastUploadedFile}文件`)
    }
    
    return suggestions.slice(0, 5) // 限制建议数量
  }

  /**
   * 生成操作建议
   * @param {string} intent - 意图
   * @param {Object} entities - 实体
   * @param {Object} context - 上下文
   * @returns {Array} 操作列表
   */
  generateActions(intent, entities, context) {
    const actions = []
    
    // 基于意图生成操作
    switch (intent) {
      case 'search_meteorite':
        if (entities.meteoriteNames && entities.meteoriteNames.length > 0) {
          actions.push({
            type: 'analyze_meteorite',
            label: '分析这个陨石',
            data: { meteoriteName: entities.meteoriteNames[0] }
          })
          actions.push({
            type: 'search_documents',
            label: '查找相关文档',
            data: { meteoriteName: entities.meteoriteNames[0] }
          })
        }
        break
        
      case 'upload_document':
        actions.push({
          type: 'analyze_document',
          label: '分析文档',
          data: { fileName: entities.fileNames?.[0] }
        })
        actions.push({
          type: 'extract_data',
          label: '提取数据',
          data: { fileName: entities.fileNames?.[0] }
        })
        break
        
      case 'analyze_document':
        actions.push({
          type: 'extract_data',
          label: '提取数据',
          data: { fileName: entities.fileNames?.[0] }
        })
        actions.push({
          type: 'intelligent_qa',
          label: '智能问答',
          data: { fileName: entities.fileNames?.[0] }
        })
        break
        
      case 'extract_data':
        actions.push({
          type: 'generate_report',
          label: '生成报告',
          data: { extractionType: entities.extractionType }
        })
        actions.push({
          type: 'view_results',
          label: '查看结果',
          data: { dataType: 'extracted' }
        })
        break
        
      case 'intelligent_qa':
        actions.push({
          type: 'generate_report',
          label: '生成问答报告',
          data: { reportType: 'qa' }
        })
        actions.push({
          type: 'view_results',
          label: '查看问答历史',
          data: { dataType: 'qa' }
        })
        break
    }
    
    // 基于工作流状态生成操作
    if (context.workflowState) {
      const { currentStep, progress } = context.workflowState
      
      if (progress < 100) {
        actions.push({
          type: 'check_status',
          label: '查看进度',
          data: { workflowId: context.workflowState.type }
        })
      }
      
      if (progress === 100) {
        actions.push({
          type: 'view_results',
          label: '查看完整结果',
          data: { workflowId: context.workflowState.type }
        })
      }
    }
    
    return actions.slice(0, 3) // 限制操作数量
  }

  /**
   * 生成工作流响应
   * @param {Object} workflowState - 工作流状态
   * @param {Object} stepResult - 步骤结果
   * @returns {Object} 工作流响应
   */
  generateWorkflowResponse(workflowState, stepResult) {
    const response = {
      type: 'workflow',
      workflow: workflowState,
      message: '',
      suggestions: [],
      actions: [],
      timestamp: new Date().toISOString()
    }
    
    // 生成工作流消息
    switch (workflowState.status) {
      case 'started':
        response.message = `开始执行${workflowState.type}工作流...`
        break
      case 'in_progress':
        response.message = `正在执行${workflowState.currentStep}步骤，进度：${workflowState.progress}%`
        break
      case 'completed':
        response.message = `工作流执行完成！`
        break
      case 'error':
        response.message = `工作流执行失败：${stepResult.error}`
        break
    }
    
    // 生成工作流建议
    if (workflowState.status === 'completed') {
      response.suggestions.push('查看完整分析结果')
      response.suggestions.push('生成详细报告')
      response.suggestions.push('导出分析数据')
    } else if (workflowState.status === 'in_progress') {
      response.suggestions.push('查看当前进度')
      response.suggestions.push('暂停工作流')
    }
    
    // 生成工作流操作
    if (workflowState.status === 'completed') {
      response.actions.push({
        type: 'view_results',
        label: '查看结果',
        data: { workflowId: workflowState.type }
      })
      response.actions.push({
        type: 'generate_report',
        label: '生成报告',
        data: { workflowId: workflowState.type }
      })
    }
    
    return response
  }

  /**
   * 生成错误响应
   * @param {Error} error - 错误对象
   * @param {string} intent - 意图
   * @returns {Object} 错误响应
   */
  generateErrorResponse(error, intent) {
    return {
      intent,
      message: `抱歉，处理您的请求时遇到错误：${error.message}`,
      suggestions: [
        '请检查输入是否正确',
        '尝试重新表述您的需求',
        '联系技术支持获取帮助'
      ],
      actions: [
        {
          type: 'retry',
          label: '重试',
          data: { originalIntent: intent }
        },
        {
          type: 'help',
          label: '获取帮助',
          data: { topic: intent }
        }
      ],
      error: {
        message: error.message,
        stack: error.stack,
        timestamp: new Date().toISOString()
      },
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 生成确认响应
   * @param {string} intent - 意图
   * @param {Object} entities - 实体
   * @param {string} confirmationMessage - 确认消息
   * @returns {Object} 确认响应
   */
  generateConfirmationResponse(intent, entities, confirmationMessage) {
    return {
      intent,
      message: confirmationMessage,
      suggestions: [
        '确认执行',
        '取消操作',
        '修改参数'
      ],
      actions: [
        {
          type: 'confirm',
          label: '确认',
          data: { intent, entities }
        },
        {
          type: 'cancel',
          label: '取消',
          data: { intent }
        }
      ],
      requiresConfirmation: true,
      timestamp: new Date().toISOString()
    }
  }
}

export default ResponseGenerator