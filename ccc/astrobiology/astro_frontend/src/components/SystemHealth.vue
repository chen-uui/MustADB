<template>
  <div class="system-health">
    <div class="health-header">
      <h3 class="health-title">
        <i class="fas fa-heartbeat"></i>
        系统健康状态
      </h3>
      <div class="health-actions">
        <button 
          @click="refreshHealth" 
          :disabled="loading"
          class="refresh-btn"
        >
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': loading }"></i>
          刷新
        </button>
        <div class="auto-refresh">
          <label>
            <input 
              type="checkbox" 
              v-model="autoRefresh"
              @change="toggleAutoRefresh"
            >
            自动刷新 (30s)
          </label>
        </div>
      </div>
    </div>

    <div v-if="loading && !healthData" class="loading-state">
      <i class="fas fa-spinner fa-spin"></i>
      正在检查系统状态...
    </div>

    <div v-else-if="error" class="error-state">
      <i class="fas fa-exclamation-triangle"></i>
      <span>{{ error }}</span>
      <button @click="refreshHealth" class="retry-btn">重试</button>
    </div>

    <div v-else-if="healthData" class="health-content">
      <!-- 整体状态 -->
      <div class="overall-status" :class="getStatusClass(healthData.overall_status)">
        <div class="status-icon">
          <i :class="getStatusIcon(healthData.overall_status)"></i>
        </div>
        <div class="status-info">
          <h4>{{ getStatusText(healthData.overall_status) }}</h4>
          <p class="timestamp">
            最后更新: {{ formatTimestamp(healthData.timestamp) }}
          </p>
        </div>
      </div>

      <!-- 组件状态 -->
      <div class="components-grid">
        <div 
          v-for="(component, name) in healthData.components" 
          :key="name"
          class="component-card"
          :class="getStatusClass(component.status)"
        >
          <div class="component-header">
            <div class="component-icon">
              <i :class="getComponentIcon(name)"></i>
            </div>
            <h5>{{ getComponentName(name) }}</h5>
            <div class="component-status" :class="getStatusClass(component.status)">
              {{ getStatusText(component.status) }}
            </div>
          </div>
          
          <div class="component-details">
            <div v-if="name === 'rag_service'" class="rag-details">
              <div class="detail-item">
                <span class="label">初始化状态:</span>
                <span class="value" :class="component.initialized ? 'success' : 'error'">
                  {{ component.initialized ? '已初始化' : '未初始化' }}
                </span>
              </div>
              <div class="detail-item">
                <span class="label">文档数量:</span>
                <span class="value">{{ component.document_count || 0 }}</span>
              </div>
              <div class="detail-item">
                <span class="label">模型:</span>
                <span class="value">{{ component.model || 'unknown' }}</span>
              </div>
            </div>

            <div v-else-if="name === 'weaviate'" class="weaviate-details">
              <div class="detail-item">
                <span class="label">URL:</span>
                <span class="value">{{ component.url }}</span>
              </div>
              <div v-if="component.response_time_ms" class="detail-item">
                <span class="label">响应时间:</span>
                <span class="value">{{ component.response_time_ms }}ms</span>
              </div>
            </div>

            <div v-else-if="name === 'llm'" class="llm-details">
              <div class="detail-item">
                <span class="label">URL:</span>
                <span class="value">{{ component.url }}</span>
              </div>
              <div v-if="component.models_count !== undefined" class="detail-item">
                <span class="label">可用模型:</span>
                <span class="value">{{ component.models_count }}</span>
              </div>
              <div v-if="component.response_time_ms" class="detail-item">
                <span class="label">响应时间:</span>
                <span class="value">{{ component.response_time_ms }}ms</span>
              </div>
            </div>

            <div v-else-if="name === 'database'" class="database-details">
              <div class="detail-item">
                <span class="label">总文档:</span>
                <span class="value">{{ component.total_documents || 0 }}</span>
              </div>
              <div class="detail-item">
                <span class="label">已处理:</span>
                <span class="value">{{ component.processed_documents || 0 }}</span>
              </div>
              <div class="detail-item">
                <span class="label">待处理:</span>
                <span class="value">{{ component.pending_documents || 0 }}</span>
              </div>
            </div>

            <div v-if="component.error" class="error-details">
              <div class="detail-item error">
                <span class="label">错误:</span>
                <span class="value">{{ component.error }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 系统指标 -->
      <div v-if="healthData.metrics" class="metrics-section">
        <h4>系统指标</h4>
        <div class="metrics-grid">
          <div v-if="healthData.metrics.document_processing_rate !== undefined" class="metric-card">
            <div class="metric-value">{{ healthData.metrics.document_processing_rate.toFixed(1) }}%</div>
            <div class="metric-label">文档处理率</div>
          </div>
        </div>
      </div>

      <!-- 错误信息 -->
      <div v-if="healthData.errors && healthData.errors.length > 0" class="errors-section">
        <h4>系统错误</h4>
        <div class="error-list">
          <div v-for="(error, index) in healthData.errors" :key="index" class="error-item">
            <i class="fas fa-exclamation-circle"></i>
            {{ error }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import PDFService from '@/services/pdfService.js'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess } from '@/utils/apiResponse'

const healthData = ref(null)
const loading = ref(false)
const error = ref(null)
const autoRefresh = ref(true)
let refreshInterval = null

const refreshHealth = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await PDFService.getSystemHealth()
    healthData.value = ensureApiSuccess(response, '获取系统健康状态失败')
  } catch (err) {
    error.value = getApiErrorMessage(err, '获取系统健康状态失败')
    console.error('健康检查失败:', err)
  } finally {
    loading.value = false
  }
}

