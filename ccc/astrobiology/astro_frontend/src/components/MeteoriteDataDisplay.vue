<template>
  <div class="meteorite-data-display">
    <div v-if="!data || Object.keys(data).length === 0" class="no-data">
      <el-empty description="暂无陨石数据" />
    </div>
    
    <div v-else class="data-content">
      <!-- 基本信息 -->
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><InfoFilled /></el-icon>
            <span>基本信息</span>
          </div>
        </template>
        
        <el-descriptions :column="2" border>
          <el-descriptions-item label="陨石名称" v-if="data.name">
            <el-tag type="primary">{{ data.name }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="分类" v-if="data.classification">
            <el-tag type="success">{{ data.classification }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="发现地点" v-if="data.location">
            {{ data.location }}
          </el-descriptions-item>
          <el-descriptions-item label="发现日期" v-if="data.date">
            {{ data.date }}
          </el-descriptions-item>
          <el-descriptions-item label="重量" v-if="data.weight">
            {{ data.weight }}
          </el-descriptions-item>
          <el-descriptions-item label="形成年龄" v-if="data.age">
            {{ data.age }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 化学成分 -->
      <el-card v-if="data.composition" class="composition-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>化学成分</span>
          </div>
        </template>
        
        <div class="composition-content">
          <el-tag
            v-for="(value, key) in parseComposition(data.composition)"
            :key="key"
            class="composition-tag"
            type="info"
          >
            {{ key }}: {{ value }}
          </el-tag>
        </div>
      </el-card>

      <!-- 物理性质 -->
      <el-card v-if="data.physical_properties" class="properties-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Setting /></el-icon>
            <span>物理性质</span>
          </div>
        </template>
        
        <div class="properties-content">
          <el-tag
            v-for="(value, key) in parseProperties(data.physical_properties)"
            :key="key"
            class="property-tag"
            type="warning"
          >
            {{ key }}: {{ value }}
          </el-tag>
        </div>
      </el-card>

      <!-- 来源信息 -->
      <el-card v-if="data.origin" class="origin-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Location /></el-icon>
            <span>来源信息</span>
          </div>
        </template>
        
        <div class="origin-content">
          <p>{{ data.origin }}</p>
        </div>
      </el-card>

      <!-- 特殊特征 -->
      <el-card v-if="data.special_features" class="features-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Star /></el-icon>
            <span>特殊特征</span>
          </div>
        </template>
        
        <div class="features-content">
          <el-alert
            :title="data.special_features"
            type="info"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- 科学意义 -->
      <el-card v-if="data.scientific_significance" class="significance-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Trophy /></el-icon>
            <span>科学意义</span>
          </div>
        </template>
        
        <div class="significance-content">
          <p>{{ data.scientific_significance }}</p>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { InfoFilled, Document, Setting, Location, Star, Trophy } from '@element-plus/icons-vue'

// 定义props
const props = defineProps({
  data: {
    type: Object,
    default: () => ({})
  }
})

// 解析化学成分
const parseComposition = (composition) => {
  if (typeof composition === 'string') {
    // 尝试解析字符串格式的化学成分
    const compositionMap = {}
    const parts = composition.split(/[,;]/)
    
    parts.forEach(part => {
      const trimmed = part.trim()
      if (trimmed) {
        // 尝试提取元素和含量
        const match = trimmed.match(/([A-Za-z]+)\s*[:\-]\s*([0-9.]+%?)/)
        if (match) {
          compositionMap[match[1]] = match[2]
        } else {
          compositionMap[trimmed] = '存在'
        }
      }
    })
    
    return compositionMap
  }
  
  return composition
}

// 解析物理性质
const parseProperties = (properties) => {
  if (typeof properties === 'string') {
    const propertiesMap = {}
    const parts = properties.split(/[,;]/)
    
    parts.forEach(part => {
      const trimmed = part.trim()
      if (trimmed) {
        const match = trimmed.match(/([A-Za-z\u4e00-\u9fa5]+)\s*[:\-]\s*([0-9.]+[A-Za-z%]*)/)
        if (match) {
          propertiesMap[match[1]] = match[2]
        } else {
          propertiesMap[trimmed] = '存在'
        }
      }
    })
    
    return propertiesMap
  }
  
  return properties
}
</script>

<style scoped>
.meteorite-data-display {
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

.info-card,
.composition-card,
.properties-card,
.origin-card,
.features-card,
.significance-card {
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

.composition-content,
.properties-content {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.composition-tag,
.property-tag {
  margin: 2px;
}

.origin-content,
.significance-content {
  line-height: 1.6;
  color: #606266;
}

.features-content {
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
</style>
