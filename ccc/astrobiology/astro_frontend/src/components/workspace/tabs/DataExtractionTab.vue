<template>
  <div class="data-extraction" :class="{ 'workspace-mode': workspaceMode }">
    <div v-if="!workspaceMode" class="extraction-header">
      <h1>数据提取管理中心</h1>
      <p>智能提取陨石数据，构建科学知识库</p>
      
      <!-- 功能说明卡片 -->
      <div class="feature-comparison-card">
        <div class="comparison-header">
          <i class="bi bi-info-circle"></i>
          <span>功能说明：数据提取 vs 直接处理</span>
          </div>
        <div class="comparison-content">
          <div class="feature-item">
            <div class="feature-title">
              <i class="bi bi-search"></i>
              <strong>数据提取（当前功能）</strong>
          </div>
            <ul class="feature-list">
              <li>基于关键词搜索相关片段</li>
              <li>精确提取特定信息</li>
              <li>适合已知要查找的内容</li>
              <li>可批量处理多个片段</li>
              <li>支持实时查看提取进度</li>
            </ul>
        </div>
          <div class="feature-item">
            <div class="feature-title">
              <i class="bi bi-lightning-charge"></i>
              <strong>直接处理</strong>
          </div>
            <ul class="feature-list">
              <li>AI自动分析整篇文档，无需关键词</li>
              <li>适合探索性分析，发现未知信息</li>
              <li>提取陨石数据、有机化合物、矿物关系等</li>
              <li>提供科学洞察和综合分析</li>
            </ul>
        </div>
      </div>
    </div>

      <button @click="navigateHome" class="home-btn">
        <i class="bi bi-house"></i> 返回首页
        </button>
      </div>

    <div class="content-shell">
      <StatsSection :statistics="dashboardData.statistics || {}" />

      <div class="single-task-surface">
        <SingleTaskExtractionTab />
          </div>
          </div>
                </div>
</template>

<script setup>
import { ref, onMounted, provide } from 'vue'
import StatsSection from '@/components/workspace/dataExtraction/StatsSection.vue'
import SingleTaskExtractionTab from '@/components/workspace/dataExtraction/SingleTaskExtractionTab.vue'
import { PDFService } from '@/services/pdfService.js'