const toggleAutoRefresh = () => {
  if (autoRefresh.value) {
    if (refreshInterval) clearInterval(refreshInterval)
    refreshInterval = setInterval(refreshHealth, 10000)
  } else {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }
}

const getStatusClass = (status) => {
  switch (status) {
    case 'healthy': return 'status-healthy'
    case 'degraded': return 'status-degraded'
    case 'unhealthy': return 'status-unhealthy'
    case 'error': return 'status-error'
    default: return 'status-unknown'
  }
}

const getStatusIcon = (status) => {
  switch (status) {
    case 'healthy': return 'fas fa-check-circle'
    case 'degraded': return 'fas fa-exclamation-triangle'
    case 'unhealthy': return 'fas fa-times-circle'
    case 'error': return 'fas fa-exclamation-circle'
    default: return 'fas fa-question-circle'
  }
}

const getStatusText = (status) => {
  switch (status) {
    case 'healthy': return '健康'
    case 'degraded': return '降级'
    case 'unhealthy': return '不健康'
    case 'error': return '错误'
    default: return '未知'
  }
}

const getComponentIcon = (name) => {
  switch (name) {
    case 'rag_service': return 'fas fa-brain'
    case 'weaviate': return 'fas fa-database'
    case 'llm': return 'fas fa-robot'
    case 'database': return 'fas fa-server'
    default: return 'fas fa-cog'
  }
}

const getComponentName = (name) => {
  switch (name) {
    case 'rag_service': return 'RAG服务'
    case 'weaviate': return 'Weaviate向量数据库'
    case 'llm': return 'LLM服务'
    case 'database': return '数据库'
    default: return name
  }
}

const formatTimestamp = (timestamp) => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

onMounted(() => {
  refreshHealth()
  toggleAutoRefresh()
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.system-health {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.health-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.health-title {
  margin: 0;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.health-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.refresh-btn {
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background-color 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #0056b3;
}

.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auto-refresh label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
  cursor: pointer;
}

.loading-state, .error-state {
  padding: 40px;
  text-align: center;
  color: #666;
}

.error-state {
  color: #dc3545;
}

.retry-btn {
  margin-left: 16px;
  padding: 4px 12px;
  background: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.health-content {
  padding: 20px;
}

.overall-status {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.status-icon {
  font-size: 32px;
}

.status-info h4 {
  margin: 0 0 4px 0;
  font-size: 18px;
}

.timestamp {
  margin: 0;
  font-size: 14px;
  opacity: 0.7;
}

.components-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.component-card {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s;
}

.component-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.component-icon {
  font-size: 20px;
}

.component-header h5 {
  margin: 0;
  flex: 1;
  font-size: 16px;
}

.component-status {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
}

.component-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.detail-item .label {
  color: #666;
  font-weight: 500;
}

.detail-item .value {
  font-weight: 600;
}

.detail-item.error .value {
  color: #dc3545;
  font-size: 12px;
  max-width: 200px;
  word-break: break-word;
}

.metrics-section, .errors-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e9ecef;
}

.metrics-section h4, .errors-section h4 {
  margin: 0 0 16px 0;
  color: #333;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.metric-card {
  text-align: center;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #007bff;
  margin-bottom: 4px;
}

.metric-label {
  font-size: 14px;
  color: #666;
}

.error-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f8d7da;
  color: #721c24;
  border-radius: 4px;
  font-size: 14px;
}

/* 状态颜色 */
.status-healthy {
  background: #d4edda;
  border-color: #c3e6cb;
  color: #155724;
}

.status-healthy .status-icon,
.status-healthy .component-icon {
  color: #28a745;
}

.status-healthy .component-status {
  background: #28a745;
  color: white;
}

.status-degraded {
  background: #fff3cd;
  border-color: #ffeaa7;
  color: #856404;
}

.status-degraded .status-icon,
.status-degraded .component-icon {
  color: #ffc107;
}

.status-degraded .component-status {
  background: #ffc107;
  color: #212529;
}

.status-unhealthy,
.status-error {
  background: #f8d7da;
  border-color: #f5c6cb;
  color: #721c24;
}

.status-unhealthy .status-icon,
.status-unhealthy .component-icon,
.status-error .status-icon,
.status-error .component-icon {
  color: #dc3545;
}

.status-unhealthy .component-status,
.status-error .component-status {
  background: #dc3545;
  color: white;
}

.status-unknown {
  background: #e2e3e5;
  border-color: #d6d8db;
  color: #383d41;
}

.status-unknown .status-icon,
.status-unknown .component-icon {
  color: #6c757d;
}

.status-unknown .component-status {
  background: #6c757d;
  color: white;
}

.value.success {
  color: #28a745;
}

.value.error {
  color: #dc3545;
}
</style>
