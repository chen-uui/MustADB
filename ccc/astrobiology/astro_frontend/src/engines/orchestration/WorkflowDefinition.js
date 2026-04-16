/**
 * 工作流定义语言
 * 定义工作流的结构、步骤、依赖关系等
 */
class WorkflowDefinition {
  constructor() {
    // 预定义工作流模板
    this.templates = {
      // 陨石文档分析工作流
      meteorite_analysis: {
        id: 'meteorite_analysis',
        name: '陨石文档综合分析',
        description: '搜索陨石信息并分析相关文档',
        version: '1.0.0',
        category: 'analysis',
        tags: ['meteorite', 'document', 'analysis'],
        steps: [
          {
            id: 'search_meteorite',
            name: '搜索陨石信息',
            description: '搜索指定陨石的基本信息',
            type: 'meteorite_search',
            required: true,
            optional: false,
            dependencies: [],
            parameters: {
              meteoriteName: {
                type: 'string',
                required: true,
                description: '陨石名称'
              },
              searchType: {
                type: 'string',
                required: false,
                default: 'basic',
                options: ['basic', 'detailed', 'comprehensive'],
                description: '搜索类型'
              }
            },
            estimatedTime: 30,
            timeout: 60000,
            retryCount: 3,
            retryDelay: 5000,
            executor: 'MeteoriteSearchService'
          },
          {
            id: 'upload_document',
            name: '上传文档',
            description: '上传要分析的PDF文档',
            type: 'document_upload',
            required: true,
            optional: false,
            dependencies: [],
            parameters: {
              file: {
                type: 'file',
                required: true,
                description: 'PDF文档文件',
                accept: ['.pdf'],
                maxSize: '50MB'
              },
              documentType: {
                type: 'string',
                required: false,
                default: 'analysis',
                description: '文档类型'
              }
            },
            estimatedTime: 60,
            timeout: 120000,
            retryCount: 2,
            retryDelay: 10000,
            executor: 'DocumentManagementService'
          },
          {
            id: 'process_document',
            name: '处理文档',
            description: 'AI分析文档内容',
            type: 'document_processing',
            required: true,
            optional: false,
            dependencies: ['upload_document'],
            parameters: {
              documentId: {
                type: 'string',
                required: true,
                description: '文档ID',
                source: 'upload_document.result.documentId'
              },
              analysisType: {
                type: 'string',
                required: false,
                default: 'comprehensive',
                options: ['content', 'structure', 'semantic', 'comprehensive'],
                description: '分析类型'
              }
            },
            estimatedTime: 120,
            timeout: 300000,
            retryCount: 2,
            retryDelay: 15000,
            executor: 'DocumentProcessingService'
          },
          {
            id: 'extract_data',
            name: '提取数据',
            description: '提取结构化数据',
            type: 'data_extraction',
            required: true,
            optional: false,
            dependencies: ['process_document'],
            parameters: {
              documentId: {
                type: 'string',
                required: true,
                description: '文档ID',
                source: 'process_document.result.documentId'
              },
              extractionType: {
                type: 'string',
                required: false,
                default: 'comprehensive',
                options: ['mineral', 'organic', 'element', 'comprehensive'],
                description: '提取类型'
              },
              targetData: {
                type: 'array',
                required: false,
                default: ['all'],
                options: ['minerals', 'organic_compounds', 'elements', 'isotopes', 'all'],
                description: '目标数据类型'
              }
            },
            estimatedTime: 90,
            timeout: 240000,
            retryCount: 2,
            retryDelay: 12000,
            executor: 'DataExtractionService'
          },
          {
            id: 'correlate_data',
            name: '关联数据',
            description: '关联陨石信息和文档数据',
            type: 'data_correlation',
            required: false,
            optional: true,
            dependencies: ['search_meteorite', 'extract_data'],
            parameters: {
              meteoriteData: {
                type: 'object',
                required: true,
                description: '陨石数据',
                source: 'search_meteorite.result'
              },
              extractedData: {
                type: 'object',
                required: true,
                description: '提取的数据',
                source: 'extract_data.result'
              },
              correlationType: {
                type: 'string',
                required: false,
                default: 'comprehensive',
                options: ['mineral', 'composition', 'age', 'comprehensive'],
                description: '关联类型'
              }
            },
            estimatedTime: 60,
            timeout: 180000,
            retryCount: 2,
            retryDelay: 10000,
            executor: 'DataCorrelationService'
          },
          {
            id: 'generate_report',
            name: '生成报告',
            description: '生成综合分析报告',
            type: 'report_generation',
            required: true,
            optional: false,
            dependencies: ['extract_data', 'correlate_data'],
            parameters: {
              data: {
                type: 'object',
                required: true,
                description: '提取的数据',
                source: 'extract_data.result'
              },
              correlations: {
                type: 'object',
                required: false,
                description: '关联数据',
                source: 'correlate_data.result'
              },
              reportType: {
                type: 'string',
                required: false,
                default: 'comprehensive',
                options: ['summary', 'detailed', 'comprehensive'],
                description: '报告类型'
              },
              format: {
                type: 'string',
                required: false,
                default: 'pdf',
                options: ['pdf', 'html', 'json', 'markdown'],
                description: '报告格式'
              }
            },
            estimatedTime: 45,
            timeout: 120000,
            retryCount: 2,
            retryDelay: 8000,
            executor: 'ReportGenerationService'
          }
        ],
        conditions: {
          start: {
            type: 'user_input',
            required: ['meteoriteName', 'file']
          },
          success: {
            type: 'all_steps_completed',
            requiredSteps: ['search_meteorite', 'upload_document', 'process_document', 'extract_data', 'generate_report']
          },
          failure: {
            type: 'any_step_failed',
            maxRetries: 3
          }
        },
        metadata: {
          author: 'RAG Workspace',
          created: '2024-01-01',
          updated: '2024-01-01',
          license: 'MIT'
        }
      },
      
      // 全面分析工作流
      comprehensive_analysis: {
        id: 'comprehensive_analysis',
        name: '全面文档分析',
        description: '上传文档并进行全面分析',
        version: '1.0.0',
        category: 'analysis',
        tags: ['document', 'comprehensive', 'analysis'],
        steps: [
          {
            id: 'upload_document',
            name: '上传文档',
            description: '上传要分析的PDF文档',
            type: 'document_upload',
            required: true,
            optional: false,
            dependencies: [],
            parameters: {
              file: {
                type: 'file',
                required: true,
                description: 'PDF文档文件',
                accept: ['.pdf'],
                maxSize: '50MB'
              }
            },
            estimatedTime: 60,
            timeout: 120000,
            retryCount: 2,
            retryDelay: 10000,
            executor: 'DocumentManagementService'
          },
          {
            id: 'process_document',
            name: '处理文档',
            description: 'AI分析文档内容',
            type: 'document_processing',
            required: true,
            optional: false,
            dependencies: ['upload_document'],
            parameters: {
              documentId: {
                type: 'string',
                required: true,
                description: '文档ID',
                source: 'upload_document.result.documentId'
              }
            },
            estimatedTime: 120,
            timeout: 300000,
            retryCount: 2,
            retryDelay: 15000,
            executor: 'DocumentProcessingService'
          },
          {
            id: 'extract_data',
            name: '提取数据',
            description: '提取结构化数据',
            type: 'data_extraction',
            required: true,
            optional: false,
            dependencies: ['process_document'],
            parameters: {
              documentId: {
                type: 'string',
                required: true,
                description: '文档ID',
                source: 'process_document.result.documentId'
              }
            },
            estimatedTime: 90,
            timeout: 240000,
            retryCount: 2,
            retryDelay: 12000,
            executor: 'DataExtractionService'
          },
          {
            id: 'intelligent_qa',
            name: '智能问答',
            description: '基于文档内容进行问答',
            type: 'intelligent_qa',
            required: false,
            optional: true,
            dependencies: ['process_document'],
            parameters: {
              documentId: {
                type: 'string',
                required: true,
                description: '文档ID',
                source: 'process_document.result.documentId'
              },
              question: {
                type: 'string',
                required: false,
                description: '问题'
              }
            },
            estimatedTime: 30,
            timeout: 60000,
            retryCount: 2,
            retryDelay: 5000,
            executor: 'IntelligentQAService'
          },
          {
            id: 'direct_processing',
            name: '直接处理',
            description: '直接处理文档获取结果',
            type: 'direct_processing',
            required: false,
            optional: true,
            dependencies: ['upload_document'],
            parameters: {
              documentId: {
                type: 'string',
                required: true,
                description: '文档ID',
                source: 'upload_document.result.documentId'
              }
            },
            estimatedTime: 90,
            timeout: 180000,
            retryCount: 2,
            retryDelay: 10000,
            executor: 'DirectProcessingService'
          },
          {
            id: 'analysis_results',
            name: '结果分析',
            description: '分析和可视化结果',
            type: 'analysis_results',
            required: true,
            optional: false,
            dependencies: ['extract_data', 'intelligent_qa', 'direct_processing'],
            parameters: {
              extractedData: {
                type: 'object',
                required: true,
                description: '提取的数据',
                source: 'extract_data.result'
              },
              qaResults: {
                type: 'object',
                required: false,
                description: '问答结果',
                source: 'intelligent_qa.result'
              },
              directResults: {
                type: 'object',
                required: false,
                description: '直接处理结果',
                source: 'direct_processing.result'
              }
            },
            estimatedTime: 45,
            timeout: 120000,
            retryCount: 2,
            retryDelay: 8000,
            executor: 'AnalysisResultsService'
          },
          {
            id: 'generate_report',
            name: '生成报告',
            description: '生成最终分析报告',
            type: 'report_generation',
            required: true,
            optional: false,
            dependencies: ['analysis_results'],
            parameters: {
              analysisData: {
                type: 'object',
                required: true,
                description: '分析数据',
                source: 'analysis_results.result'
              }
            },
            estimatedTime: 30,
            timeout: 90000,
            retryCount: 2,
            retryDelay: 6000,
            executor: 'ReportGenerationService'
          }
        ],
        conditions: {
          start: {
            type: 'user_input',
            required: ['file']
          },
          success: {
            type: 'all_steps_completed',
            requiredSteps: ['upload_document', 'process_document', 'extract_data', 'analysis_results', 'generate_report']
          },
          failure: {
            type: 'any_step_failed',
            maxRetries: 3
          }
        },
        metadata: {
          author: 'RAG Workspace',
          created: '2024-01-01',
          updated: '2024-01-01',
          license: 'MIT'
        }
      }
    }
  }

