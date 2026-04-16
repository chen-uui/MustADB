/**
 * 实体提取器
 * 负责从用户输入中提取具体的实体信息
 */
class EntityExtractor {
  constructor() {
    // 陨石名称数据库
    this.meteoriteNames = new Set([
      'Allende', 'Murchison', 'Murray', 'Orgueil', 'Tagish Lake', 'Ivuna', 'Alais',
      'Cold Bokkeveld', 'Mighei', 'Nogoya', 'Revelstoke', 'Tonk', 'Vigarano',
      'Warrenton', 'Y-791717', 'Y-793321', 'Y-82094', 'Y-82162', 'Y-86029',
      'Y-86720', 'Y-86789', 'Y-9002', 'Y-980115', 'Y-980223', 'Y-980425',
      'Y-980459', 'Y-980480', 'Y-980489', 'Y-980493', 'Y-980500', 'Y-980520',
      'Y-980523', 'Y-980524', 'Y-980525', 'Y-980526', 'Y-980527', 'Y-980528',
      'Y-980529', 'Y-980530', 'Y-980531', 'Y-980532', 'Y-980533', 'Y-980534',
      'Y-980535', 'Y-980536', 'Y-980537', 'Y-980538', 'Y-980539', 'Y-980540'
    ])
    
    // 陨石分类
    this.meteoriteTypes = new Set([
      'CI', 'CM', 'CV', 'CO', 'CR', 'CH', 'CB', 'CK', 'CR2', 'CM2', 'CV3',
      'CO3', 'CR3', 'CH3', 'CB3', 'CK3', 'CR1', 'CM1', 'CV1', 'CO1',
      '普通球粒陨石', '碳质球粒陨石', '顽火辉石球粒陨石', '铁陨石', '石铁陨石',
      '无球粒陨石', '月球陨石', '火星陨石'
    ])
    
    // 矿物名称
    this.minerals = new Set([
      '橄榄石', 'olivine', '辉石', 'pyroxene', '长石', 'feldspar', '石英', 'quartz',
      '方解石', 'calcite', '白云石', 'dolomite', '黄铁矿', 'pyrite', '磁铁矿', 'magnetite',
      '赤铁矿', 'hematite', '针铁矿', 'goethite', '高岭石', 'kaolinite', '蒙脱石', 'montmorillonite',
      '伊利石', 'illite', '绿泥石', 'chlorite', '蛇纹石', 'serpentine', '滑石', 'talc',
      '石膏', 'gypsum', '硬石膏', 'anhydrite', '重晶石', 'barite', '萤石', 'fluorite'
    ])
    
    // 有机化合物
    this.organicCompounds = new Set([
      '氨基酸', 'amino acid', '甘氨酸', 'glycine', '丙氨酸', 'alanine', '谷氨酸', 'glutamic acid',
      '天冬氨酸', 'aspartic acid', '丝氨酸', 'serine', '缬氨酸', 'valine', '脯氨酸', 'proline',
      '多环芳烃', 'PAH', 'polycyclic aromatic hydrocarbon', '脂肪族化合物', 'aliphatic compound',
      '芳香族化合物', 'aromatic compound', '酮', 'ketone', '醛', 'aldehyde', '醇', 'alcohol',
      '酸', 'acid', '酯', 'ester', '醚', 'ether', '胺', 'amine', '酰胺', 'amide'
    ])
    
    // 元素名称
    this.elements = new Set([
      '氢', 'H', '氢', 'helium', 'He', '锂', 'lithium', 'Li', '铍', 'beryllium', 'Be',
      '硼', 'boron', 'B', '碳', 'carbon', 'C', '氮', 'nitrogen', 'N', '氧', 'oxygen', 'O',
      '氟', 'fluorine', 'F', '氖', 'neon', 'Ne', '钠', 'sodium', 'Na', '镁', 'magnesium', 'Mg',
      '铝', 'aluminum', 'Al', '硅', 'silicon', 'Si', '磷', 'phosphorus', 'P', '硫', 'sulfur', 'S',
      '氯', 'chlorine', 'Cl', '氩', 'argon', 'Ar', '钾', 'potassium', 'K', '钙', 'calcium', 'Ca',
      '钛', 'titanium', 'Ti', '钒', 'vanadium', 'V', '铬', 'chromium', 'Cr', '锰', 'manganese', 'Mn',
      '铁', 'iron', 'Fe', '钴', 'cobalt', 'Co', '镍', 'nickel', 'Ni', '铜', 'copper', 'Cu',
      '锌', 'zinc', 'Zn', '镓', 'gallium', 'Ga', '锗', 'germanium', 'Ge', '砷', 'arsenic', 'As',
      '硒', 'selenium', 'Se', '溴', 'bromine', 'Br', '氪', 'krypton', 'Kr', '铷', 'rubidium', 'Rb',
      '锶', 'strontium', 'Sr', '钇', 'yttrium', 'Y', '锆', 'zirconium', 'Zr', '铌', 'niobium', 'Nb',
      '钼', 'molybdenum', 'Mo', '锝', 'technetium', 'Tc', '钌', 'ruthenium', 'Ru', '铑', 'rhodium', 'Rh',
      '钯', 'palladium', 'Pd', '银', 'silver', 'Ag', '镉', 'cadmium', 'Cd', '铟', 'indium', 'In',
      '锡', 'tin', 'Sn', '锑', 'antimony', 'Sb', '碲', 'tellurium', 'Te', '碘', 'iodine', 'I',
      '氙', 'xenon', 'Xe', '铯', 'cesium', 'Cs', '钡', 'barium', 'Ba', '镧', 'lanthanum', 'La',
      '铈', 'cerium', 'Ce', '镨', 'praseodymium', 'Pr', '钕', 'neodymium', 'Nd', '钷', 'promethium', 'Pm',
      '钐', 'samarium', 'Sm', '铕', 'europium', 'Eu', '钆', 'gadolinium', 'Gd', '铽', 'terbium', 'Tb',
      '镝', 'dysprosium', 'Dy', '钬', 'holmium', 'Ho', '铒', 'erbium', 'Er', '铥', 'thulium', 'Tm',
      '镱', 'ytterbium', 'Yb', '镥', 'lutetium', 'Lu', '铪', 'hafnium', 'Hf', '钽', 'tantalum', 'Ta',
      '钨', 'tungsten', 'W', '铼', 'rhenium', 'Re', '锇', 'osmium', 'Os', '铱', 'iridium', 'Ir',
      '铂', 'platinum', 'Pt', '金', 'gold', 'Au', '汞', 'mercury', 'Hg', '铊', 'thallium', 'Tl',
      '铅', 'lead', 'Pb', '铋', 'bismuth', 'Bi', '钋', 'polonium', 'Po', '砹', 'astatine', 'At',
      '氡', 'radon', 'Rn', '钫', 'francium', 'Fr', '镭', 'radium', 'Ra', '锕', 'actinium', 'Ac',
      '钍', 'thorium', 'Th', '镤', 'protactinium', 'Pa', '铀', 'uranium', 'U', '镎', 'neptunium', 'Np',
      '钚', 'plutonium', 'Pu', '镅', 'americium', 'Am', '锔', 'curium', 'Cm', '锫', 'berkelium', 'Bk',
      '锎', 'californium', 'Cf', '锿', 'einsteinium', 'Es', '镄', 'fermium', 'Fm', '钔', 'mendelevium', 'Md',
      '锘', 'nobelium', 'No', '铹', 'lawrencium', 'Lr'
    ])
    
    // 文件扩展名
    this.fileExtensions = new Set([
      'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt', 'pages', 'xls', 'xlsx', 'csv',
      'ppt', 'pptx', 'key', 'odp', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff',
      'svg', 'eps', 'ai', 'psd', 'zip', 'rar', '7z', 'tar', 'gz'
    ])
    
    // 单位
    this.units = new Set([
      'mg', 'g', 'kg', 'μg', 'ng', 'pg', 'fg', 'ag', 'mol', 'mmol', 'μmol', 'nmol',
      'pmol', 'fmol', 'amol', 'L', 'mL', 'μL', 'nL', 'pL', 'fL', 'aL', 'm', 'cm',
      'mm', 'μm', 'nm', 'pm', 'fm', 'am', 'K', '°C', '°F', 'Pa', 'kPa', 'MPa', 'GPa',
      'atm', 'bar', 'mbar', 'μbar', 'nbar', 'pbar', 'fbar', 'abar', 'Hz', 'kHz',
      'MHz', 'GHz', 'THz', 'PHz', 'EHz', 'ZHz', 'YHz', 'J', 'kJ', 'MJ', 'GJ', 'TJ',
      'PJ', 'EJ', 'ZJ', 'YJ', 'W', 'kW', 'MW', 'GW', 'TW', 'PW', 'EW', 'ZW', 'YW',
      'V', 'kV', 'MV', 'GV', 'TV', 'PV', 'EV', 'ZV', 'YV', 'A', 'mA', 'μA', 'nA',
      'pA', 'fA', 'aA', 'Ω', 'kΩ', 'MΩ', 'GΩ', 'TΩ', 'PΩ', 'EΩ', 'ZΩ', 'YΩ'
    ])
  }

