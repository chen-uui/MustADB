/**
 * 自然语言理解处理器
 * 负责处理用户输入的自然语言，进行分词、词性标注等基础处理
 */
class NLUProcessor {
  constructor() {
    this.stopWords = new Set([
      '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'
    ])
    
    // 陨石相关关键词
    this.meteoriteKeywords = [
      '陨石', 'meteorite', '球粒陨石', '碳质球粒陨石', '普通球粒陨石', '铁陨石', '石铁陨石',
      'Allende', 'Murchison', 'Murray', 'Orgueil', 'Tagish Lake', 'CI', 'CM', 'CV', 'CO', 'CR', 'CH', 'CB'
    ]
    
    // 文档相关关键词
    this.documentKeywords = [
      '文档', 'PDF', '文件', '上传', '分析', '处理', '提取', '数据', '内容', '报告'
    ]
    
    // 操作相关关键词
    this.actionKeywords = [
      '搜索', '查找', '分析', '处理', '提取', '生成', '查看', '显示', '上传', '下载', '保存'
    ]
  }

  /**
   * 处理用户输入
   * @param {string} input - 用户输入的自然语言
   * @returns {Object} NLU处理结果
   */
  async process(input) {
    if (!input || typeof input !== 'string') {
      throw new Error('输入必须是非空字符串')
    }

    const normalizedInput = this.normalizeInput(input)
    const tokens = this.tokenize(normalizedInput)
    const keywords = this.extractKeywords(tokens)
    const entities = this.extractEntities(normalizedInput, tokens)
    
    return {
      originalInput: input,
      normalizedInput,
      tokens,
      keywords,
      entities,
      confidence: this.calculateConfidence(keywords, entities),
      timestamp: new Date().toISOString()
    }
  }

  /**
   * 标准化输入
   * @param {string} input - 原始输入
   * @returns {string} 标准化后的输入
   */
  normalizeInput(input) {
    return input
      .trim()
      .toLowerCase()
      .replace(/[，。！？；：""''（）【】]/g, ' ') // 移除中文标点
      .replace(/[^\w\s\u4e00-\u9fff]/g, ' ') // 保留字母、数字、空格和中文
      .replace(/\s+/g, ' ') // 合并多个空格
      .trim()
  }

  /**
   * 分词处理
   * @param {string} text - 标准化后的文本
   * @returns {Array} 分词结果
   */
  tokenize(text) {
    // 简单的分词实现，实际项目中可以使用更专业的分词库
    const tokens = []
    
    // 按空格分割
    const words = text.split(/\s+/)
    
    for (const word of words) {
      if (word.length > 0) {
        // 进一步分割中文词汇
        const chineseTokens = this.splitChineseWord(word)
        tokens.push(...chineseTokens)
      }
    }
    
    return tokens.filter(token => token.length > 0 && !this.stopWords.has(token))
  }

  /**
   * 分割中文词汇
   * @param {string} word - 词汇
   * @returns {Array} 分割后的词汇数组
   */
  splitChineseWord(word) {
    const tokens = []
    
    // 检查是否包含陨石关键词
    for (const keyword of this.meteoriteKeywords) {
      if (word.includes(keyword)) {
        const index = word.indexOf(keyword)
        if (index > 0) {
          tokens.push(word.substring(0, index))
        }
        tokens.push(keyword)
        if (index + keyword.length < word.length) {
          tokens.push(word.substring(index + keyword.length))
        }
        return tokens
      }
    }
    
    // 如果没有匹配到关键词，返回原词
    tokens.push(word)
    return tokens
  }

  /**
   * 提取关键词
   * @param {Array} tokens - 分词结果
   * @returns {Object} 关键词分类
   */
  extractKeywords(tokens) {
    const keywords = {
      meteorite: [],
      document: [],
      action: [],
      other: []
    }

    for (const token of tokens) {
      if (this.meteoriteKeywords.some(keyword => token.includes(keyword))) {
        keywords.meteorite.push(token)
      } else if (this.documentKeywords.some(keyword => token.includes(keyword))) {
        keywords.document.push(token)
      } else if (this.actionKeywords.some(keyword => token.includes(keyword))) {
        keywords.action.push(token)
      } else {
        keywords.other.push(token)
      }
    }

    return keywords
  }

  /**
   * 实体提取
   * @param {string} text - 原始文本
   * @param {Array} tokens - 分词结果
   * @returns {Object} 提取的实体
   */
  extractEntities(text, tokens) {
    const entities = {
      meteoriteNames: [],
      documentTypes: [],
      fileNames: [],
      numbers: [],
      dates: [],
      locations: []
    }

    // 提取陨石名称
    for (const keyword of this.meteoriteKeywords) {
      if (text.includes(keyword)) {
        entities.meteoriteNames.push(keyword)
      }
    }

    // 提取文件名（简单模式匹配）
    const fileNamePattern = /([a-zA-Z0-9_-]+\.(pdf|doc|docx|txt))/gi
    const fileNameMatches = text.match(fileNamePattern)
    if (fileNameMatches) {
      entities.fileNames.push(...fileNameMatches)
    }

    // 提取数字
    const numberPattern = /\d+(\.\d+)?/g
    const numberMatches = text.match(numberPattern)
    if (numberMatches) {
      entities.numbers.push(...numberMatches.map(n => parseFloat(n)))
    }

    // 提取日期
    const datePattern = /(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})/g
    const dateMatches = text.match(datePattern)
    if (dateMatches) {
      entities.dates.push(...dateMatches)
    }

    return entities
  }

  /**
   * 计算置信度
   * @param {Object} keywords - 关键词
   * @param {Object} entities - 实体
   * @returns {number} 置信度分数 (0-1)
   */
  calculateConfidence(keywords, entities) {
    let score = 0
    let totalWeight = 0

    // 陨石关键词权重
    if (keywords.meteorite.length > 0) {
      score += keywords.meteorite.length * 0.3
      totalWeight += keywords.meteorite.length * 0.3
    }

    // 文档关键词权重
    if (keywords.document.length > 0) {
      score += keywords.document.length * 0.2
      totalWeight += keywords.document.length * 0.2
    }

    // 操作关键词权重
    if (keywords.action.length > 0) {
      score += keywords.action.length * 0.25
      totalWeight += keywords.action.length * 0.25
    }

    // 实体权重
    if (entities.meteoriteNames.length > 0) {
      score += entities.meteoriteNames.length * 0.15
      totalWeight += entities.meteoriteNames.length * 0.15
    }

    if (entities.fileNames.length > 0) {
      score += entities.fileNames.length * 0.1
      totalWeight += entities.fileNames.length * 0.1
    }

    return totalWeight > 0 ? Math.min(score / totalWeight, 1) : 0
  }
}

export default NLUProcessor