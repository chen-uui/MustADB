<template>
  <div v-if="visible" class="processing-progress-modal" @click.self="handleBackgroundClick">
    <div class="progress-modal-content">
      <div class="progress-header">
        <h3 class="progress-title">{{ title }}</h3>
        <button class="close-btn" @click="close">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div class="progress-body">
        <div class="overall-progress-section">
          <div class="progress-info">
            <span class="progress-text">{{ currentPhase }}</span>
            <span class="progress-percentage">{{ Math.round(overallProgress) }}%</span>
          </div>
          <div class="progress-bar-container">
            <div class="progress-bar" :style="{ width: `${overallProgress}%` }" />
          </div>
          <div class="progress-stats">
            <span>{{ finishedCount }}/{{ totalCount }} 个文件</span>
            <span>{{ elapsedTime }}</span>
          </div>
        </div>

        <div v-if="currentFile && currentFileProgress > 0" class="current-file-progress">
          <div class="file-info">
            <span class="file-name">{{ truncateFileName(currentFile.name) }}</span>
            <span class="file-progress-text">{{ currentFileProgress }}%</span>
          </div>
          <div class="file-progress-bar-container">
            <div class="file-progress-bar" :style="{ width: `${currentFileProgress}%` }" />
          </div>
        </div>

        <div v-if="isComplete || errorCount > 0" class="processing-results">
          <div class="result-item success">
            <span class="result-icon">✓</span>
            <span>成功: {{ successCount }}</span>
          </div>
          <div v-if="errorCount > 0" class="result-item error">
            <span class="result-icon">!</span>
            <span>失败: {{ errorCount }}</span>
          </div>
        </div>

        <div v-if="errors.length > 0" class="error-list">
          <h4 class="error-title">失败文件</h4>
          <div v-for="(error, index) in errors" :key="index" class="error-item">
            <span class="error-filename">{{ truncateFileName(error.file) }}</span>
            <span class="error-message">{{ error.message }}</span>
          </div>
        </div>

        <div v-if="isComplete" class="completion-message">
          <div class="completion-icon">完成</div>
          <p>文件处理已结束。</p>
        </div>
      </div>

      <div class="progress-footer">
        <button class="btn btn-primary" @click="close">
          {{ isComplete ? '关闭' : '停止并关闭' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  files: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: 'PDF 文档处理进度'
  }
})

const emit = defineEmits(['close', 'complete'])

const isComplete = ref(false)
const currentFile = ref(null)
const currentFileProgress = ref(0)
const processedCount = ref(0)
const successCount = ref(0)
const errorCount = ref(0)
const errors = ref([])
const startTime = ref(null)
const elapsedTime = ref('00:00')
const totalDocuments = ref(0)

let elapsedTimer = null

const totalCount = computed(() => totalDocuments.value || props.files.length || 0)

const finishedCount = computed(() => {
  const total = totalCount.value || 0
  return Math.min(total, processedCount.value + errorCount.value)
})

const overallProgress = computed(() => {
  if (isComplete.value) {
    return 100
  }
  const total = totalCount.value
  if (!total) {
    return 0
  }
  return (finishedCount.value / total) * 100
})

const currentPhase = computed(() => {
  if (isComplete.value) {
    return '处理完成'
  }
  if (currentFile.value?.name) {
    return `正在处理：${truncateFileName(currentFile.value.name)}`
  }
  return '等待处理开始...'
})

const startElapsedTimer = () => {
  stopElapsedTimer()
  startTime.value = Date.now()
  elapsedTimer = setInterval(() => {
    if (!startTime.value) {
      return
    }
    const elapsed = Math.floor((Date.now() - startTime.value) / 1000)
    const minutes = Math.floor(elapsed / 60)
    const seconds = elapsed % 60
    elapsedTime.value = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }, 1000)
}

const stopElapsedTimer = () => {
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
}

const handleBackgroundClick = () => {
  close()
}

const close = () => {
  emit('close')
}

const updateProgress = (data = {}) => {
  if (typeof data.total === 'number') {
    totalDocuments.value = data.total
  }
  if (typeof data.processed === 'number') {
    processedCount.value = Math.max(0, data.processed)
    successCount.value = Math.max(successCount.value, data.processed)
  }
  if (typeof data.progress === 'number') {
    currentFileProgress.value = Math.max(0, Math.min(100, data.progress))
  }
  if (data.current_file) {
    currentFile.value = { name: data.current_file }
  }
}

