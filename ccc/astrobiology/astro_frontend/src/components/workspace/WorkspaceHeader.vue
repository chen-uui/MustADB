<template>
  <header class="workspace-header">
    <div class="header-container">
      <div class="header-left">
        <div class="logo">
          <div class="logo-icon-wrapper">
            <svg class="logo-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7v10c0 5.55 3.84 10 9 9 5.16-1 9-5.45 9-9V7l-10-5z"/>
              <path d="M12 8v8M8 12h8"/>
            </svg>
          </div>
          <div class="logo-text-wrapper">
            <span class="logo-text">RAG智能工作台</span>
            <span class="logo-subtitle">Intelligent RAG Workspace</span>
          </div>
        </div>
      </div>
      
      <div class="header-center">
        <nav class="tab-navigation">
          <button 
            v-for="tab in tabs"
            :key="tab.id"
            :class="['tab-button', { active: activeTab === tab.id }]"
            @click="$emit('tab-change', tab.id)"
            :title="tab.description"
          >
            <i :class="tab.icon"></i>
            <span class="tab-label">{{ tab.label }}</span>
          </button>
        </nav>
      </div>
      
      <div class="system-health-section">
        <button class="home-button" @click="$emit('navigate', 'system-health')">
          <i class="bi bi-activity"></i>
          <span>系统健康</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'documents'
  }
})

const emit = defineEmits(['tab-change', 'navigate'])

// 标签页配置
const tabs = [
  {
    id: 'meteorite-search',
    label: '陨石搜索',
    icon: 'bi bi-search',
    description: '搜索陨石数据'
  },
  {
    id: 'documents',
    label: '文档管理',
    icon: 'bi bi-file-earmark-text',
    description: '上传和管理PDF文档'
  },
  {
    id: 'qa',
    label: '智能问答',
    icon: 'bi bi-chat-dots',
    description: '基于文档的AI问答'
  },
  {
    id: 'extraction',
    label: '数据提取',
    icon: 'bi bi-gear',
    description: '智能提取陨石数据'
  },
  {
    id: 'direct-processing',
    label: '直接处理',
    icon: 'bi bi-lightning',
    description: 'AI直接分析文档'
  },
  {
    id: 'meteorite-management',
    label: '陨石数据管理',
    icon: 'bi bi-database',
    description: '管理已审核通过的陨石数据'
  }
]

// 状态指示器
const statusClass = computed(() => {
  // 根据当前状态返回不同的样式类
  return 'status-idle'
})

const statusText = computed(() => {
  // 根据当前状态返回状态文本
  return '就绪'
})
</script>

<style scoped>
.workspace-header {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-bottom: 1px solid rgba(226, 232, 240, 0.8);
  padding: 0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  position: relative;
  z-index: 100;
}

.workspace-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.3), transparent);
}

.header-container {
  max-width: 1920px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}

.header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: scale(1.02);
}

.logo-icon-wrapper {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
}

.logo:hover .logo-icon-wrapper {
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
  transform: rotate(5deg);
}

.logo-icon {
  color: white;
  width: 24px;
  height: 24px;
}

.logo-text-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.logo-text {
  font-size: 1.25rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.logo-subtitle {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 500;
  letter-spacing: 0.05em;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.tab-navigation {
  display: flex;
  gap: 0.5rem;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #6c757d;
  font-weight: 500;
}

.tab-button:hover {
  background: #f8f9fa;
  color: #495057;
}

.tab-button.active {
  background: #007bff;
  color: white;
}

.tab-button i {
  font-size: 1.125rem;
}

.tab-label {
  font-size: 0.9375rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.status-indicator.status-idle {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-indicator.status-processing {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(245, 158, 11, 0.05) 100%);
  color: #d97706;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.status-indicator.status-error {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(239, 68, 68, 0.05) 100%);
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.home-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: #64748b;
  font-weight: 500;
  font-size: 0.9375rem;
}

.home-button:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border-color: #667eea;
  color: #667eea;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* 响应式设计 */
@media (max-width: 1199px) {
  .tab-navigation {
    flex-wrap: wrap;
  }
  
  .tab-button {
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
  }
}

@media (max-width: 767px) {
  .workspace-header {
    flex-direction: column;
    gap: 1rem;
  }
  
  .header-center {
    order: 1;
  }
  
  .header-left,
  .header-right {
    order: 2;
  }
  
  .tab-navigation {
    flex-direction: column;
    width: 100%;
  }
  
  .tab-button {
    justify-content: center;
  }
}
</style>
