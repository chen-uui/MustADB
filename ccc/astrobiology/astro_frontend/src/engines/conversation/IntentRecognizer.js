/**
 * 意图识别器
 * 负责识别用户的意图，将自然语言转换为具体的操作意图
 */
class IntentRecognizer {
  constructor() {
    // 意图模式定义
    this.intentPatterns = {
      // 陨石搜索相关意图
      search_meteorite: {
        patterns: [
          /搜索.*陨石/,
          /查找.*陨石/,
          /找.*陨石/,
          /meteorite.*search/i,
          /find.*meteorite/i,
          /陨石.*信息/,
          /陨石.*数据/
        ],
        keywords: ['搜索', '查找', '找', 'search', 'find', '信息', '数据'],
        weight: 0.8
      },
      
      // 文档上传相关意图
      upload_document: {
        patterns: [
          /上传.*文档/,
          /上传.*文件/,
          /上传.*pdf/i,
          /添加.*文档/,
          /添加.*文件/,
          /upload.*document/i,
          /upload.*file/i,
          /add.*document/i
        ],
        keywords: ['上传', '添加', 'upload', 'add', '文档', '文件', 'pdf'],
        weight: 0.8
      },
      
      // 文档分析相关意图
      analyze_document: {
        patterns: [
          /分析.*文档/,
          /分析.*文件/,
          /处理.*文档/,
          /处理.*文件/,
          /analyze.*document/i,
          /process.*document/i,
          /文档.*分析/,
          /文件.*分析/
        ],
        keywords: ['分析', '处理', 'analyze', 'process', '文档', '文件'],
        weight: 0.8
      },
      
      // 数据提取相关意图
      extract_data: {
        patterns: [
          /提取.*数据/,
          /提取.*信息/,
          /数据.*提取/,
          /信息.*提取/,
          /extract.*data/i,
          /extract.*information/i,
          /数据.*挖掘/,
          /信息.*挖掘/
        ],
        keywords: ['提取', 'extract', '数据', '信息', '挖掘'],
        weight: 0.8
      },
      
      // 智能问答相关意图
      intelligent_qa: {
        patterns: [
          /问.*问题/,
          /问.*答/,
          /问答/,
          /问.*什么/,
          /问.*如何/,
          /问.*为什么/,
          /问.*哪里/,
          /问.*什么时候/,
          /问.*谁/,
          /ask.*question/i,
          /what.*is/i,
          /how.*to/i,
          /why.*is/i,
          /where.*is/i,
          /when.*is/i,
          /who.*is/i
        ],
        keywords: ['问', '问题', '问答', 'ask', 'question', 'what', 'how', 'why', 'where', 'when', 'who'],
        weight: 0.7
      },
      
      // 查看结果相关意图
      view_results: {
        patterns: [
          /查看.*结果/,
          /查看.*报告/,
          /显示.*结果/,
          /显示.*报告/,
          /结果.*查看/,
          /报告.*查看/,
          /view.*results/i,
          /show.*results/i,
          /view.*report/i,
          /show.*report/i
        ],
        keywords: ['查看', '显示', 'view', 'show', '结果', '报告', 'results', 'report'],
        weight: 0.8
      },
      
      // 生成报告相关意图
      generate_report: {
        patterns: [
          /生成.*报告/,
          /创建.*报告/,
          /制作.*报告/,
          /报告.*生成/,
          /报告.*创建/,
          /generate.*report/i,
          /create.*report/i,
          /make.*report/i
        ],
        keywords: ['生成', '创建', '制作', 'generate', 'create', 'make', '报告', 'report'],
        weight: 0.8
      },
      
      // 直接处理相关意图
      direct_processing: {
        patterns: [
          /直接.*处理/,
          /直接.*分析/,
          /直接.*提取/,
          /直接.*生成/,
          /direct.*process/i,
          /direct.*analysis/i,
          /direct.*extract/i,
          /direct.*generate/i
        ],
        keywords: ['直接', 'direct', '处理', '分析', '提取', '生成', 'process', 'analysis', 'extract', 'generate'],
        weight: 0.8
      },
      
      // 帮助相关意图
      help: {
        patterns: [
          /帮助/,
          /帮助.*我/,
          /怎么.*用/,
          /如何.*使用/,
          /使用.*方法/,
          /help/i,
          /how.*to.*use/i,
          /usage/i,
          /guide/i
        ],
        keywords: ['帮助', 'help', '怎么', '如何', '使用', '方法', 'guide', 'usage'],
        weight: 0.6
      },
      
      // 状态查询相关意图
      check_status: {
        patterns: [
          /状态/,
          /进度/,
          /进行.*情况/,
          /处理.*状态/,
          /status/i,
          /progress/i,
          /check.*status/i,
          /check.*progress/i
        ],
        keywords: ['状态', '进度', 'status', 'progress', 'check', '情况'],
        weight: 0.6
      }
    }
    
    // 复合意图模式（多个意图组合）
    this.compositeIntentPatterns = {
      meteorite_analysis: {
        intents: ['search_meteorite', 'analyze_document'],
        patterns: [
          /分析.*陨石.*文档/,
          /陨石.*文档.*分析/,
          /analyze.*meteorite.*document/i,
          /meteorite.*document.*analysis/i
        ],
        weight: 0.9
      },
      
      comprehensive_analysis: {
        intents: ['upload_document', 'analyze_document', 'extract_data', 'generate_report'],
        patterns: [
          /全面.*分析/,
          /完整.*分析/,
          /综合分析/,
          /comprehensive.*analysis/i,
          /complete.*analysis/i,
          /full.*analysis/i
        ],
        weight: 0.9
      }
    }
  }