const handleProcessingComplete = (data = {}) => {
  if (typeof data.total === 'number') {
    totalDocuments.value = data.total
  }
  if (typeof data.processed === 'number') {
    processedCount.value = Math.max(0, data.processed)
    successCount.value = Math.max(successCount.value, data.processed)
  } else {
    processedCount.value += 1
    successCount.value += 1
  }
  if (data.current_file) {
    currentFile.value = { name: data.current_file }
  }
  if (totalCount.value > 0 && finishedCount.value >= totalCount.value) {
    completeProcessing()
  }
}

const handleProcessingError = (data = {}) => {
  errorCount.value += 1
  errors.value.push({
    file: data.file || '未知文件',
    message: data.message || '处理失败'
  })

  if (typeof data.total === 'number') {
    totalDocuments.value = data.total
  }
  if (data.current_file) {
    currentFile.value = { name: data.current_file }
  }
  if (totalCount.value > 0 && finishedCount.value >= totalCount.value) {
    completeProcessing()
  }
}

const completeProcessing = () => {
  if (isComplete.value) {
    return
  }
  isComplete.value = true
  currentFile.value = null
  currentFileProgress.value = 100
  stopElapsedTimer()
  emit('complete', {
    total: totalCount.value,
    processed: processedCount.value,
    success: successCount.value,
    errors: errorCount.value
  })
}

const reset = () => {
  isComplete.value = false
  currentFile.value = null
  currentFileProgress.value = 0
  processedCount.value = 0
  successCount.value = 0
  errorCount.value = 0
  errors.value = []
  totalDocuments.value = 0
  startTime.value = null
  elapsedTime.value = '00:00'
  stopElapsedTimer()
}

const truncateFileName = (name) => {
  if (!name || name.length <= 30) {
    return name || '未知文件'
  }
  return `${name.substring(0, 15)}...${name.substring(name.length - 12)}`
}

watch(
  () => props.visible,
  (newValue) => {
    if (newValue) {
      if (!startTime.value) {
        startElapsedTimer()
      }
      if (!totalDocuments.value && props.files.length > 0) {
        totalDocuments.value = props.files.length
      }
    } else {
      stopElapsedTimer()
    }
  }
)

onUnmounted(() => {
  stopElapsedTimer()
})

defineExpose({
  updateProgress,
  handleProcessingError,
  handleProcessingComplete,
  completeProcessing,
  reset
})
</script>

<style scoped>
.processing-progress-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}

.progress-modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.progress-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.close-btn {
  background: none;
  border: none;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f3f4f6;
  color: #374151;
}

.progress-body {
  padding: 24px;
}

.overall-progress-section {
  margin-bottom: 24px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-text {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.progress-percentage {
  font-size: 14px;
  font-weight: 600;
  color: #3b82f6;
}

.progress-bar-container {
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-stats {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
}

.current-file-progress {
  margin-bottom: 20px;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #4b5563;
}

.file-progress-bar-container {
  height: 6px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.file-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  transition: width 0.3s ease;
}

.processing-results {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}

.result-item.success {
  background: #ecfdf5;
  color: #047857;
}

.result-item.error {
  background: #fef2f2;
  color: #b91c1c;
}

.error-list {
  margin-top: 16px;
}

.error-title {
  margin: 0 0 12px;
  font-size: 14px;
  color: #991b1b;
}

.error-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fef2f2;
  margin-bottom: 8px;
}

.error-filename {
  font-size: 13px;
  font-weight: 600;
  color: #991b1b;
}

.error-message {
  font-size: 12px;
  color: #7f1d1d;
  word-break: break-word;
}

.completion-message {
  margin-top: 20px;
  text-align: center;
  color: #047857;
}

.completion-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  height: 64px;
  padding: 0 16px;
  border-radius: 999px;
  background: #ecfdf5;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.progress-footer {
  padding: 16px 24px 24px;
  display: flex;
  justify-content: flex-end;
}

.btn {
  border: none;
  border-radius: 8px;
  padding: 10px 16px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
}

.btn-primary:hover {
  background: #1d4ed8;
}
</style>
