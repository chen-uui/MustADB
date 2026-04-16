<template>
  <div class="organic-compounds-display">
    <div v-if="!data || Object.keys(data).length === 0" class="no-data">
      <el-empty description="暂无有机化合物数据" />
    </div>
    
    <div v-else class="data-content">
      <!-- 化合物列表 -->
      <el-card v-if="data.compounds" class="compounds-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>识别的有机化合物</span>
          </div>
        </template>
        
        <div class="compounds-content">
          <el-tag
            v-for="compound in parseCompounds(data.compounds)"
            :key="compound"
            class="compound-tag"
            :type="getCompoundType(compound)"
          >
            {{ compound }}
          </el-tag>
        </div>
      </el-card>

      <!-- 浓度信息 -->
      <el-card v-if="data.concentration" class="concentration-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><PieChart /></el-icon>
            <span>浓度信息</span>
          </div>
        </template>
        
        <div class="concentration-content">
          <el-alert
            :title="data.concentration"
            type="success"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- 检测方法 -->
      <el-card v-if="data.detection_method" class="method-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Tools /></el-icon>
            <span>检测方法</span>
          </div>
        </template>
        
        <div class="method-content">
          <el-tag
            v-for="method in parseMethods(data.detection_method)"
            :key="method"
            class="method-tag"
            type="info"
          >
            {{ method }}
          </el-tag>
        </div>
      </el-card>

      <!-- 分布特征 -->
      <el-card v-if="data.distribution" class="distribution-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Location /></el-icon>
            <span>分布特征</span>
          </div>
        </template>
        
        <div class="distribution-content">
          <p>{{ data.distribution }}</p>
        </div>
      </el-card>

      <!-- 来源分析 -->
      <el-card v-if="data.origin" class="origin-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Search /></el-icon>
            <span>来源分析</span>
          </div>
        </template>
        
        <div class="origin-content">
          <p>{{ data.origin }}</p>
        </div>
      </el-card>

      <!-- 形成机制 -->
      <el-card v-if="data.formation_mechanism" class="mechanism-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Connection /></el-icon>
            <span>形成机制</span>
          </div>
        </template>
        
        <div class="mechanism-content">
          <p>{{ data.formation_mechanism }}</p>
        </div>
      </el-card>

      <!-- 生命起源意义 -->
      <el-card v-if="data.life_origin_significance" class="significance-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Star /></el-icon>
            <span>生命起源意义</span>
          </div>
        </template>
        
        <div class="significance-content">
          <el-alert
            :title="data.life_origin_significance"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- 科学影响 -->
      <el-card v-if="data.scientific_impact" class="impact-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Trophy /></el-icon>
            <span>科学影响</span>
          </div>
        </template>
        
        <div class="impact-content">
          <p>{{ data.scientific_impact }}</p>
        </div>
      </el-card>

      <!-- 分析技术 -->
      <el-card v-if="data.analytical_techniques" class="techniques-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Setting /></el-icon>
            <span>分析技术</span>
          </div>
        </template>
        
        <div class="techniques-content">
          <el-tag
            v-for="technique in parseTechniques(data.analytical_techniques)"
            :key="technique"
            class="technique-tag"
            type="success"
          >
            {{ technique }}
          </el-tag>
        </div>
      </el-card>

      <!-- 环境条件 -->
      <el-card v-if="data.environmental_conditions" class="conditions-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Monitor /></el-icon>
            <span>环境条件</span>
          </div>
        </template>
        
        <div class="conditions-content">
          <el-descriptions :column="2" border>
            <el-descriptions-item
              v-for="(value, key) in parseConditions(data.environmental_conditions)"
              :key="key"
              :label="key"
            >
              {{ value }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { 
  Document, PieChart, Tools, Location, Search, Connection, 
  Star, Trophy, Setting, Monitor 
} from '@element-plus/icons-vue'

// 定义props
const props = defineProps({
  data: {
    type: Object,
    default: () => ({})
  }
})

// 解析化合物列表
const parseCompounds = (compounds) => {
  if (typeof compounds === 'string') {
    return compounds.split(/[,;]/).map(c => c.trim()).filter(c => c)
  }
  return Array.isArray(compounds) ? compounds : []
}

// 解析检测方法
const parseMethods = (methods) => {
  if (typeof methods === 'string') {
    return methods.split(/[,;]/).map(m => m.trim()).filter(m => m)
  }
  return Array.isArray(methods) ? methods : []
}

// 解析分析技术
const parseTechniques = (techniques) => {
  if (typeof techniques === 'string') {
    return techniques.split(/[,;]/).map(t => t.trim()).filter(t => t)
  }
  return Array.isArray(techniques) ? techniques : []
}

// 解析环境条件
const parseConditions = (conditions) => {
  if (typeof conditions === 'string') {
    const conditionsMap = {}
    const parts = conditions.split(/[,;]/)
    
    parts.forEach(part => {
      const trimmed = part.trim()
      if (trimmed) {
        const match = trimmed.match(/([A-Za-z\u4e00-\u9fa5]+)\s*[:\-]\s*([0-9.]+[A-Za-z%]*)/)
        if (match) {
          conditionsMap[match[1]] = match[2]
        } else {
          conditionsMap[trimmed] = '存在'
        }
      }
    })
    
    return conditionsMap
  }
  
  return conditions
}

// 获取化合物类型
const getCompoundType = (compound) => {
  const compoundType = compound.toLowerCase()
  
  if (compoundType.includes('amino') || compoundType.includes('acid')) {
    return 'primary'
  } else if (compoundType.includes('protein') || compoundType.includes('peptide')) {
    return 'success'
  } else if (compoundType.includes('lipid') || compoundType.includes('fatty')) {
    return 'warning'
  } else if (compoundType.includes('carbohydrate') || compoundType.includes('sugar')) {
    return 'info'
  } else if (compoundType.includes('nucleic') || compoundType.includes('dna') || compoundType.includes('rna')) {
    return 'danger'
  } else {
    return 'default'
  }
}
</script>

<style scoped>
.organic-compounds-display {
  padding: 20px;
}

.no-data {
  text-align: center;
  padding: 40px;
}

.data-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.compounds-card,
.concentration-card,
.method-card,
.distribution-card,
.origin-card,
.mechanism-card,
.significance-card,
.impact-card,
.techniques-card,
.conditions-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: bold;
  color: #2c3e50;
}

.compounds-content,
.method-content,
.techniques-content {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.compound-tag,
.method-tag,
.technique-tag {
  margin: 2px;
}

.concentration-content,
.distribution-content,
.origin-content,
.mechanism-content,
.significance-content,
.impact-content {
  line-height: 1.6;
  color: #606266;
}

.conditions-content {
  margin-top: 10px;
}

.el-descriptions {
  margin-top: 10px;
}

.el-descriptions-item {
  padding: 10px;
}

.el-tag {
  margin: 2px;
}

.el-alert {
  margin-top: 10px;
}
</style>
