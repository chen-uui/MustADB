<template>
  <div class="document-management-container" :class="{ 'workspace-mode': workspaceMode }">
    <!-- 头部区域 - 在工作台模式下隐藏 -->
    <div v-if="!workspaceMode" class="header-section">
      <div class="header-content">
        <div class="header-text">
          <span class="badge">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <path d="M14 2v6h6"/>
            </svg>
            管理系统
          </span>
          <h1 class="title">文档管理中心</h1>
          <p class="subtitle">集中管理您的PDF文档，支持批量上传、分类整理和详细查看</p>
        </div>
        <button class="btn-back" @click="$emit('navigate', 'home')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5"/>
            <path d="M12 19l-7-7 7-7"/>
          </svg>
          返回首页
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-section">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-icon gradient-blue">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <path d="M14 2v6h6"/>
            </svg>
          </div>
          <div class="stat-number">{{ stats.totalFiles }}</div>
          <div class="stat-label">PDF文档总数</div>
          <div class="stat-progress">
            <div class="progress-bar-fill" :style="{ width: stats.totalFiles > 0 ? '100%' : '0%' }"></div>
          </div>
          <div class="stat-trend">
            <span class="trend-text" v-if="stats.totalFiles > 0">共 {{ stats.totalFiles }} 个文档</span>
            <span class="trend-text" v-else>暂无文档</span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon gradient-green">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
          </div>
          <div class="stat-number">{{ stats.uploadCount }}</div>
          <div class="stat-label">本月上传</div>
          <div class="stat-progress">
            <div class="progress-bar-fill" :style="{ width: stats.uploadCount > 0 ? Math.min((stats.uploadCount / Math.max(stats.totalFiles, 1)) * 100, 100) + '%' : '0%' }"></div>
          </div>
          <div class="stat-trend">
            <span class="trend-text" v-if="stats.uploadCount > 0">本月已上传 {{ stats.uploadCount }} 个</span>
            <span class="trend-text" v-else>本月暂无上传</span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon gradient-purple">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <path d="M14 2v6h6"/>
              <path d="M16 13l-4 4-4-4"/>
              <path d="M12 17V9"/>
            </svg>
          </div>
          <div class="stat-number">{{ stats.chunksCount }}</div>
          <div class="stat-label">嵌入块数量</div>
          <div class="stat-progress">
            <div class="progress-bar-fill" :style="{ width: Math.min((stats.chunksCount / 2000) * 100, 100) + '%' }"></div>
          </div>
          <div class="stat-trend">
            <span class="trend-text positive">AI知识片段</span>
          </div>
        </div>

        <div class="stat-card">
          <div class="stat-icon gradient-orange">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7v10c0 5.55 3.84 10 9 9 5.16-1 9-5.45 9-9V7l-10-5z"/>
              <path d="M12 8v8M8 12h8"/>
            </svg>
          </div>
          <div class="stat-number">{{ stats.processedFiles }}/{{ stats.totalFiles }}</div>
          <div class="stat-label">处理状态</div>
          <div class="stat-progress">
            <div class="progress-bar-fill" :style="{ width: stats.processingRate + '%' }"></div>
          </div>
          <div class="stat-trend">
            <span class="trend-text">{{ stats.processingRate }}% 已处理</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 操作区域 -->
    <div class="content-section">
      <div class="manage-header">
        <h3>文档列表</h3>
        <div class="header-actions">
          <div class="search-box">
            <svg class="search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索文档名称..."
              class="search-input"
            />
          </div>
          <button class="reprocess-all-btn" @click="reprocessAllDocuments" :disabled="loading" title="重新处理所有文档">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
              <path d="M21 3v5h-5"/>
              <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
              <path d="M8 16H3v5"/>
            </svg>
            {{ loading ? '重新处理中...' : '重新处理全部' }}
          </button>
          <button class="sync-btn" @click="processStale" :disabled="loading" title="增量修复：仅处理陈旧或缺失向量的文档">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7v10c0 5.55 3.84 10 9 9 5.16-1 9-5.45 9-9V7l-10-5z"/>
              <path d="M12 8v8M8 12h8"/>
            </svg>
            {{ loading ? '修复中...' : '增量修复' }}
          </button>
          <button class="sync-btn" @click="syncFiles" :disabled="loading" title="同步文件夹中的PDF文件">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 2v6h-6"/>
              <path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
              <path d="M3 22v-6h6"/>
              <path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
            </svg>
            {{ loading ? '同步中...' : '同步文件' }}
          </button>
          <!-- Progress dialog test entry -->
          <button class="sync-btn test" @click="testProgressModal" :disabled="loading" title="测试进度窗口">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="12" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            测试进度
          </button>
          <button class="process-all-btn" @click="processAllDocuments" :disabled="loading">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7v10c0 5.55 3.84 10 9 9 5.16-1 9-5.45 9-9V7l-10-5z"/>
              <path d="M12 8v8M8 12h8"/>
            </svg>
            {{ loading ? '处理中...' : '批量处理' }}
          </button>
          <button class="upload-btn" @click="triggerFileUpload">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            上传PDF
          </button>
          <input ref="fileInput" type="file" multiple accept=".pdf" @change="handleFileUpload" style="display: none">
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
        <p v-if="loadDuration > 0" class="load-time">已用时: {{ loadDuration.toFixed(0) }}ms</p>
      </div>

      <!-- 文档网格 -->
      <div v-else class="documents-grid">
        <div v-for="doc in filteredDocuments" :key="doc.id" class="document-card" :data-doc-id="doc.id" @click="selectDocument(doc)">
          <div class="doc-preview">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <path d="M14 2v6h6"/>
            </svg>
          </div>
          <div class="doc-info">
            <h4>{{ cleanDocumentTitle(doc.title) }}</h4>
            <p class="doc-meta">{{ doc.size }} • {{ doc.date }}</p>
            <span class="process-status" :class="{ processed: doc.processed, unprocessed: !doc.processed }">
              {{ doc.processed ? '已处理' : '未处理' }}
            </span>
          </div>
          <div class="doc-actions">
            <button v-if="!doc.processed" class="doc-btn process" @click="processDocument(doc.id)" :disabled="processingDoc === doc.id">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7v10c0 5.55 3.84 10 9 9 5.16-1 9-5.45 9-9V7l-10-5z"/>
                <path d="M12 8v8M8 12h8"/>
              </svg>
              {{ processingDoc === doc.id ? '处理中...' : '处理' }}
            </button>
            <button class="doc-btn view" @click="viewPDF(doc.id)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              查看
            </button>
            <button class="doc-btn download" @click="downloadPDF(doc.id)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              下载
            </button>
            <button class="doc-btn delete" @click="deleteDocument(doc.id)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
              删除
            </button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="filteredDocuments.length === 0" class="empty-state">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <path d="M14 2v6h6"/>
        </svg>
        <h3>暂无文档</h3>
        <p>点击上传按钮添加您的第一个PDF文档</p>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="totalPages > 1">
        <button 
          @click="loadDocuments(currentPage - 1)" 
          :disabled="currentPage === 1"
          class="page-btn"
        >
          上一页
        </button>
        <span class="page-info">
          第 {{ currentPage }} 页 / 共 {{ totalPages }} 页
          <span v-if="documents.length > 0" style="margin-left: 10px; color: #666;">
            ({{ (currentPage - 1) * pageSize + 1 }}-{{ Math.min((currentPage - 1) * pageSize + documents.length, currentPage * pageSize) }})
          </span>
        </span>
        <button 
          @click="loadDocuments(currentPage + 1)" 
          :disabled="currentPage === totalPages"
          class="page-btn"
        >
          下一页
        </button>
      </div>
    </div>
  </div>

  <!-- 处理进度窗口 -->
  <ProcessingProgress
    ref="progressModalRef"
    :visible="showProgressModal"
    :files="processingFiles"
    title="PDF文档处理进度"
    @close="closeProgressModal"
    @complete="onProcessingComplete"
  />

  <!-- PDF预览模态框 -->
  <PDFPreviewModal
    :visible="showPreviewModal"
    :document-id="previewPDFId"
    :title="previewPDFId ? documents.find(d => d.id === previewPDFId)?.title : ''"
    @update:visible="showPreviewModal = $event"
    @close="closePreview"
  />