  /**
   * 提取实体
   * @param {Object} nluResult - NLU处理结果
   * @returns {Object} 提取的实体
   */
  async extract(nluResult) {
    const { normalizedInput, tokens } = nluResult
    
    const entities = {
      meteoriteNames: this.extractMeteoriteNames(normalizedInput, tokens),
      meteoriteTypes: this.extractMeteoriteTypes(normalizedInput, tokens),
      minerals: this.extractMinerals(normalizedInput, tokens),
      organicCompounds: this.extractOrganicCompounds(normalizedInput, tokens),
      elements: this.extractElements(normalizedInput, tokens),
      fileNames: this.extractFileNames(normalizedInput),
      fileExtensions: this.extractFileExtensions(normalizedInput),
      numbers: this.extractNumbers(normalizedInput),
      units: this.extractUnits(normalizedInput, tokens),
      dates: this.extractDates(normalizedInput),
      locations: this.extractLocations(normalizedInput, tokens),
      percentages: this.extractPercentages(normalizedInput),
      concentrations: this.extractConcentrations(normalizedInput),
      temperatures: this.extractTemperatures(normalizedInput),
      pressures: this.extractPressures(normalizedInput)
    }
    
    return entities
  }

  /**
   * 提取陨石名称
   * @param {string} input - 输入文本
   * @param {Array} tokens - 分词结果
   * @returns {Array} 陨石名称列表
   */
  extractMeteoriteNames(input, tokens) {
    const names = []
    
    // 检查完整匹配
    for (const name of this.meteoriteNames) {
      if (input.includes(name.toLowerCase())) {
        names.push(name)
      }
    }
    
    // 检查部分匹配
    for (const token of tokens) {
      for (const name of this.meteoriteNames) {
        if (name.toLowerCase().includes(token) || token.includes(name.toLowerCase())) {
          if (!names.includes(name)) {
            names.push(name)
          }
        }
      }
    }
    
    return [...new Set(names)]
  }

