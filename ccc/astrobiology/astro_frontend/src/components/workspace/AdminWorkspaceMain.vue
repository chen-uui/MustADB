<template>
  <main class="workspace-main">
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
import { defineAsyncComponent } from 'vue'

// 懒加载标签页组件 - 后台管理功能
const DocumentManagementTab = defineAsyncComponent(() => import('./tabs/DocumentManagementTab.vue'))
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
  extractionTasks: Array
})

const emit = defineEmits([
  'navigate',
  'state-change',
  'document-selected',
  'upload-complete',
  'document-processed',
  'extraction-started',
  'extraction-progress',
  'extraction-complete',
  'error'
])

const handleNavigate = (route) => {
  emit('navigate', route)
}

const handleDocumentSelected = (document) => {
  emit('document-selected', document)
}

const handleUploadComplete = (result) => {
  emit('upload-complete', result)
}

const handleDocumentProcessed = (result) => {
  emit('document-processed', result)
}

const handleExtractionStarted = (task) => {
  emit('extraction-started', task)
}

const handleExtractionProgress = (progress) => {
  emit('extraction-progress', progress)
}

const handleExtractionComplete = (result) => {
  emit('extraction-complete', result)
}

const handleError = (error) => {
  emit('error', error)
}
</script>

<style scoped>
.workspace-main {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}
</style>

