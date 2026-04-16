<template>
  <div class="scientific-insights-display">
    <div v-if="!data || Object.keys(data).length === 0" class="no-data">
      <el-empty description="暂无科学洞察数据" />
    </div>
    
    <div v-else class="data-content">
      <!-- 科学意义 -->
      <el-card v-if="data.significance" class="significance-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Trophy /></el-icon>
            <span>科学意义</span>
          </div>
        </template>
        
        <div class="significance-content">
          <el-alert
            :title="data.significance"
            type="success"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- 主要结论 -->
      <el-card v-if="data.conclusions" class="conclusions-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Document /></el-icon>
            <span>主要结论</span>
          </div>
        </template>
        
        <div class="conclusions-content">
          <p>{{ data.conclusions }}</p>
        </div>
      </el-card>

      <!-- 研究影响 -->
      <el-card v-if="data.implications" class="implications-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><TrendCharts /></el-icon>
            <span>研究影响</span>
          </div>
        </template>
        
        <div class="implications-content">
          <p>{{ data.implications }}</p>
        </div>
      </el-card>

      <!-- 生命起源洞察 -->
      <el-card v-if="data.life_origin_insights" class="life-origin-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Star /></el-icon>
            <span>生命起源洞察</span>
          </div>
        </template>
        
        <div class="life-origin-content">
          <el-alert
            :title="data.life_origin_insights"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <!-- 宇宙化学洞察 -->
      <el-card v-if="data.cosmochemistry_insights" class="cosmochemistry-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><Moon /></el-icon>
            <span>宇宙化学洞察</span>
          </div>
        </template>
        
        <div class="cosmochemistry-content">
          <p>{{ data.cosmochemistry_insights }}</p>
        </div>
      </el-card>

      <!-- 未来研究方向 -->
      <el-card v-if="data.future_research" class="future-research-card" shadow="never">
        <template #header>
          <div class="card-header">
            <el-icon><TrendCharts /></el-icon>
            <span>未来研究方向</span>
          </div>
        </template>
        
        <div class="future-research-content">
          <el-tag
            v-for="direction in parseFutureResearch(data.future_research)"
            :key="direction"
            class="research-tag"
            type="info"
          >
            {{ direction }}
          </el-tag>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { 
  Trophy, Document, TrendCharts, Star, Moon 
} from '@element-plus/icons-vue'

// 定义props
const props = defineProps({
  data: {
    type: Object,
    default: () => ({})
  }
})

// 解析未来研究方向
const parseFutureResearch = (research) => {
  if (typeof research === 'string') {
    return research.split(/[,;]/).map(r => r.trim()).filter(r => r)
  }
  return Array.isArray(research) ? research : []
}
</script>

<style scoped>
.scientific-insights-display {
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

.significance-card,
.conclusions-card,
.implications-card,
.life-origin-card,
.cosmochemistry-card,
.future-research-card {
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

.significance-content,
.conclusions-content,
.implications-content,
.life-origin-content,
.cosmochemistry-content,
.future-research-content {
  line-height: 1.6;
  color: #606266;
}

.future-research-content {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.research-tag {
  margin: 2px;
}

.el-alert {
  margin-top: 10px;
}

.el-tag {
  margin: 2px;
}
</style>
