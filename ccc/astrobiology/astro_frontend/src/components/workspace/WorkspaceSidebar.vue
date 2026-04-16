<template>
  <aside class="workspace-sidebar">
    <!-- 当前文档信息 -->
    <div class="current-document" v-if="currentDocument">
      <h4>当前文档</h4>
      <div class="document-info">
        <div class="document-name">{{ currentDocument.name }}</div>
        <div class="document-status" :class="currentDocument.status">
          {{ getStatusText(currentDocument.status) }}
        </div>
      </div>
    </div>
    
    <!-- 快速操作 -->
    <div class="quick-actions">
      <h4>快速操作</h4>
      <div class="action-buttons">
        <button 
          v-for="action in quickActions"
          :key="action.id"
          :class="['action-btn', { disabled: !action.enabled }]"
          @click="handleAction(action)"
        >
          <i :class="action.icon"></i>
          {{ action.label }}
        </button>
      </div>
    </div>
    
    <!-- 工作流进度 -->
    <div class="workflow-progress">
      <h4>工作流进度</h4>
      <div class="progress-steps">
        <div 
          v-for="step in workflowSteps" 
          :key="step.id"
          :class="['progress-step', { active: step.active, completed: step.completed }]"
        >
          <div class="step-indicator">
            <i v-if="step.completed" class="bi bi-check-circle-fill"></i>
            <i v-else-if="step.active" class="bi bi-circle-fill"></i>
            <i v-else class="bi bi-circle"></i>
          </div>
          <div class="step-content">
            <div class="step-title">{{ step.title }}</div>
            <div class="step-desc">{{ step.description }}</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 系统状态 -->
    <div class="system-status">
      <h4>统计信息</h4>
      <div class="status-items">
        <div class="status-item">
          <div class="status-icon">
            <i class="bi bi-file-earmark-text"></i>
          </div>
          <div class="status-content">
            <span class="status-label">文档总数</span>
            <span class="status-value">{{ documentCount }}</span>
          </div>
        </div>
        <div class="status-item">
          <div class="status-icon">
            <i class="bi bi-chat-dots"></i>
          </div>
          <div class="status-content">
            <span class="status-label">问答记录</span>
            <span class="status-value">{{ qaCount }}</span>
          </div>
        </div>
        <div class="status-item">
          <div class="status-icon">
            <i class="bi bi-database"></i>
          </div>
          <div class="status-content">
            <span class="status-label">提取任务</span>
            <span class="status-value">{{ extractionCount }}</span>
          </div>
        </div>
        <div class="status-item">
          <div class="status-icon status-icon-ai">
            <i class="bi bi-cpu"></i>
          </div>
          <div class="status-content">
            <span class="status-label">AI状态</span>
            <span class="status-value status-connected">
              <span class="status-dot"></span>
              运行中
            </span>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'documents'
  },
  workspaceState: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['action'])

// 计算属性
const currentDocument = computed(() => props.workspaceState.currentDocument)
const systemStatus = computed(() => props.workspaceState.systemStatus || {})

// 统计数据
const documentCount = computed(() => {
  return props.workspaceState.documents?.list?.length || 0
})

const qaCount = computed(() => {
  return props.workspaceState.qa?.history?.length || 0
})

const extractionCount = computed(() => {
  return props.workspaceState.extraction?.tasks?.length || 0
})

// 工作流步骤
const workflowSteps = computed(() => [
  {
    id: 'documents',
    title: '文档管理',
    description: '上传和管理文档',
    active: props.activeTab === 'documents',
    completed: props.workspaceState.documents?.list?.length > 0
  },
  {
    id: 'qa',
    title: '智能问答',
    description: 'AI问答分析',
    active: props.activeTab === 'qa',
    completed: props.workspaceState.qa?.history?.length > 0
  },
  {
    id: 'extraction',
    title: '数据提取',
    description: '提取结构化数据',
    active: props.activeTab === 'extraction',
    completed: props.workspaceState.extraction?.tasks?.length > 0
  },
  {
    id: 'results',
    title: '分析结果',
    description: '查看分析结果',
    active: props.activeTab === 'results',
    completed: props.workspaceState.results?.extractedData?.length > 0
  }
])

// 快速操作配置
const quickActions = computed(() => [
  {
    id: 'upload',
    label: '上传文档',
    icon: 'bi bi-upload',
    enabled: true
  },
  {
    id: 'process',
    label: '处理文档',
    icon: 'bi bi-gear',
    enabled: !!currentDocument.value
  },
  {
    id: 'extract',
    label: '提取数据',
    icon: 'bi bi-database',
    enabled: !!currentDocument.value
  },
  {
    id: 'ask',
    label: '智能问答',
    icon: 'bi bi-chat',
    enabled: !!currentDocument.value
  }
])