  /**
   * 获取工作流模板
   * @param {string} templateId - 模板ID
   * @returns {Object|null} 工作流模板
   */
  getTemplate(templateId) {
    return this.templates[templateId] || null
  }

  /**
   * 获取所有模板
   * @returns {Object} 所有模板
   */
  getAllTemplates() {
    return this.templates
  }

  /**
   * 验证工作流定义
   * @param {Object} workflow - 工作流定义
   * @returns {Object} 验证结果
   */
  validateWorkflow(workflow) {
    const validation = {
      isValid: true,
      errors: [],
      warnings: []
    }

    // 检查必需字段
    if (!workflow.id) {
      validation.isValid = false
      validation.errors.push('工作流缺少ID')
    }

    if (!workflow.name) {
      validation.isValid = false
      validation.errors.push('工作流缺少名称')
    }

    if (!workflow.steps || !Array.isArray(workflow.steps)) {
      validation.isValid = false
      validation.errors.push('工作流缺少步骤定义')
    }

    // 验证步骤
    if (workflow.steps) {
      workflow.steps.forEach((step, index) => {
        const stepValidation = this.validateStep(step, index)
        if (!stepValidation.isValid) {
          validation.isValid = false
          validation.errors.push(...stepValidation.errors)
        }
        validation.warnings.push(...stepValidation.warnings)
      })
    }

    return validation
  }

