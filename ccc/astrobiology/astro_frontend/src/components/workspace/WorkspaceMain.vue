<template>
  <main class="workspace-main">
    <!-- 陨石搜索标签页 -->
    <MeteoriteSearchTab 
      v-if="activeTab === 'meteorite-search'"
      :workspace-mode="true"
      @navigate="handleNavigate"
      @error="handleError"
    />
    
    <!-- 文档管理标签页 -->
    <DocumentManagementTab 
      v-if="activeTab === 'documents'"
      :workspace-mode="true"
      :current-document="currentDocument"
      :workspace-state="workspaceState"
      @navigate="handleNavigate"
      @document-selected="handleDocumentSelected"
      @upload-complete="handleUploadComplete"
      @document-processed="handleDocumentProcessed"
      @error="handleError"
    />
    
    <!-- 智能问答标签页 -->
    <IntelligentQATab 
      v-if="activeTab === 'qa'"
      :workspace-mode="true"
      :current-document="currentDocument"
      :qa-history="qaHistory"
      @navigate="handleNavigate"
      @question-asked="handleQuestionAsked"
      @answer-received="handleAnswerReceived"
      @history-updated="handleHistoryUpdated"
      @error="handleError"
    />
    
    <!-- 数据提取标签页 -->
    <DataExtractionTab 
      v-if="activeTab === 'extraction'"
      :workspace-mode="true"
      :current-document="currentDocument"
      :extraction-tasks="extractionTasks"
      @navigate="handleNavigate"
      @extraction-started="handleExtractionStarted"
      @extraction-progress="handleExtractionProgress"
      @extraction-complete="handleExtractionComplete"
      @error="handleError"
    />
    
    <!-- 直接处理标签页 -->
    <DirectProcessingTab 
      v-if="activeTab === 'direct-processing'"
      :workspace-mode="true"
      @navigate="handleNavigate"
      @error="handleError"
    />
    
    <!-- 陨石数据管理标签页 -->
    <MeteoriteManagementTab 
      v-if="activeTab === 'meteorite-management'"
      :workspace-mode="true"
      @navigate="handleNavigate"
      @error="handleError"
    />
  </main>
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'

// 懒加载标签页组件 - 使用新的重构版本
const MeteoriteSearchTab = defineAsyncComponent(() => import('./tabs/MeteoriteSearchTab.vue'))
const DocumentManagementTab = defineAsyncComponent(() => import('./tabs/DocumentManagementTab.vue'))
const IntelligentQATab = defineAsyncComponent(() => import('./tabs/IntelligentQATab.vue'))
const DataExtractionTab = defineAsyncComponent(() => import('./tabs/DataExtractionTab.vue'))
const DirectProcessingTab = defineAsyncComponent(() => import('./tabs/DirectProcessingTab.vue'))
const MeteoriteManagementTab = defineAsyncComponent(() => import('./tabs/MeteoriteManagementTab.vue'))

const props = defineProps({
  activeTab: {
    type: String,
    default: 'documents'
  },
  workspaceState: {
    type: Object,
    default: () => ({})
  },
  currentDocument: Object,
  qaHistory: Array,
  extractionTasks: Array
})

const emit = defineEmits([
  'navigate',
  'state-change',
  'document-selected',
  'upload-complete',
  'document-processed',
  'question-asked',
  'answer-received',
  'history-updated',
  'extraction-started',
  'extraction-progress',
  'extraction-complete',
  'error'
])

// 计算属性
const currentDocument = computed(() => props.currentDocument || props.workspaceState.currentDocument)
const qaHistory = computed(() => props.qaHistory || props.workspaceState.qa?.history || [])
const extractionTasks = computed(() => props.extractionTasks || props.workspaceState.extraction?.tasks || [])

// 事件处理函数
const handleDocumentSelected = (document) => {
  emit('document-selected', document)
  emit('state-change', { currentDocument: document })
}

const handleUploadComplete = (result) => {
  emit('upload-complete', result)
  emit('state-change', { uploadComplete: result })
}

const handleDocumentProcessed = (result) => {
  emit('document-processed', result)
  emit('state-change', { documentProcessed: result })
}

const handleQuestionAsked = (question) => {
  emit('question-asked', question)
  emit('state-change', { currentQuestion: question })
}

const handleAnswerReceived = (answer) => {
  emit('answer-received', answer)
  emit('state-change', { currentAnswer: answer })
}

const handleHistoryUpdated = (history) => {
  emit('history-updated', history)
  emit('state-change', { qaHistory: history })
}

const handleExtractionStarted = (task) => {
  emit('extraction-started', task)
  emit('state-change', { extractionTask: task })
}

const handleExtractionProgress = (progress) => {
  emit('extraction-progress', progress)
  emit('state-change', { extractionProgress: progress })
}

const handleExtractionComplete = (result) => {
  emit('extraction-complete', result)
  emit('state-change', { extractionComplete: result })
}

const handleResultSelected = (result) => {
  emit('result-selected', result)
  emit('state-change', { selectedResult: result })
}

const handleExportData = (data) => {
  emit('export-data', data)
  emit('state-change', { exportData: data })
}

const handleGenerateReport = (data) => {
  emit('generate-report', data)
  emit('state-change', { generateReport: data })
}

const handleNavigate = (route) => {
  emit('navigate', route)
}

const handleError = (error) => {
  emit('error', error)
  emit('state-change', { error: error })
}
</script>

<style scoped>
.workspace-main {
  flex: 1;
  background: white;
  overflow: auto; /* 允许滚动 */
  display: flex;
  flex-direction: column;
  min-height: 0; /* 确保flex子元素可以收缩 */
}

/* 标签页样式已在各个组件中定义 */
</style>
