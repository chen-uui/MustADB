<template>
  <teleport to="body">
    <transition name="fade">
      <div v-if="visible" class="pdf-preview-overlay" @click="close">
        <div class="pdf-preview-container" @click.stop>
          <div class="pdf-preview-header">
            <h3>{{ title || 'PDF预览' }}</h3>
            <div class="header-actions">
              <button class="btn-icon" @click="download" title="下载">
                <i class="bi bi-download"></i>
              </button>
              <button class="btn-icon" @click="openInNewTab" title="在新标签页打开">
                <i class="bi bi-box-arrow-up-right"></i>
              </button>
              <button class="btn-close" @click="close">×</button>
            </div>
          </div>
          <div class="pdf-preview-body">
            <div v-if="loading" class="loading-state">
              <i class="bi bi-arrow-repeat loading-spin"></i>
              <p>正在加载PDF...</p>
            </div>
            <div v-else-if="error" class="error-state">
              <i class="bi bi-exclamation-triangle"></i>
              <p>{{ error }}</p>
              <button class="btn-retry" @click="loadPDF">重试</button>
            </div>
            <iframe
              v-else
              :src="pdfUrl"
              class="pdf-iframe"
              frameborder="0"
              allowfullscreen
            ></iframe>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { PDFService } from '@/services/pdfService.js'
import { useNotification } from '@/components/base/useNotification.js'
import { getApiErrorMessage } from '@/utils/apiError'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  documentId: {
    type: [Number, String],
    default: null
  },
  title: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:visible', 'close'])

const loading = ref(false)
const error = ref(null)
const pdfUrl = ref('')
const { showError, showSuccess } = useNotification()

const loadPDF = async () => {
  if (!props.documentId) {
    error.value = '文档ID无效'
    return
  }

  loading.value = true
  error.value = null

  try {
    const url = await PDFService.getDownloadUrl(props.documentId)
    pdfUrl.value = url
  } catch (err) {
    console.error('加载PDF失败:', err)
    error.value = getApiErrorMessage(err, '加载PDF失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const close = () => {
  emit('update:visible', false)
  emit('close')
  // 清理URL以释放资源
  pdfUrl.value = ''
}

const download = async () => {
  if (!props.documentId) return
  
  try {
    const response = await PDFService.downloadPDF(props.documentId)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `document_${props.documentId}.pdf`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('下载PDF失败:', err)
    showError(err, '下载PDF失败')
  }
}

const openInNewTab = async () => {
  if (!props.documentId) return
  
  try {
    const url = await PDFService.getDownloadUrl(props.documentId)
    window.open(url, '_blank')
  } catch (err) {
    console.error('打开PDF失败:', err)
    showError(err, '打开PDF失败')
  }
}

// 监听visible变化，当打开时加载PDF
watch(() => props.visible, (newVal) => {
  if (newVal && props.documentId) {
    loadPDF()
  }
})

// 监听documentId变化
watch(() => props.documentId, (newVal) => {
  if (props.visible && newVal) {
    loadPDF()
  }
})
</script>

<style scoped>
.pdf-preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.pdf-preview-container {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 95vw;
  height: 90vh;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.pdf-preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.pdf-preview-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #1f2937;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-icon {
  background: none;
  border: none;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: #6b7280;
  font-size: 1.125rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: #e5e7eb;
  color: #374151;
}

.btn-close {
  background: none;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  color: #6b7280;
  font-size: 1.5rem;
  line-height: 1;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #e5e7eb;
  color: #374151;
}

.pdf-preview-body {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #525252;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
}

.loading-state i {
  font-size: 2rem;
  margin-bottom: 12px;
  color: #3b82f6;
}

.loading-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error-state i {
  font-size: 2rem;
  margin-bottom: 12px;
  color: #ef4444;
}

.error-state p {
  margin: 8px 0 16px;
  font-size: 0.9375rem;
}

.btn-retry {
  padding: 8px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.2s;
}

.btn-retry:hover {
  background: #2563eb;
}

.pdf-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