  /**
   * 提取陨石类型
   * @param {string} input - 输入文本
   * @param {Array} tokens - 分词结果
   * @returns {Array} 陨石类型列表
   */
  extractMeteoriteTypes(input, tokens) {
    const types = []
    
    for (const type of this.meteoriteTypes) {
      if (input.includes(type.toLowerCase())) {
        types.push(type)
      }
    }
    
    return [...new Set(types)]
  }

  /**
   * 提取矿物名称
   * @param {string} input - 输入文本
   * @param {Array} tokens - 分词结果
   * @returns {Array} 矿物名称列表
   */
  extractMinerals(input, tokens) {
    const minerals = []
    
    for (const mineral of this.minerals) {
      if (input.includes(mineral.toLowerCase())) {
        minerals.push(mineral)
      }
    }
    
    return [...new Set(minerals)]
  }

  /**
   * 提取有机化合物
   * @param {string} input - 输入文本
   * @param {Array} tokens - 分词结果
   * @returns {Array} 有机化合物列表
   */
  extractOrganicCompounds(input, tokens) {
    const compounds = []
    
    for (const compound of this.organicCompounds) {
      if (input.includes(compound.toLowerCase())) {
        compounds.push(compound)
      }
    }
    
    return [...new Set(compounds)]
  }