  /**
   * 识别用户意图
   * @param {Object} nluResult - NLU处理结果
   * @returns {Object} 意图识别结果
   */
  async recognize(nluResult) {
    const { normalizedInput, keywords, entities } = nluResult
    
    // 首先检查复合意图
    const compositeIntent = this.recognizeCompositeIntent(normalizedInput)
    if (compositeIntent) {
      return {
        primaryIntent: compositeIntent.name,
        secondaryIntents: compositeIntent.intents,
        confidence: compositeIntent.confidence,
        entities: entities,
        context: this.buildContext(nluResult, compositeIntent.name),
        timestamp: new Date().toISOString()
      }
    }
    
    // 识别单一意图
    const intentScores = this.calculateIntentScores(normalizedInput, keywords, entities)
    const bestIntent = this.selectBestIntent(intentScores)
    
    return {
      primaryIntent: bestIntent.name,
      secondaryIntents: [],
      confidence: bestIntent.confidence,
      entities: entities,
      context: this.buildContext(nluResult, bestIntent.name),
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 识别复合意图
   * @param {string} input - 标准化输入
   * @returns {Object|null} 复合意图结果
   */
  recognizeCompositeIntent(input) {
    for (const [name, pattern] of Object.entries(this.compositeIntentPatterns)) {
      for (const regex of pattern.patterns) {
        if (regex.test(input)) {
          return {
            name,
            intents: pattern.intents,
            confidence: pattern.weight
          }
        }
      }
    }
    return null
  }

  /**
   * 计算意图分数
   * @param {string} input - 标准化输入
   * @param {Object} keywords - 关键词
   * @param {Object} entities - 实体
   * @returns {Array} 意图分数数组
   */
  calculateIntentScores(input, keywords, entities) {
    const scores = []
    
    for (const [intentName, intentConfig] of Object.entries(this.intentPatterns)) {
      let score = 0
      let matchCount = 0
      
      // 模式匹配分数
      for (const pattern of intentConfig.patterns) {
        if (pattern.test(input)) {
          score += intentConfig.weight
          matchCount++
        }
      }
      
      // 关键词匹配分数
      for (const keyword of intentConfig.keywords) {
        if (input.includes(keyword)) {
          score += 0.1
          matchCount++
        }
      }
      
      // 实体匹配分数
      if (this.hasRelevantEntities(intentName, entities)) {
        score += 0.2
        matchCount++
      }
      
      // 计算最终分数
      const finalScore = matchCount > 0 ? score / matchCount : 0
      
      scores.push({
        name: intentName,
        score: finalScore,
        confidence: Math.min(finalScore, 1),
        matchCount
      })
    }
    
    return scores.sort((a, b) => b.score - a.score)
  }

  /**
   * 检查是否有相关实体
   * @param {string} intentName - 意图名称
   * @param {Object} entities - 实体
   * @returns {boolean} 是否有相关实体
   */
  hasRelevantEntities(intentName, entities) {
    switch (intentName) {
      case 'search_meteorite':
        return entities.meteoriteNames.length > 0
      case 'upload_document':
      case 'analyze_document':
        return entities.fileNames.length > 0 || entities.documentTypes.length > 0
      case 'extract_data':
        return entities.numbers.length > 0 || entities.fileNames.length > 0
      default:
        return false
    }
  }

  /**
   * 选择最佳意图
   * @param {Array} scores - 意图分数数组
   * @returns {Object} 最佳意图
   */
  selectBestIntent(scores) {
    if (scores.length === 0) {
      return {
        name: 'unknown',
        confidence: 0
      }
    }
    
    const bestScore = scores[0]
    
    // 如果最佳分数太低，返回未知意图
    if (bestScore.confidence < 0.3) {
      return {
        name: 'unknown',
        confidence: bestScore.confidence
      }
    }
    
    return bestScore
  }

  /**
   * 构建上下文信息
   * @param {Object} nluResult - NLU处理结果
   * @param {string} intent - 意图名称
   * @returns {Object} 上下文信息
   */
  buildContext(nluResult, intent) {
    const context = {
      intent,
      entities: nluResult.entities,
      keywords: nluResult.keywords,
      originalInput: nluResult.originalInput,
      normalizedInput: nluResult.normalizedInput
    }
    
    // 根据意图添加特定上下文
    switch (intent) {
      case 'search_meteorite':
        context.meteoriteName = nluResult.entities.meteoriteNames[0] || null
        context.searchType = this.determineSearchType(nluResult.normalizedInput)
        break
        
      case 'upload_document':
        context.fileName = nluResult.entities.fileNames[0] || null
        context.documentType = this.determineDocumentType(nluResult.normalizedInput)
        break
        
      case 'analyze_document':
        context.analysisType = this.determineAnalysisType(nluResult.normalizedInput)
        context.targetDocument = nluResult.entities.fileNames[0] || null
        break
        
      case 'extract_data':
        context.extractionType = this.determineExtractionType(nluResult.normalizedInput)
        context.targetData = this.determineTargetData(nluResult.normalizedInput)
        break
        
      case 'intelligent_qa':
        context.questionType = this.determineQuestionType(nluResult.normalizedInput)
        context.questionScope = this.determineQuestionScope(nluResult.normalizedInput)
        break
    }
    
    return context
  }

  /**
   * 确定搜索类型
   * @param {string} input - 输入文本
   * @returns {string} 搜索类型
   */
  determineSearchType(input) {
    if (input.includes('基本信息') || input.includes('basic')) return 'basic'
    if (input.includes('详细') || input.includes('detailed')) return 'detailed'
    if (input.includes('全部') || input.includes('all')) return 'comprehensive'
    return 'basic'
  }

  /**
   * 确定文档类型
   * @param {string} input - 输入文本
   * @returns {string} 文档类型
   */
  determineDocumentType(input) {
    if (input.includes('pdf')) return 'pdf'
    if (input.includes('doc')) return 'doc'
    if (input.includes('txt')) return 'txt'
    return 'unknown'
  }

  /**
   * 确定分析类型
   * @param {string} input - 输入文本
   * @returns {string} 分析类型
   */
  determineAnalysisType(input) {
    if (input.includes('内容') || input.includes('content')) return 'content'
    if (input.includes('结构') || input.includes('structure')) return 'structure'
    if (input.includes('语义') || input.includes('semantic')) return 'semantic'
    return 'comprehensive'
  }

  /**
   * 确定提取类型
   * @param {string} input - 输入文本
   * @returns {string} 提取类型
   */
  determineExtractionType(input) {
    if (input.includes('矿物') || input.includes('mineral')) return 'mineral'
    if (input.includes('有机') || input.includes('organic')) return 'organic'
    if (input.includes('元素') || input.includes('element')) return 'element'
    return 'comprehensive'
  }

  /**
   * 确定目标数据
   * @param {string} input - 输入文本
   * @returns {Array} 目标数据列表
   */
  determineTargetData(input) {
    const targets = []
    if (input.includes('矿物') || input.includes('mineral')) targets.push('minerals')
    if (input.includes('有机') || input.includes('organic')) targets.push('organic_compounds')
    if (input.includes('元素') || input.includes('element')) targets.push('elements')
    if (input.includes('同位素') || input.includes('isotope')) targets.push('isotopes')
    return targets.length > 0 ? targets : ['all']
  }

  /**
   * 确定问题类型
   * @param {string} input - 输入文本
   * @returns {string} 问题类型
   */
  determineQuestionType(input) {
    if (input.includes('什么') || input.includes('what')) return 'what'
    if (input.includes('如何') || input.includes('how')) return 'how'
    if (input.includes('为什么') || input.includes('why')) return 'why'
    if (input.includes('哪里') || input.includes('where')) return 'where'
    if (input.includes('什么时候') || input.includes('when')) return 'when'
    if (input.includes('谁') || input.includes('who')) return 'who'
    return 'general'
  }

  /**
   * 确定问题范围
   * @param {string} input - 输入文本
   * @returns {string} 问题范围
   */
  determineQuestionScope(input) {
    if (input.includes('陨石') || input.includes('meteorite')) return 'meteorite'
    if (input.includes('文档') || input.includes('document')) return 'document'
    if (input.includes('数据') || input.includes('data')) return 'data'
    return 'general'
  }
}

export default IntentRecognizer