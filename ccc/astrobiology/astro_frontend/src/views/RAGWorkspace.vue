<template>
  <div class="rag-workspace">
    <WorkspaceHeader 
      :active-tab="activeTab"
      @tab-change="handleTabChange"
      @navigate="handleNavigate"
    />
    
    <div class="workspace-body">
      <WorkspaceSidebar 
        :active-tab="activeTab"
        :workspace-state="workspaceState"
        @action="handleSidebarAction"
      />
      
      <WorkspaceMain 
        :active-tab="activeTab"
        :workspace-state="workspaceState"
        :current-document="currentDocument"
        :qa-history="qaHistory"
        :extraction-tasks="extractionTasks"
        :analysis-results="results?.extractedData || []"
        @state-change="handleStateChange"
        @document-selected="handleDocumentSelected"
        @upload-complete="handleUploadComplete"
        @document-processed="handleDocumentProcessed"
        @question-asked="handleQuestionAsked"
        @answer-received="handleAnswerReceived"
        @history-updated="handleHistoryUpdated"
        @extraction-started="handleExtractionStarted"
        @extraction-progress="handleExtractionProgress"
        @extraction-complete="handleExtractionComplete"
        @result-selected="handleResultSelected"
        @export-data="handleExportData"
        @generate-report="handleGenerateReport"
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
import WorkspaceHeader from '@/components/workspace/WorkspaceHeader.vue'
import WorkspaceSidebar from '@/components/workspace/WorkspaceSidebar.vue'
import WorkspaceMain from '@/components/workspace/WorkspaceMain.vue'
import LoadingOverlay from '@/components/workspace/LoadingOverlay.vue'
import ErrorNotification from '@/components/workspace/ErrorNotification.vue'
import { runAPICompatibilityTest, getTestResults } from '@/utils/apiCompatibilityTest'
import { runFunctionalityTest, getFunctionalityTestResults } from '@/utils/functionalityTest'
import { runWorkspaceIntegrationTest, getWorkspaceIntegrationTestResults } from '@/utils/workspaceIntegrationTest'
import { runEndToEndTest, getEndToEndTestResults } from '@/utils/endToEndTest'
import { getApiErrorMessage } from '@/utils/apiError'

const store = useStore()
const emit = defineEmits(['navigate'])

// 响应式数据
const activeTab = computed(() => store.getters['workspace/activeTab'] || 'meteorite-search')

// 工作台状态
const workspaceState = ref({
  currentDocument: null,
  isProcessing: false,
  hasError: false
})

// 当前文档
const currentDocument = computed(() => store.getters['workspace/currentDocument'])

// 问答历史
const qaHistory = computed(() => store.getters['workspace/qaHistory'] || [])

// 提取任务
const extractionTasks = computed(() => store.getters['workspace/extractionTasks'] || [])

// 分析结果
const results = computed(() => store.getters['workspace/results'] || { extractedData: [] })

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

// 测试状态
const isRunningAPITest = ref(false)
const functionalityTestResults = ref(null)
const isRunningFunctionalityTest = ref(false)
const workspaceIntegrationTestResults = ref(null)
const isRunningWorkspaceIntegrationTest = ref(false)
const endToEndTestResults = ref(null)
const isRunningEndToEndTest = ref(false)

// 导航处理
const workspaceTabs = new Set([
  'meteorite-search',
  'documents',
  'qa',
  'extraction',
  'direct-processing',
  'meteorite-management'
])

const handleNavigate = (route) => {
  if (workspaceTabs.has(route)) {
    store.dispatch('workspace/switchTab', route)
    return
  }
  emit('navigate', route)
}

// 标签切换处理
const handleTabChange = (tabId) => {
  store.dispatch('workspace/switchTab', tabId)
}

const handleSidebarAction = (action) => {
  console.log('Sidebar action:', action)
  // 处理侧边栏操作
}