  /**
   * 提取元素
   * @param {string} input - 输入文本
   * @param {Array} tokens - 分词结果
   * @returns {Array} 元素列表
   */
  extractElements(input, tokens) {
    const elements = []
    
    for (const element of this.elements) {
      if (input.includes(element.toLowerCase())) {
        elements.push(element)
      }
    }
    
    return [...new Set(elements)]
  }

  /**
   * 提取文件名
   * @param {string} input - 输入文本
   * @returns {Array} 文件名列表
   */
  extractFileNames(input) {
    const fileNames = []
    
    // 匹配文件名模式
    const patterns = [
      /([a-zA-Z0-9_-]+\.(pdf|doc|docx|txt|rtf|odt|pages|xls|xlsx|csv|ppt|pptx|key|odp))/gi,
      /([a-zA-Z0-9_-]+\.(jpg|jpeg|png|gif|bmp|tiff|svg|eps|ai|psd))/gi,
      /([a-zA-Z0-9_-]+\.(zip|rar|7z|tar|gz))/gi
    ]
    
    for (const pattern of patterns) {
      const matches = input.match(pattern)
      if (matches) {
        fileNames.push(...matches)
      }
    }
    
    return [...new Set(fileNames)]
  }

  /**
   * 提取文件扩展名
   * @param {string} input - 输入文本
   * @returns {Array} 文件扩展名列表
   */
  extractFileExtensions(input) {
    const extensions = []
    
    for (const ext of this.fileExtensions) {
      if (input.includes(`.${ext}`)) {
        extensions.push(ext)
      }
    }
    
    return [...new Set(extensions)]
  }

  /**
   * 提取数字
   * @param {string} input - 输入文本
   * @returns {Array} 数字列表
   */
  extractNumbers(input) {
    const numbers = []
    
    // 匹配整数和小数
    const numberPattern = /-?\d+(\.\d+)?([eE][+-]?\d+)?/g
    const matches = input.match(numberPattern)
    
    if (matches) {
      numbers.push(...matches.map(n => parseFloat(n)))
    }
    
    return numbers
  }

  /**
   * 提取单位
   * @param {string} input - 输入文本
   * @param {Array} tokens - 分词结果
   * @returns {Array} 单位列表
   */
  extractUnits(input, tokens) {
    const units = []
    
    for (const unit of this.units) {
      if (input.includes(unit)) {
        units.push(unit)
      }
    }
    
    return [...new Set(units)]
  }

  /**
   * 提取日期
   * @param {string} input - 输入文本
   * @returns {Array} 日期列表
   */
  extractDates(input) {
    const dates = []
    
    // 匹配各种日期格式
    const patterns = [
      /\d{4}[-/]\d{1,2}[-/]\d{1,2}/g,  // YYYY-MM-DD
      /\d{1,2}[-/]\d{1,2}[-/]\d{4}/g,  // MM-DD-YYYY
      /\d{4}年\d{1,2}月\d{1,2}日/g,     // YYYY年MM月DD日
      /\d{1,2}月\d{1,2}日/g,            // MM月DD日
      /\d{4}年/g                        // YYYY年
    ]
    
    for (const pattern of patterns) {
      const matches = input.match(pattern)
      if (matches) {
        dates.push(...matches)
      }
    }
    
    return [...new Set(dates)]
  }