const props = defineProps({
  workspaceMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['navigate'])

const dashboardData = ref({
  statistics: {
    current_session_status: '未开始',
    processed_segments: 0,
    extracted_entities: 0,
    aggregated_results: 0
  }
})

// 提供更新统计数据的函数给子组件
const updateStatistics = (stats) => {
  dashboardData.value.statistics = {
    current_session_status: stats.status || '未开始',
    processed_segments: stats.processed_segments || 0,
    extracted_entities: stats.extracted_entities || 0,
    aggregated_results: stats.aggregated_results || 0
  }
}

// 通过 provide 传递给子组件
provide('updateExtractionStats', updateStatistics)

const loadDashboardData = async () => {
  try {
    // 初始化统计数据
    dashboardData.value = {
      statistics: {
        current_session_status: '未开始',
        processed_segments: 0,
        extracted_entities: 0,
        aggregated_results: 0
      }
    }
  } catch (error) {
    console.error('加载仪表板数据失败:', error)
  }
}

const navigateHome = () => {
  emit('navigate', 'home')
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.data-extraction {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.extraction-header {
  text-align: center;
  color: white;
  margin-bottom: 40px;
  position: relative;
}

.extraction-header h1 {
  font-size: 3rem;
  margin-bottom: 10px;
  font-weight: 700;
}

.extraction-header p {
  font-size: 1.2rem;
  opacity: 0.9;
  margin-bottom: 20px;
}

.home-btn {
  position: absolute;
  top: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.2);
  border: 2px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 10px 20px;
  border-radius: 25px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.home-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.content-shell {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.single-task-surface {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 24px;
  box-shadow: 0 24px 60px rgba(64, 80, 180, 0.16);
  padding: 6px;
}

.data-extraction.workspace-mode {
  padding: 0;
  background: transparent;
}

.data-extraction.workspace-mode .extraction-header {
  display: none;
}

.data-extraction.workspace-mode .content-shell {
  padding: 0 1rem 1.5rem;
}

.data-extraction.workspace-mode :deep(.stats-section) {
  margin-top: 0;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 0.5rem;
  margin-bottom: 1rem;
}

.data-extraction.workspace-mode :deep(.search-config) {
  background: linear-gradient(180deg, #fbfcff 0%, #f3f6ff 100%);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid rgba(65, 84, 241, 0.08);
  box-shadow: 0 10px 28px rgba(65, 84, 241, 0.08);
}

.data-extraction.workspace-mode :deep(.template-buttons) {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.data-extraction.workspace-mode :deep(.template-btn) {
  position: relative;
  padding: 10px 20px;
  border: 1px solid rgba(85, 108, 255, 0.18) !important;
  border-radius: 999px;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.9), rgba(244, 248, 255, 0.94));
  color: #3c48a7 !important;
  box-shadow: 0 8px 22px rgba(85, 108, 255, 0.12);
  transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease, color 0.25s ease;
}

.data-extraction.workspace-mode :deep(.template-btn i) {
  margin-right: 6px;
  font-size: 1.1rem;
  opacity: 0.85;
}

.data-extraction.workspace-mode :deep(.template-btn:hover) {
  transform: translateY(-3px);
  box-shadow: 0 14px 28px rgba(85, 108, 255, 0.18);
}

.data-extraction.workspace-mode :deep(.template-btn.active) {
  background: linear-gradient(135deg, #5067ff, #7c8dff) !important;
  color: #fff !important;
  box-shadow: 0 16px 34px rgba(80, 103, 255, 0.3);
  border-color: transparent !important;
}

.data-extraction.workspace-mode :deep(.search-input) {
  border-radius: 12px;
  border: 1px solid rgba(65, 84, 241, 0.15);
  padding: 10px 16px;
  font-size: 0.95rem;
  transition: border 0.2s ease, box-shadow 0.2s ease;
  box-shadow: inset 0 1px 3px rgba(65, 84, 241, 0.06);
}

.data-extraction.workspace-mode :deep(.search-input:focus) {
  outline: none;
  border-color: rgba(65, 84, 241, 0.45);
  box-shadow: 0 0 0 3px rgba(65, 84, 241, 0.12);
}

.data-extraction.workspace-mode :deep(.range-input) {
  appearance: none;
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, #5d78ff 0%, #34c1d1 100%);
  outline: none;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
}

.data-extraction.workspace-mode :deep(.range-input::-webkit-slider-runnable-track) {
  height: 10px;
  border-radius: 999px;
  background: transparent;
}

.data-extraction.workspace-mode :deep(.range-input::-moz-range-track) {
  height: 10px;
  border-radius: 999px;
  background: transparent;
}

.data-extraction.workspace-mode :deep(.range-input::-webkit-slider-thumb) {
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  border: 3px solid #4d63ff;
  box-shadow: 0 6px 18px rgba(77, 99, 255, 0.28);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  margin-top: -6px;
}

.data-extraction.workspace-mode :deep(.range-input::-moz-range-thumb) {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  border: 3px solid #4d63ff;
  box-shadow: 0 6px 18px rgba(77, 99, 255, 0.28);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.data-extraction.workspace-mode :deep(.range-input::-webkit-slider-thumb:hover),
.data-extraction.workspace-mode :deep(.range-input::-moz-range-thumb:hover) {
  transform: scale(1.08);
  box-shadow: 0 10px 24px rgba(77, 99, 255, 0.36);
}

.data-extraction.workspace-mode :deep(.threshold-value) {
  display: inline-block;
  min-width: 48px;
  margin-left: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(93, 120, 255, 0.12);
  color: #4b5dde;
  font-weight: 600;
  text-align: center;
}

.feature-comparison-card {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;
  border-radius: 12px;
  padding: 20px;
  margin-top: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  max-width: 1000px;
  margin-left: auto;
  margin-right: auto;
}

.comparison-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 1rem;
  font-weight: 600;
  color: #0369a1;
}

.comparison-header i {
  font-size: 1.25rem;
}

.comparison-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.feature-item {
  background: white;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e0f2fe;
}

.feature-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 0.9375rem;
  color: #0c4a6e;
}

.feature-title i {
  font-size: 1.125rem;
  color: #0284c7;
}

.feature-list {
  margin: 0;
  padding-left: 20px;
  list-style: none;
}

.feature-list li {
  position: relative;
  padding-left: 20px;
  margin-bottom: 8px;
  font-size: 0.875rem;
  color: #475569;
  line-height: 1.5;
}

.feature-list li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #0284c7;
  font-weight: bold;
}

@media (max-width: 768px) {
  .comparison-content {
    grid-template-columns: 1fr;
  }
}
</style>