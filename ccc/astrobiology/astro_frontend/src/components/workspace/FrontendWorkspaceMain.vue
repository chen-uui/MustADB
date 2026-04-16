<template>
  <main class="workspace-main">
    <!-- 陨石搜索标签页 -->
    <MeteoriteSearchTab 
      v-if="activeTab === 'meteorite-search'"
      :workspace-mode="true"
      @navigate="handleNavigate"
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
  </main>
</template>

<script setup>
import { defineAsyncComponent } from 'vue'

// 懒加载标签页组件 - 只加载前台需要的
const MeteoriteSearchTab = defineAsyncComponent(() => import('./tabs/MeteoriteSearchTab.vue'))
const IntelligentQATab = defineAsyncComponent(() => import('./tabs/IntelligentQATab.vue'))

const props = defineProps({
  activeTab: {
    type: String,
    default: 'meteorite-search'
  },
  workspaceState: {
    type: Object,
    default: () => ({})
  },
  currentDocument: Object,
  qaHistory: Array
})

const emit = defineEmits([
  'navigate',
  'state-change',
  'document-selected',
  'question-asked',
  'answer-received',
  'history-updated',
  'error'
])

const handleNavigate = (route) => {
  emit('navigate', route)
}

const handleQuestionAsked = (question) => {
  emit('question-asked', question)
}

const handleAnswerReceived = (answer) => {
  emit('answer-received', answer)
}

const handleHistoryUpdated = (history) => {
  emit('history-updated', history)
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