  /**
   * 提取地点
   * @param {string} input - 输入文本
   * @param {Array} tokens - 分词结果
   * @returns {Array} 地点列表
   */
  extractLocations(input, tokens) {
    const locations = []
    
    // 简单的地点识别（可以扩展）
    const locationKeywords = [
      '南极', 'antarctica', '沙漠', 'desert', '海洋', 'ocean', '山脉', 'mountain',
      '平原', 'plain', '高原', 'plateau', '盆地', 'basin', '山谷', 'valley',
      '中国', 'china', '美国', 'usa', '俄罗斯', 'russia', '日本', 'japan',
      '澳大利亚', 'australia', '加拿大', 'canada', '巴西', 'brazil', '印度', 'india'
    ]
    
    for (const location of locationKeywords) {
      if (input.includes(location.toLowerCase())) {
        locations.push(location)
      }
    }
    
    return [...new Set(locations)]
  }

  /**
   * 提取百分比
   * @param {string} input - 输入文本
   * @returns {Array} 百分比列表
   */
  extractPercentages(input) {
    const percentages = []
    
    // 匹配百分比模式
    const patterns = [
      /\d+(\.\d+)?%/g,                    // 数字%
      /\d+(\.\d+)?\s*percent/g,           // 数字 percent
      /\d+(\.\d+)?\s*百分比/g             // 数字 百分比
    ]
    
    for (const pattern of patterns) {
      const matches = input.match(pattern)
      if (matches) {
        percentages.push(...matches)
      }
    }
    
    return [...new Set(percentages)]
  }

  /**
   * 提取浓度
   * @param {string} input - 输入文本
   * @returns {Array} 浓度列表
   */
  extractConcentrations(input) {
    const concentrations = []
    
    // 匹配浓度模式
    const patterns = [
      /\d+(\.\d+)?\s*(mg|g|kg|μg|ng|pg|fg|ag)\s*\/\s*(L|mL|μL|nL|pL|fL|aL)/g,
      /\d+(\.\d+)?\s*(mol|mmol|μmol|nmol|pmol|fmol|amol)\s*\/\s*(L|mL|μL|nL|pL|fL|aL)/g,
      /\d+(\.\d+)?\s*(ppm|ppb|ppt|ppq)/g
    ]
    
    for (const pattern of patterns) {
      const matches = input.match(pattern)
      if (matches) {
        concentrations.push(...matches)
      }
    }
    
    return [...new Set(concentrations)]
  }

  /**
   * 提取温度
   * @param {string} input - 输入文本
   * @returns {Array} 温度列表
   */
  extractTemperatures(input) {
    const temperatures = []
    
    // 匹配温度模式
    const patterns = [
      /\d+(\.\d+)?\s*°?[CKF]/g,          // 数字°C/K/F
      /\d+(\.\d+)?\s*(celsius|fahrenheit|kelvin)/g,  // 数字 celsius/fahrenheit/kelvin
      /\d+(\.\d+)?\s*(度|摄氏度|华氏度|开尔文)/g      // 数字 度/摄氏度/华氏度/开尔文
    ]
    
    for (const pattern of patterns) {
      const matches = input.match(pattern)
      if (matches) {
        temperatures.push(...matches)
      }
    }
    
    return [...new Set(temperatures)]
  }

  /**
   * 提取压力
   * @param {string} input - 输入文本
   * @returns {Array} 压力列表
   */
  extractPressures(input) {
    const pressures = []
    
    // 匹配压力模式
    const patterns = [
      /\d+(\.\d+)?\s*(Pa|kPa|MPa|GPa|atm|bar|mbar|μbar|nbar|pbar|fbar|abar)/g,
      /\d+(\.\d+)?\s*(帕|千帕|兆帕|吉帕|大气压|巴|毫巴|微巴|纳巴|皮巴|飞巴|阿巴)/g
    ]
    
    for (const pattern of patterns) {
      const matches = input.match(pattern)
      if (matches) {
        pressures.push(...matches)
      }
    }
    
    return [...new Set(pressures)]
  }
}

export default EntityExtractor