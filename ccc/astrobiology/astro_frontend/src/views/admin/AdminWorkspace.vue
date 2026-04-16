<template>
  <div class="admin-workspace">
    <AdminWorkspaceHeader 
      :active-tab="computedActiveTab"
      @tab-change="handleTabChange"
      @navigate="handleNavigate"
    />
    
    <div class="workspace-body">
      <AdminWorkspaceMain 
        :active-tab="activeTab"
        :workspace-state="workspaceState"
        :current-document="currentDocument"
        :extraction-tasks="extractionTasks"
        @state-change="handleStateChange"
        @document-selected="handleDocumentSelected"
        @upload-complete="handleUploadComplete"
        @document-processed="handleDocumentProcessed"
        @extraction-started="handleExtractionStarted"
        @extraction-progress="handleExtractionProgress"
        @extraction-complete="handleExtractionComplete"
        @error="handleError"
      />
    </div>
    
    <!-- 加载状态覆盖层 -->
    <LoadingOverlay 
      :loading="isLoading"
      :title="loadingTitle"
      :message="loadingMessage"
      :progress="loadingProgress"
    />
    
    <!-- 错误通知 -->
    <ErrorNotification 
      :error="error"
      :type="errorType"
      @retry="handleRetry"
      @dismiss="hideError"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useStore } from 'vuex'
import AdminWorkspaceHeader from '@/components/workspace/AdminWorkspaceHeader.vue'
import AdminWorkspaceMain from '@/components/workspace/AdminWorkspaceMain.vue'
import LoadingOverlay from '@/components/workspace/LoadingOverlay.vue'
import ErrorNotification from '@/components/workspace/ErrorNotification.vue'

const props = defineProps({
  activeTab: {
    type: String,
    default: null
  }
})

const store = useStore()
const emit = defineEmits(['navigate'])

// 响应式数据
const activeTab = computed(() => store.getters['workspace/activeTab'] || 'documents')

// 计算活动标签（考虑当前路径）
const computedActiveTab = computed(() => {
  // 如果传入了props.activeTab，使用它（用于导航栏高亮）
  if (props.activeTab && (props.activeTab === 'unified-review' || props.activeTab === 'system-health')) {
    return props.activeTab
  }
  return activeTab.value
})

// 工作台状态
const workspaceState = ref({
  currentDocument: null,
  isProcessing: false,
  hasError: false
})

// 当前文档
const currentDocument = computed(() => store.getters['workspace/currentDocument'])

// 提取任务
const extractionTasks = computed(() => store.getters['workspace/extractionTasks'] || [])

// 处理状态
const processingStatus = ref({
  isProcessing: false,
  currentTask: null,
  progress: 0
})

// 系统状态
const systemStatus = ref({
  document_count: 0,
  model_name: '未知',
  weaviate_connected: false,
  llm_connected: false,
  initialized: false,
  error: null
})

// API测试结果
const apiTestResults = ref(null)

// 加载状态
const isLoading = ref(false)
const loadingTitle = ref('')
const loadingMessage = ref('')
const loadingProgress = ref(null)

// 错误状态
const error = ref(null)
const errorType = ref('error')

// 导航处理
const adminTabs = new Set([
  'documents',
  'extraction',
  'direct-processing',
  'meteorite-management'
])

const handleNavigate = (route) => {
  if (adminTabs.has(route)) {
    store.dispatch('workspace/switchTab', route)
    return
  }
  emit('navigate', route)
}

// 标签切换处理
const handleTabChange = (tabId) => {
  store.dispatch('workspace/switchTab', tabId)
}

const handleStateChange = (state) => {
  console.log('State change:', state)
}

// 处理文档选择
const handleDocumentSelected = (document) => {
  store.dispatch('workspace/setCurrentDocument', document)
}

// 处理上传完成
const handleUploadComplete = (result) => {
  if (result.success && result.document) {
    store.dispatch('workspace/addDocument', result.document)
  }
}

// 处理文档处理完成
const handleDocumentProcessed = (result) => {
  if (result.success && result.document) {
    store.dispatch('workspace/updateDocument', result.document)
  }
}

// 处理提取事件
const handleExtractionStarted = (task) => {
  store.dispatch('workspace/addExtractionTask', task)
}

const handleExtractionProgress = (progress) => {
  store.dispatch('workspace/updateExtractionProgress', progress)
}

const handleExtractionComplete = (result) => {
  if (result.success && result.task) {
    store.dispatch('workspace/updateExtractionTask', result.task)
  }
}

// 处理错误
const handleError = (err) => {
  console.error('Workspace error:', err)
  error.value = err
  errorType.value = 'error'
}

// 显示加载状态
const showLoading = (title, message, progress = null) => {
  isLoading.value = true
  loadingTitle.value = title
  loadingMessage.value = message
  loadingProgress.value = progress
}

// 隐藏加载状态
const hideLoading = () => {
  isLoading.value = false
  loadingTitle.value = ''
  loadingMessage.value = ''
  loadingProgress.value = null
}

// 显示错误
const showError = (err, type = 'error') => {
  error.value = err
  errorType.value = type
}

// 隐藏错误
const hideError = () => {
  error.value = null
}

// 重试操作
const handleRetry = () => {
  hideError()
}

onMounted(async () => {
  // 恢复状态
  store.dispatch('workspace/restoreState')
  
  // 初始化工作台
  store.dispatch('workspace/initialize')
  
  console.log('后台工作台初始化完成')
})
</script>

<style scoped>
.admin-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: #f5f7fa;
}

.workspace-body {
  display: flex;
  flex: 1;
  overflow: visible;
  min-height: 0;
  width: 100%;
}
</style>