// 方法
const getStatusText = (status) => {
  const statusMap = {
    'uploaded': '已上传',
    'processing': '处理中',
    'processed': '已处理',
    'error': '错误',
    'deleted': '已删除'
  }
  return statusMap[status] || '未知'
}

const handleAction = (action) => {
  if (!action.enabled) return
  
  emit('action', {
    type: action.id,
    data: action
  })
}
</script>

<style scoped>
.workspace-sidebar {
  width: 320px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border-right: 1px solid rgba(226, 232, 240, 0.8);
  padding: 1.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  box-shadow: 4px 0 6px -1px rgba(0, 0, 0, 0.05);
}

.current-document {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  padding: 1.25rem;
  border-radius: 1rem;
  border: 1px solid rgba(102, 126, 234, 0.2);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.current-document:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.current-document h4 {
  margin: 0 0 0.75rem 0;
  font-size: 0.9375rem;
  font-weight: 700;
  color: #667eea;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.current-document h4::before {
  content: '';
  width: 4px;
  height: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
}

.document-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.document-name {
  font-weight: 500;
  color: #2c3e50;
  word-break: break-word;
}

.document-status {
  font-size: 0.875rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  display: inline-block;
  width: fit-content;
}

.document-status.uploaded {
  background: #d1ecf1;
  color: #0c5460;
}

.document-status.processing {
  background: #fff3cd;
  color: #856404;
}

.document-status.processed {
  background: #d4edda;
  color: #155724;
}

.document-status.error {
  background: #f8d7da;
  color: #721c24;
}

.quick-actions h4,
.workflow-progress h4,
.system-status h4 {
  margin: 0 0 1rem 0;
  font-size: 0.9375rem;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e2e8f0;
}

.quick-actions h4::before,
.workflow-progress h4::before,
.system-status h4::before {
  content: '';
  width: 4px;
  height: 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
}

.workflow-progress {
  background: var(--workspace-surface);
  padding: 1.25rem;
  border-radius: 1rem;
  border: 1px solid var(--workspace-border);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.progress-steps {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.progress-step {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.75rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.progress-step:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  transform: translateX(4px);
}

.progress-step.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-left: 3px solid #667eea;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
}

.progress-step.completed .step-title {
  color: #28a745;
}

.step-indicator {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f1f5f9;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.progress-step.active .step-indicator {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.progress-step.completed .step-indicator {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.step-indicator i {
  font-size: 1rem;
  color: #64748b;
}

.progress-step.active .step-indicator i {
  color: white;
}

.progress-step.completed .step-indicator i {
  color: white;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: #495057;
  margin-bottom: 0.25rem;
}

.step-desc {
  font-size: 0.75rem;
  color: #6c757d;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  border: 1px solid var(--workspace-border);
  background: var(--workspace-surface);
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: var(--workspace-text);
  font-weight: 500;
  text-align: left;
  position: relative;
  overflow: hidden;
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.1), transparent);
  transition: left 0.5s ease;
}

.action-btn:hover:not(.disabled)::before {
  left: 100%;
}

.action-btn:hover:not(.disabled) {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border-color: var(--workspace-primary);
  transform: translateY(-2px);
  box-shadow: var(--workspace-shadow);
}

.action-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f8f9fa;
  color: #6c757d;
}

.action-btn i {
  font-size: 1rem;
  width: 1rem;
  text-align: center;
}

.system-status {
  background: var(--workspace-surface);
  padding: 1.25rem;
  border-radius: 1rem;
  border: 1px solid var(--workspace-border);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.status-items {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.5rem;
  background: #f8fafc;
  transition: all 0.2s ease;
}

.status-item:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  transform: translateX(2px);
}

.status-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-radius: 0.5rem;
  color: #667eea;
  flex-shrink: 0;
}

.status-icon i {
  font-size: 1rem;
}

.status-icon-ai {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%);
  color: #10b981;
}

.status-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.status-label {
  font-size: 0.75rem;
  color: #64748b;
  font-weight: 500;
}

.status-value {
  font-size: 1rem;
  font-weight: 700;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-connected {
  color: #10b981;
}

.status-connected .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  animation: pulse 2s infinite;
}

/* 响应式设计 */
@media (max-width: 1199px) {
  .workspace-sidebar {
    width: 250px;
  }
}

@media (max-width: 767px) {
  .workspace-sidebar {
    width: 100%;
    height: auto;
    max-height: 200px;
    order: 2;
  }
  
  .workspace-sidebar {
    flex-direction: row;
    overflow-x: auto;
    gap: 1rem;
  }
  
  .current-document,
  .quick-actions,
  .system-status {
    min-width: 200px;
    flex-shrink: 0;
  }
}
</style>
