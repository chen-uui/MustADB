<template>
  <div class="smart-assistant" v-if="showAssistant">
    <div class="assistant-card">
      <div class="assistant-header">
        <div class="assistant-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7v10c0 5.55 3.84 10 9 9 5.16-1 9-5.45 9-9V7l-10-5z"/>
            <path d="M12 8v8M8 12h8"/>
          </svg>
        </div>
        <div class="assistant-title">
          <h4>智能助手</h4>
          <p>为你提供工作流建议</p>
        </div>
        <button class="close-btn" @click="closeAssistant">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      
      <div class="assistant-suggestions">
        <div 
          v-for="suggestion in suggestions" 
          :key="suggestion.id"
          class="suggestion-item"
          @click="handleSuggestion(suggestion)"
        >
          <div class="suggestion-icon" :class="suggestion.type">
            <i :class="suggestion.icon"></i>
          </div>
          <div class="suggestion-content">
            <div class="suggestion-title">{{ suggestion.title }}</div>
            <div class="suggestion-desc">{{ suggestion.description }}</div>
          </div>
          <div class="suggestion-arrow">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="5" y1="12" x2="19" y2="12"/>
              <polyline points="12 5 19 12 12 19"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'documents'
  },
  documentCount: {
    type: Number,
    default: 0
  },
  hasDocuments: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['action', 'close'])

const showAssistant = ref(true)

// 智能建议
const suggestions = computed(() => {
  const baseSuggestions = []
  
  // 根据当前状态生成建议
  if (props.activeTab === 'documents') {
    if (props.documentCount === 0) {
      baseSuggestions.push({
        id: 'upload-first',
        type: 'upload',
        icon: 'bi bi-cloud-upload',
        title: '上传第一个文档',
        description: '开始上传PDF文档进行AI分析',
        action: 'upload'
      })
    } else {
      baseSuggestions.push({
        id: 'search-docs',
        type: 'search',
        icon: 'bi bi-search',
        title: '搜索文档',
        description: '快速查找所需的文档',
        action: 'search'
      })
    }
  }
  
  if (props.hasDocuments && props.activeTab !== 'qa') {
    baseSuggestions.push({
      id: 'try-qa',
      type: 'qa',
      icon: 'bi bi-chat-dots',
      title: '尝试智能问答',
      description: '向AI询问文档中的信息',
      action: 'switch-tab',
      targetTab: 'qa'
    })
  }
  
  if (props.activeTab === 'qa') {
    baseSuggestions.push({
      id: 'example-questions',
      type: 'example',
      icon: 'bi bi-lightbulb',
      title: '查看示例问题',
      description: '了解可以问什么类型的问题',
      action: 'show-examples'
    })
  }
  
  // 始终显示的通用建议
  baseSuggestions.push({
    id: 'view-recent',
    type: 'history',
    icon: 'bi bi-clock-history',
    title: '查看最近活动',
    description: '浏览最近的操作记录',
    action: 'view-history'
  })
  
  return baseSuggestions
})

const handleSuggestion = (suggestion) => {
  emit('action', {
    type: suggestion.action,
    data: suggestion
  })
}

const closeAssistant = () => {
  showAssistant.value = false
  emit('close')
}

onMounted(() => {
  // 可以添加一些初始化逻辑
})
</script>

<style scoped>
.smart-assistant {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
  animation: slideInUp 0.3s ease-out;
}

@keyframes slideInUp {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.assistant-card {
  width: 360px;
  background: white;
  border-radius: 1rem;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.assistant-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.25rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.assistant-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.75rem;
}

.assistant-icon svg {
  width: 24px;
  height: 24px;
}

.assistant-title {
  flex: 1;
}

.assistant-title h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
}

.assistant-title p {
  margin: 0.25rem 0 0 0;
  font-size: 0.75rem;
  opacity: 0.9;
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  color: white;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: rotate(90deg);
}

.assistant-suggestions {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid #e2e8f0;
  background: white;
}

.suggestion-item:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border-color: #667eea;
  transform: translateX(4px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.suggestion-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.75rem;
  flex-shrink: 0;
}

.suggestion-icon.upload {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%);
  color: #3b82f6;
}

.suggestion-icon.search {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
  color: #10b981;
}

.suggestion-icon.qa {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(102, 126, 234, 0.05) 100%);
  color: #667eea;
}

.suggestion-icon.example {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%);
  color: #f59e0b;
}

.suggestion-icon.history {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%);
  color: #8b5cf6;
}

.suggestion-icon i {
  font-size: 1.25rem;
}

.suggestion-content {
  flex: 1;
  min-width: 0;
}

.suggestion-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.25rem;
}

.suggestion-desc {
  font-size: 0.8125rem;
  color: #64748b;
  line-height: 1.4;
}

.suggestion-arrow {
  flex-shrink: 0;
  color: #cbd5e1;
  transition: all 0.3s ease;
}

.suggestion-item:hover .suggestion-arrow {
  color: #667eea;
  transform: translateX(4px);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .smart-assistant {
    bottom: 16px;
    right: 16px;
    left: 16px;
  }
  
  .assistant-card {
    width: 100%;
  }
}
</style>