const handleStateChange = (state) => {
  console.log('State change:', state)
  // 处理状态变化
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

// 处理问答事件
const handleQuestionAsked = (question) => {
  store.dispatch('workspace/setCurrentQuestion', question)
}

const handleAnswerReceived = (answer) => {
  const qaEntry = {
    question: store.getters['workspace/currentQuestion'],
    answer: answer,
    timestamp: new Date().toISOString()
  }
  store.dispatch('workspace/addQAHistoryItem', qaEntry)
}

const handleHistoryUpdated = (history) => {
  store.dispatch('workspace/updateQAHistory', history)
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

// 处理结果事件
const handleResultSelected = (result) => {
  store.dispatch('workspace/setCurrentResult', result)
}

const handleExportData = (data) => {
  console.log('Exporting data:', data)
}

const handleGenerateReport = (data) => {
  console.log('Generating report:', data)
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
  error.value = typeof err === 'string' ? err : getApiErrorMessage(err, '操作失败')
  errorType.value = type
}

// 隐藏错误
const hideError = () => {
  error.value = null
}

// 重试操作
const handleRetry = () => {
  hideError()
  // 可以添加重试逻辑
}

// API兼容性测试
const runAPITest = async () => {
  isRunningAPITest.value = true
  showLoading('API兼容性测试', '正在测试API连接和功能...')
  
  try {
    const results = await runAPICompatibilityTest()
    apiTestResults.value = results
    
    if (results.failed > 0) {
      showError(`API测试失败: ${results.failed}个测试未通过`, 'warning')
    } else {
      hideLoading()
      console.log('✅ API兼容性测试全部通过')
    }
  } catch (error) {
    showError(error, 'error')
  } finally {
    isRunningAPITest.value = false
    hideLoading()
  }
}

// 获取API测试结果
const getAPITestResultsLocal = () => {
  return getTestResults()
}

// 功能可用性测试
const runFunctionalityTestLocal = async () => {
  isRunningFunctionalityTest.value = true
  showLoading('功能可用性测试', '正在测试现有功能...')
  
  try {
    const results = await runFunctionalityTest()
    functionalityTestResults.value = results
    
    if (results.failed > 0) {
      showError(`功能测试失败: ${results.failed}个功能异常`, 'warning')
    } else {
      hideLoading()
      console.log('✅ 功能可用性测试全部通过')
    }
  } catch (error) {
    showError(error, 'error')
  } finally {
    isRunningFunctionalityTest.value = false
    hideLoading()
  }
}

// 获取功能测试结果
const getFunctionalityTestResultsLocal = () => {
  return getFunctionalityTestResults()
}

// 工作台集成测试
const runWorkspaceIntegrationTestLocal = async () => {
  isRunningWorkspaceIntegrationTest.value = true
  showLoading('工作台集成测试', '正在测试工作台集成...')
  
  try {
    const results = await runWorkspaceIntegrationTest()
    workspaceIntegrationTestResults.value = results
    
    if (results.failed > 0) {
      showError(`工作台集成测试失败: ${results.failed}个集成异常`, 'warning')
    } else {
      hideLoading()
      console.log('✅ 工作台集成测试全部通过')
    }
  } catch (error) {
    showError(error, 'error')
  } finally {
    isRunningWorkspaceIntegrationTest.value = false
    hideLoading()
  }
}

// 获取工作台集成测试结果
const getWorkspaceIntegrationTestResultsLocal = () => {
  return getWorkspaceIntegrationTestResults()
}

// 端到端测试
const runEndToEndTestLocal = async () => {
  isRunningEndToEndTest.value = true
  showLoading('端到端测试', '正在测试完整工作流程...')
  
  try {
    const results = await runEndToEndTest()
    endToEndTestResults.value = results
    
    if (results.failed > 0) {
      showError(`端到端测试失败: ${results.failed}个流程异常`, 'warning')
    } else {
      hideLoading()
      console.log('✅ 端到端测试全部通过')
    }
  } catch (error) {
    showError(error, 'error')
  } finally {
    isRunningEndToEndTest.value = false
    hideLoading()
  }
}

// 获取端到端测试结果
const getEndToEndTestResultsLocal = () => {
  return getEndToEndTestResults()
}

onMounted(async () => {
  // 恢复状态
  store.dispatch('workspace/restoreState')
  
  // 初始化工作台
  store.dispatch('workspace/initialize')
  
  console.log('工作台初始化完成')
})
</script>

<style scoped>
.rag-workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f8f9fa;
}

.workspace-body {
  display: flex;
  flex: 1;
  overflow: auto; /* 允许滚动 */
  min-height: 0; /* 确保flex子元素可以收缩 */
}
</style>