</template>

<script>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import PDFService from '@/services/pdfService'
import PDFPreviewModal from '@/components/workspace/PDFPreviewModal.vue'
import ProcessingProgress from '@/components/ProcessingProgress.vue'
import { useDocumentList } from '@/composables/useDocumentList'
import { useDocumentUpload } from '@/composables/useDocumentUpload'
import { useProcessingStatus } from '@/composables/useProcessingStatus'

export default {
  name: 'DocumentManagement',
  components: {
    ProcessingProgress,
    PDFPreviewModal
  },
  props: {
    workspaceMode: {
      type: Boolean,
      default: false
    },
    currentDocument: Object,
    workspaceState: Object
  },
  emits: ['navigate', 'document-selected', 'upload-complete', 'document-processed', 'error'],
  setup(props, { emit }) {
    const searchQuery = ref('')
    const fileInput = ref(null)
    const loading = ref(false)

    const stats = reactive({
      totalFiles: 0,
      uploadCount: 0,
      chunksCount: 0,
      processedFiles: 0,
      pendingFiles: 0,
      processingRate: 0
    })

    const documents = ref([])
    const currentPage = ref(1)
    const pageSize = 20
    const totalPages = ref(1)
    const showProgressModal = ref(false)
    const processingFiles = ref([])
    const progressModalRef = ref(null)
    const processingDoc = ref(null)

    const loadStartTime = ref(0)
    const loadEndTime = ref(0)
    const loadDuration = computed(() => loadEndTime.value - loadStartTime.value)

    const debouncedSearch = ref('')
    let searchTimeout = null
    const searchCache = new Map()

    watch(searchQuery, (newQuery) => {
      if (searchTimeout) clearTimeout(searchTimeout)
      searchTimeout = setTimeout(() => {
        debouncedSearch.value = newQuery
      }, 200)
    })

    const filteredDocuments = computed(() => {
      if (!debouncedSearch.value.trim()) return documents.value

      const query = debouncedSearch.value.toLowerCase().trim()
      if (searchCache.has(query)) {
        return searchCache.get(query)
      }

      const results = documents.value.filter((doc) => {
        const titleLower = doc.title?.toLowerCase() || ''
        return titleLower.includes(query)
      })

      if (searchCache.size > 50) {
        const firstKey = searchCache.keys().next().value
        searchCache.delete(firstKey)
      }
      searchCache.set(query, results)

      return results
    })

    const documentListActions = useDocumentList({
      workspaceMode: props.workspaceMode,
      loading,
      stats,
      documents,
      currentPage,
      totalPages,
      pageSize,
      processingDoc,
      loadStartTime,
      loadEndTime,
      loadDuration
    })

    const processingStatusActions = useProcessingStatus({
      loading,
      documents,
      stats,
      currentPage,
      loadDocuments: (...args) => documentListActions.loadDocuments(...args),
      loadStats: (...args) => documentListActions.loadStats(...args),
      showProgressModal,
      processingFiles,
      progressModalRef
    })

    const uploadActions = useDocumentUpload({
      fileInput,
      currentPage,
      loadDocuments: (...args) => documentListActions.loadDocuments(...args),
      loadStats: (...args) => documentListActions.loadStats(...args),
      processingFiles,
      showProgressModal,
      progressModalRef,
      updateProgress: (...args) => processingStatusActions.updateProgress(...args),
      handleProcessingComplete: (...args) => processingStatusActions.handleProcessingComplete(...args),
      closeProgressModal: (...args) => processingStatusActions.closeProgressModal(...args)
    })

    const previewPDFId = ref(null)
    const showPreviewModal = ref(false)

    const viewPDF = (id) => {
      previewPDFId.value = id
      showPreviewModal.value = true
    }

    const closePreview = () => {
      showPreviewModal.value = false
      previewPDFId.value = null
    }

    const loadDocuments = (...args) => documentListActions.loadDocuments(...args)
    const loadStats = (...args) => documentListActions.loadStats(...args)
    const downloadPDF = (...args) => documentListActions.downloadPDF(...args)
    const triggerFileUpload = (...args) => uploadActions.triggerFileUpload(...args)
    const handleFileUpload = (...args) => uploadActions.handleFileUpload(...args)
    const deleteDocument = (...args) => documentListActions.deleteDocument(...args)
    const processDocument = (...args) => documentListActions.processDocument(...args)
    const processAllDocuments = (...args) => processingStatusActions.processAllDocuments(...args)
    const processStale = (...args) => processingStatusActions.processStale(...args)
    const reprocessAllDocuments = (...args) => processingStatusActions.reprocessAllDocuments(...args)
    const syncFiles = (...args) => documentListActions.syncFiles(...args)
    const cleanDocumentTitle = (...args) => documentListActions.cleanDocumentTitle(...args)
    const closeProgressModal = (...args) => processingStatusActions.closeProgressModal(...args)
    const onProcessingComplete = (...args) => processingStatusActions.onProcessingComplete(...args)
    const testProgressModal = (...args) => processingStatusActions.testProgressModal(...args)

    const setupGlobalErrorHandlers = () => {
      const errorHandler = (event) => {
        console.error('Global error:', event.error)
      }

      const rejectionHandler = (event) => {
        console.error('Unhandled promise rejection:', event.reason)
      }

      window.addEventListener('error', errorHandler)
      window.addEventListener('unhandledrejection', rejectionHandler)

      return () => {
        window.removeEventListener('error', errorHandler)
        window.removeEventListener('unhandledrejection', rejectionHandler)
      }
    }

    const selectDocument = (document) => {
      if (props.workspaceMode) {
        emit('document-selected', document)
      }
    }

    let statsRefreshInterval = null
    let autoSyncTimer = null
    let cleanupErrorHandlers = () => {}

    onMounted(() => {
      Promise.all([loadDocuments(1), loadStats()]).catch((error) => {
        console.error('Initial document load failed:', error)
      })

      if (!props.workspaceMode) {
        autoSyncTimer = setTimeout(async () => {
          if (documents.value.length === 0) {
            try {
              await PDFService.syncFiles()
              await loadDocuments(1)
              await loadStats(true)
            } catch (error) {
              console.warn('Automatic file sync skipped:', error)
            }
          }
        }, 100)
      }

      const refreshInterval = props.workspaceMode ? 300000 : 120000
      statsRefreshInterval = setInterval(() => {
        loadStats()
      }, refreshInterval)

      cleanupErrorHandlers = setupGlobalErrorHandlers()
    })

    onUnmounted(() => {
      if (searchTimeout) clearTimeout(searchTimeout)
      if (statsRefreshInterval) clearInterval(statsRefreshInterval)
      if (autoSyncTimer) clearTimeout(autoSyncTimer)
      cleanupErrorHandlers()
      processingStatusActions.cleanup()
      searchCache.clear()
    })

    watch(showProgressModal, (newValue, oldValue) => {
      console.log('showProgressModal changed:', oldValue, '->', newValue)
    })

    return {
      searchQuery,
      stats,
      documents,
      filteredDocuments,
      fileInput,
      loading,
      processingDoc,
      currentPage,
      pageSize,
      totalPages,
      showProgressModal,
      processingFiles,
      debouncedSearch,
      loadDuration,
      previewPDFId,
      showPreviewModal,
      progressModalRef,
      viewPDF,
      closePreview,
      downloadPDF,
      triggerFileUpload,
      handleFileUpload,
      deleteDocument,
      processDocument,
      processAllDocuments,
      processStale,
      reprocessAllDocuments,
      syncFiles,
      loadDocuments,
      cleanDocumentTitle,
      closeProgressModal,
      selectDocument,
      onProcessingComplete,
      testProgressModal
    }
  }
}
</script>

