<template>
  <div class="frontend-workspace">
    <!-- Navigation Bar -->
    <div class="workspace-nav">
      <button class="back-home-btn" @click="handleNavigate('/')">
        <i class="bi bi-arrow-left"></i>
        <span>Back to Home</span>
      </button>
      
      <!-- Tab Switcher -->
      <div class="workspace-tabs">
        <button 
          v-for="tab in tabs" 
          :key="tab.id"
          :class="['tab-button', { active: activeTab === tab.id }]"
          @click="handleTabChange(tab.id)"
        >
          <i :class="tab.icon"></i>
          <span>{{ tab.label }}</span>
        </button>
      </div>
      
      <!-- Placeholder for balance -->
      <div class="nav-placeholder"></div>
    </div>
    
    <div class="workspace-body">
      <FrontendWorkspaceMain 
        :active-tab="activeTab"
        :workspace-state="workspaceState"
        :current-document="currentDocument"
        :qa-history="qaHistory"
        @state-change="handleStateChange"
        @document-selected="handleDocumentSelected"
        @question-asked="handleQuestionAsked"
        @answer-received="handleAnswerReceived"
        @history-updated="handleHistoryUpdated"
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
import FrontendWorkspaceMain from '@/components/workspace/FrontendWorkspaceMain.vue'
import LoadingOverlay from '@/components/workspace/LoadingOverlay.vue'
import ErrorNotification from '@/components/workspace/ErrorNotification.vue'

const store = useStore()
const emit = defineEmits(['navigate'])

// Tabs definition
const tabs = [
  { id: 'meteorite-search', label: 'Meteorite Search', icon: 'bi bi-search' },
  { id: 'qa', label: 'AI Q&A', icon: 'bi bi-chat-dots' }
]

// 响应式数据
const frontendTabIds = new Set(tabs.map((tab) => tab.id))
const normalizeFrontendTab = (tabId) => {
  if (tabId === 'intelligent-qa') {
    return 'qa'
  }
  if (frontendTabIds.has(tabId)) {
    return tabId
  }
  return 'meteorite-search'
}
const activeTab = computed(() => normalizeFrontendTab(store.getters['workspace/activeTab']))

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

// 加载状态
const isLoading = ref(false)
const loadingTitle = ref('')
const loadingMessage = ref('')
const loadingProgress = ref(null)

// 错误状态
const error = ref(null)
const errorType = ref('error')
const syncFrontendTab = (preferredTab = null) => {
  const current = store.getters['workspace/activeTab']
  const next = normalizeFrontendTab(preferredTab || current)
  if (current !== next) {
    store.dispatch('workspace/switchTab', next)
  }
  return next
}

// 导航处理
const handleNavigate = (route) => {
  if (route === 'meteorite-search' || route === 'qa') {
    store.dispatch('workspace/switchTab', normalizeFrontendTab(route))
    store.dispatch('workspace/saveState')
    return
  }
  emit('navigate', route)
}

// 标签切换处理
const handleTabChange = (tabId) => {
  store.dispatch('workspace/switchTab', normalizeFrontendTab(tabId))
  store.dispatch('workspace/saveState')
}

const handleStateChange = (state) => {
  console.log('State change:', state)
}

// 处理文档选择
const handleDocumentSelected = (document) => {
  store.dispatch('workspace/setCurrentDocument', document)
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

// 处理错误
const handleError = (err) => {
  console.error('Workspace error:', err)
  error.value = err
  errorType.value = 'error'
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
  const requestedTab = new URLSearchParams(window.location.search).get('tab')
  syncFrontendTab(requestedTab)
  
  console.log('前台工作台初始化完成')
})
</script>

<style scoped>
.frontend-workspace {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  position: relative;
  z-index: 10;
}

.workspace-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  position: relative;
  z-index: 20;
}

.back-home-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 9999px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.9rem;
  backdrop-filter: blur(4px);
}

.back-home-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transform: translateX(-2px);
}

.nav-placeholder {
  width: 120px; /* Approximate width of back button for centering tabs */
}

.workspace-tabs-container {
  /* Removed as tabs are now in nav */
  display: none; 
}

.workspace-tabs {
  display: flex;
  background: rgba(30, 41, 59, 0.4);
  backdrop-filter: blur(12px);
  padding: 0.5rem;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  gap: 0.5rem;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: 500;
  font-size: 0.95rem;
}

.tab-button:hover {
  color: white;
  background: rgba(255, 255, 255, 0.05);
}

.tab-button.active {
  background: linear-gradient(135deg, #3fbbc0 0%, #1071fb 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(16, 113, 251, 0.3);
}

.tab-button i {
  font-size: 1.1rem;
}

.workspace-body {
  flex: 1;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem 4rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .frontend-workspace {
    padding-top: 80px;
  }
  
  .workspace-body {
    padding: 0 1rem 2rem;
  }
  
  .tab-button {
    padding: 0.6rem 1rem;
    font-size: 0.9rem;
  }
}
</style>