  /**
   * 验证步骤定义
   * @param {Object} step - 步骤定义
   * @param {number} index - 步骤索引
   * @returns {Object} 验证结果
   */
  validateStep(step, index) {
    const validation = {
      isValid: true,
      errors: [],
      warnings: []
    }

    if (!step.id) {
      validation.isValid = false
      validation.errors.push(`步骤${index}缺少ID`)
    }

    if (!step.name) {
      validation.isValid = false
      validation.errors.push(`步骤${index}缺少名称`)
    }

    if (!step.type) {
      validation.isValid = false
      validation.errors.push(`步骤${index}缺少类型`)
    }

    if (!step.executor) {
      validation.isValid = false
      validation.errors.push(`步骤${index}缺少执行器`)
    }

    // 检查依赖关系
    if (step.dependencies && Array.isArray(step.dependencies)) {
      step.dependencies.forEach(dep => {
        if (typeof dep !== 'string') {
          validation.warnings.push(`步骤${index}的依赖关系格式不正确`)
        }
      })
    }

    return validation
  }

  /**
   * 创建自定义工作流
   * @param {Object} workflowData - 工作流数据
   * @returns {Object} 创建结果
   */
  createCustomWorkflow(workflowData) {
    const validation = this.validateWorkflow(workflowData)
    
    if (!validation.isValid) {
      return {
        success: false,
        errors: validation.errors,
        warnings: validation.warnings
      }
    }

    // 生成唯一ID
    const workflowId = `custom_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    const customWorkflow = {
      ...workflowData,
      id: workflowId,
      version: workflowData.version || '1.0.0',
      category: workflowData.category || 'custom',
      metadata: {
        ...workflowData.metadata,
        author: workflowData.metadata?.author || 'User',
        created: new Date().toISOString(),
        updated: new Date().toISOString()
      }
    }

    return {
      success: true,
      workflow: customWorkflow,
      warnings: validation.warnings
    }
  }

  /**
   * 克隆工作流模板
   * @param {string} templateId - 模板ID
   * @param {Object} modifications - 修改内容
   * @returns {Object} 克隆结果
   */
  cloneTemplate(templateId, modifications = {}) {
    const template = this.getTemplate(templateId)
    
    if (!template) {
      return {
        success: false,
        error: `模板${templateId}不存在`
      }
    }

    const clonedWorkflow = JSON.parse(JSON.stringify(template))
    
    // 应用修改
    Object.assign(clonedWorkflow, modifications)
    
    // 生成新ID
    clonedWorkflow.id = `cloned_${templateId}_${Date.now()}`
    
    return {
      success: true,
      workflow: clonedWorkflow
    }
  }

  /**
   * 获取工作流统计信息
   * @param {Object} workflow - 工作流定义
   * @returns {Object} 统计信息
   */
  getWorkflowStats(workflow) {
    const stats = {
      totalSteps: workflow.steps?.length || 0,
      requiredSteps: workflow.steps?.filter(step => step.required).length || 0,
      optionalSteps: workflow.steps?.filter(step => step.optional).length || 0,
      estimatedTime: workflow.steps?.reduce((total, step) => total + (step.estimatedTime || 0), 0) || 0,
      dependencies: 0,
      executors: new Set()
    }

    if (workflow.steps) {
      workflow.steps.forEach(step => {
        if (step.dependencies) {
          stats.dependencies += step.dependencies.length
        }
        if (step.executor) {
          stats.executors.add(step.executor)
        }
      })
    }

    stats.executorCount = stats.executors.size
    stats.executors = Array.from(stats.executors)

    return stats
  }
}

export default WorkflowDefinition