<style scoped>
.document-management-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

/* 头部区域 */
.header-section {
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  color: white;
  padding: 2rem 0;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1.5rem;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.625rem;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 24px;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
  font-weight: 500;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.title {
  font-size: 2.25rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.subtitle {
  font-size: 1.0625rem;
  opacity: 0.9;
  margin-bottom: 0;
}

.btn-back {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  backdrop-filter: blur(10px);
  border-radius: 24px;
  padding: 0.75rem 1.5rem;
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
}

.btn-back:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 统计区域 - 玻璃态卡片 */
.stats-section {
  padding: 2rem;
  background: transparent;
}

.stats-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

/* 卡片背景渐变装饰 */
.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 120px;
  height: 120px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
  border-radius: 50%;
  transform: translate(30%, -30%);
  transition: transform 0.4s ease;
}

.stat-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.stat-card:hover::before {
  transform: translate(30%, -30%) scale(1.2);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 1;
}

.gradient-blue { 
  background: linear-gradient(135deg, #3b82f6, #8b5cf6); 
  color: white; 
}

.gradient-green { 
  background: linear-gradient(135deg, #10b981, #059669); 
  color: white; 
}

.gradient-purple { 
  background: linear-gradient(135deg, #8b5cf6, #ec4899); 
  color: white; 
}

.gradient-orange { 
  background: linear-gradient(135deg, #f59e0b, #ef4444); 
  color: white; 
}

.stat-number {
  font-size: 2.25rem;
  font-weight: 700;
  background: linear-gradient(135deg, #1e293b, #475569);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 0.5rem;
  position: relative;
  z-index: 1;
}

.stat-label {
  color: #64748b;
  font-size: 0.9375rem;
  margin-bottom: 0.75rem;
  font-weight: 500;
  position: relative;
  z-index: 1;
}

.stat-progress {
  height: 6px;
  background: rgba(0, 0, 0, 0.08);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 0.75rem;
  position: relative;
  z-index: 1;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.trend-text {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
  position: relative;
  z-index: 1;
}

.trend-text.positive { 
  color: #10b981; 
}

/* 内容区域 */
.content-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.manage-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1.5rem;
}

.manage-header h3 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1e293b;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

/* 现代化搜索框 */
.search-box {
  position: relative;
  display: flex;
  max-width: 320px;
}

.search-icon {
  position: absolute;
  left: 1.25rem;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  z-index: 2;
  transition: color 0.3s ease;
}

.search-input {
  flex: 1;
  padding: 0.875rem 1.25rem 0.875rem 3.25rem;
  border: 2px solid #e2e8f0;
  border-radius: 14px;
  font-size: 0.9375rem;
  outline: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.search-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.15), 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.search-input:focus + .search-icon {
  color: #3b82f6;
}

/* 优化按钮设计 */
.upload-btn {
  padding: 0.875rem 1.75rem;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-weight: 600;
  font-size: 0.9375rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.upload-btn:hover {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.upload-btn:active {
  transform: translateY(0);
}

.reprocess-all-btn {
  padding: 0.875rem 1.75rem;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-weight: 600;
  font-size: 0.9375rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.reprocess-all-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.reprocess-all-btn:disabled {
  background: linear-gradient(135deg, #fca5a5 0%, #f87171 100%);
  cursor: not-allowed;
  transform: none;
  opacity: 0.6;
}

.process-all-btn {
  padding: 0.875rem 1.75rem;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-weight: 600;
  font-size: 0.9375rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.process-all-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.process-all-btn:disabled {
  background: linear-gradient(135deg, #86efac 0%, #6ee7b7 100%);
  cursor: not-allowed;
  transform: none;
  opacity: 0.6;
}

.sync-btn {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 0.75rem 1.25rem;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.sync-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.sync-btn:disabled {
  background: linear-gradient(135deg, #c4b5fd 0%, #a78bfa 100%);
  cursor: not-allowed;
  transform: none;
  opacity: 0.6;
}

/* 测试按钮样式 */
.sync-btn.test {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.sync-btn.test:hover:not(:disabled) {
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.sync-btn.test:disabled {
  background: linear-gradient(135deg, #fcd34d 0%, #fbbf24 100%);
  opacity: 0.6;
  cursor: not-allowed;
}

/* 文档网格 */
.documents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.document-card {
  background: white;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 16px;
  padding: 1.75rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  position: relative;
  overflow: hidden;
}

.document-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.document-card:hover {
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
  transform: translateY(-4px);
  border-color: rgba(59, 130, 246, 0.3);
}

.document-card:hover::before {
  opacity: 1;
}

.doc-preview {
  width: 70px;
  height: 70px;
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.25rem;
  color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.doc-info h4 {
  margin: 0 0 0.75rem 0;
  color: #1e293b;
  font-size: 1.125rem;
  font-weight: 600;
  line-height: 1.4;
}

.doc-meta {
  color: #64748b;
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
  font-weight: 500;
}

.process-status {
  display: inline-block;
  padding: 0.375rem 0.875rem;
  border-radius: 16px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-top: 0.5rem;
}

.process-status.processed {
  background: linear-gradient(135deg, #dcfce7, #bbf7d0);
  color: #166534;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.15);
}

.process-status.unprocessed {
  background: linear-gradient(135deg, #fef3c7, #fde68a);
  color: #92400e;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.15);
}

.doc-actions {
  display: flex;
  gap: 0.625rem;
  margin-top: 1.25rem;
  flex-wrap: wrap;
}

.doc-btn {
  padding: 0.625rem 1.125rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  background: white;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  gap: 0.375rem;
}

.doc-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.doc-btn.view {
  color: #3b82f6;
  border-color: #bfdbfe;
}

.doc-btn.view:hover {
  background: #eff6ff;
  border-color: #3b82f6;
}

.doc-btn.download {
  color: #10b981;
  border-color: #a7f3d0;
}

.doc-btn.download:hover {
  background: #d1fae5;
  border-color: #10b981;
}

.doc-btn.delete {
  color: #ef4444;
  border-color: #fecaca;
}

.doc-btn.delete:hover {
  background: #fee2e2;
  border-color: #ef4444;
}

.doc-btn.process {
  color: #10b981;
  border-color: #a7f3d0;
}

.doc-btn.process:hover:not(:disabled) {
  background: #d1fae5;
  border-color: #10b981;
}

.doc-btn.process:disabled {
  background: #d1fae5;
  color: #6ee7b7;
  cursor: not-allowed;
  opacity: 0.6;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.empty-state svg {
  margin-bottom: 1.5rem;
  color: #cbd5e1;
}

.empty-state h3 {
  margin: 0 0 0.75rem 0;
  color: #1e293b;
  font-size: 1.375rem;
  font-weight: 600;
}

.empty-state p {
  color: #64748b;
  font-size: 1rem;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2.5rem;
  padding: 1.5rem;
}

.page-btn {
  padding: 0.75rem 1.5rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 0.9375rem;
  font-weight: 600;
  color: #475569;
}

.page-btn:hover:not(:disabled) {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: #f8fafc;
}

.page-info {
  font-size: 0.9375rem;
  color: #64748b;
  font-weight: 500;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
  color: #64748b;
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.load-time {
  font-size: 0.875rem;
  color: #94a3b8;
  margin-top: 0.75rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 1.5rem;
  }
  
  .manage-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-box {
    max-width: 100%;
  }
  
  .documents-grid {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* 工作台模式样式 */
.document-management-container.workspace-mode {
  padding: 0;
  background: transparent;
}

.document-management-container.workspace-mode .header-section {
  display: none;
}

.document-management-container.workspace-mode .stats-section {
  margin-top: 0;
  padding: 1.5rem;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  margin-bottom: 1.5rem;
}

.document-management-container.workspace-mode .content-section {
  padding: 0 1.5rem 1.5rem;
}

.document-management-container.workspace-mode .document-card {
  cursor: pointer;
}

.document-management-container.workspace-mode .document-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.15);
}
</style>
