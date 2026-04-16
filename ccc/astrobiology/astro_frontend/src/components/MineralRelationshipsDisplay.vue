<template>
  <div class="mineral-relationships-display">
    <div v-if="!data || Object.keys(data).length === 0" class="no-data">
      <el-empty description="暂无矿物关系数据" />
    </div>
    
    <div v-else class="data-content">
      <!-- 矿物种类 -->
      <el-card v-if="data.minerals" class="minerals-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>矿物种类</span>
          </div>
        </template>
        
        <div class="minerals-content">
          <el-tag
            v-for="mineral in parseMinerals(data.minerals)"
            :key="mineral"
            class="mineral-tag"
            :type="getMineralType(mineral)"
          >
            {{ mineral }}
          </el-tag>
        </div>
      </el-card>

      <!-- 矿物关系 -->
      <el-card v-if="data.relationships" class="relationships-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Connection /></el-icon>
            <span>矿物关系</span>
          </div>
        </template>
        
        <div class="relationships-content">
          <p>{{ data.relationships }}</p>
        </div>
      </el-card>

      <!-- 相互作用机制 -->
      <el-card v-if="data.interactions" class="interactions-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Setting /></el-icon>
            <span>相互作用机制</span>
          </div>
        </template>
        
        <div class="interactions-content">
          <el-tag
            v-for="interaction in parseInteractions(data.interactions)"
            :key="interaction"
            class="interaction-tag"
            type="warning"
          >
            {{ interaction }}
          </el-tag>
        </div>
      </el-card>

      <!-- 矿物-有机质关系 -->
      <el-card v-if="data.organic_mineral_relations" class="organic-mineral-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Star /></el-icon>
            <span>矿物-有机质关系</span>
          </div>
        </template>
        
        <div class="organic-mineral-content">
          <el-alert
            :title="data.organic_mineral_relations"
            type="info"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- 催化作用 -->
      <el-card v-if="data.catalysis" class="catalysis-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Tools /></el-icon>
            <span>催化作用</span>
          </div>
        </template>
        
        <div class="catalysis-content">
          <p>{{ data.catalysis }}</p>
        </div>
      </el-card>

      <!-- 保护机制 -->
      <el-card v-if="data.protection" class="protection-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Shield /></el-icon>
            <span>保护机制</span>
          </div>
        </template>
        
        <div class="protection-content">
          <p>{{ data.protection }}</p>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { 
  Document, Connection, Setting, Star, Tools, Shield 
} from '@element-plus/icons-vue'

// 定义props
const props = defineProps({
  data: {
    type: Object,
    default: () => ({})
  }
})

// 解析矿物列表
const parseMinerals = (minerals) => {
  if (typeof minerals === 'string') {
    return minerals.split(/[,;]/).map(m => m.trim()).filter(m => m)
  }
  return Array.isArray(minerals) ? minerals : []
}

// 解析相互作用
const parseInteractions = (interactions) => {
  if (typeof interactions === 'string') {
    return interactions.split(/[,;]/).map(i => i.trim()).filter(i => i)
  }
  return Array.isArray(interactions) ? interactions : []
}

// 获取矿物类型
const getMineralType = (mineral) => {
  const mineralType = mineral.toLowerCase()
  
  // 硅酸盐矿物
  if (mineralType.includes('olivine') || mineralType.includes('橄榄石') ||
      mineralType.includes('pyroxene') || mineralType.includes('辉石') ||
      mineralType.includes('plagioclase') || mineralType.includes('长石') ||
      mineralType.includes('quartz') || mineralType.includes('石英')) {
    return 'primary'
  }
  // 碳酸盐矿物
  else if (mineralType.includes('carbonate') || mineralType.includes('碳酸盐') ||
           mineralType.includes('calcite') || mineralType.includes('方解石')) {
    return 'success'
  }
  // 硫化物矿物
  else if (mineralType.includes('sulfide') || mineralType.includes('硫化物') ||
           mineralType.includes('pyrite') || mineralType.includes('黄铁矿')) {
    return 'warning'
  }
  // 氧化物矿物
  else if (mineralType.includes('oxide') || mineralType.includes('氧化物') ||
           mineralType.includes('magnetite') || mineralType.includes('磁铁矿')) {
    return 'info'
  }
  // 其他矿物
  else {
    return 'default'
  }
}
</script>

<style scoped>
.mineral-relationships-display {
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

.minerals-card,
.relationships-card,
.interactions-card,
.organic-mineral-card,
.catalysis-card,
.protection-card {
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

.minerals-content,
.interactions-content {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.mineral-tag,
.interaction-tag {
  margin: 2px;
}

.relationships-content,
.organic-mineral-content,
.catalysis-content,
.protection-content {
  line-height: 1.6;
  color: #606266;
}

.el-tag {
  margin: 2px;
}

.el-alert {
  margin-top: 10px;
}
</style>
