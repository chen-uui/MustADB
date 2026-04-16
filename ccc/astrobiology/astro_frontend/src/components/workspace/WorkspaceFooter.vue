<template>
  <footer class="workspace-footer">
    <div class="footer-left">
      <div class="processing-status" v-if="processingStatus !== 'idle'">
        <div class="progress-bar">
          <div 
            class="progress-fill" 
            :style="{ width: processingProgress + '%' }"
          ></div>
        </div>
        <span class="progress-text">{{ processingStatusText }}</span>
      </div>
    </div>
    
    <div class="footer-center">
      <div class="system-messages">
        <span 
          v-for="message in systemMessages"
          :key="message.id"
          :class="['message', message.type]"
        >
          {{ message.text }}
        </span>
      </div>
    </div>
    
    <div class="footer-right">
      <div class="api-status" v-if="apiTestResults">
        <span class="api-label">API:</span>
        <span class="api-value" :class="apiTestResults.failed > 0 ? 'warning' : 'success'">
          {{ apiTestResults.failed > 0 ? `${apiTestResults.failed}个问题` : '正常' }}
        </span>
        <button @click="showAPIDetails" class="api-details-btn" title="查看API测试详情">
          <i class="bi bi-info-circle"></i>
        </button>
      </div>
      
      <div class="connection-status">
        <i :class="connectionIcon"></i>
        <span>{{ connectionStatus }}</span>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessageBox } from 'element-plus'

const props = defineProps({
  processingStatus: {
    type: String,
    default: 'idle'
  },
  systemStatus: {
    type: Object,
    default: () => ({})
  },
  apiTestResults: {
    type: Object,
    default: null
  }
})

// 响应式数据
const processingProgress = ref(0)
const systemMessages = ref([])

// 计算属性
const processingStatusText = computed(() => {
  const statusMap = {
    'idle': '就绪',
    'uploading': '上传中...',
    'processing': '处理中...',
    'extracting': '提取中...',
    'completed': '完成',
    'error': '错误'
  }
  return statusMap[props.processingStatus] || '未知状态'
})

const connectionStatus = computed(() => {
  const s = props.systemStatus || {}
  const ok = !!(s.weaviate_connected && s.llm_connected)
  return ok ? '已连接' : '未连接'
})

const connectionIcon = computed(() => {
  const s = props.systemStatus || {}
  const ok = !!(s.weaviate_connected && s.llm_connected)
  return ok ? 'bi bi-wifi' : 'bi bi-wifi-off'
})

// 模拟进度更新
const updateProgress = () => {
  if (props.processingStatus === 'processing' || props.processingStatus === 'extracting') {
    processingProgress.value = Math.min(processingProgress.value + 10, 100)
  } else if (props.processingStatus === 'completed') {
    processingProgress.value = 100
  } else {
    processingProgress.value = 0
  }
}

// 添加系统消息
const addSystemMessage = (message, type = 'info') => {
  const id = Date.now()
  systemMessages.value.push({
    id,
    text: message,
    type
  })
  
  // 5秒后自动移除消息
  setTimeout(() => {
    const index = systemMessages.value.findIndex(msg => msg.id === id)
    if (index > -1) {
      systemMessages.value.splice(index, 1)
    }
  }, 5000)
}

// 监听状态变化
const watchStatus = () => {
  if (props.processingStatus === 'processing') {
    addSystemMessage('开始处理文档...', 'info')
  } else if (props.processingStatus === 'completed') {
    addSystemMessage('处理完成！', 'success')
  } else if (props.processingStatus === 'error') {
    addSystemMessage('处理失败，请重试', 'error')
  }
}

// 显示API详情
const showAPIDetails = () => {
  if (props.apiTestResults) {
    console.log('API测试详情:', props.apiTestResults)
    ElMessageBox.alert(
      `通过: ${props.apiTestResults.passed}\n失败: ${props.apiTestResults.failed}\n总计: ${props.apiTestResults.total}`,
      'API测试结果',
      {
        confirmButtonText: '确定'
      }
    )
  }
}

// 暴露方法给父组件
defineExpose({
  addSystemMessage,
  updateProgress,
  showAPIDetails
})
</script>

<style scoped>
.workspace-footer {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 60px;
  color: rgba(255, 255, 255, 0.8);
}

.footer-left {
  flex: 1;
  display: flex;
  align-items: center;
}

.processing-status {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-bar {
  width: 200px;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007bff, #0056b3);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.875rem;
  color: #495057;
  font-weight: 500;
}

.footer-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.system-messages {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  max-height: 60px;
  overflow-y: auto;
}

.message {
  font-size: 0.875rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  animation: slideIn 0.3s ease;
}

.message.info {
  background: #d1ecf1;
  color: #0c5460;
}

.message.success {
  background: #d4edda;
  color: #155724;
}

.message.error {
  background: #f8d7da;
  color: #721c24;
}

.message.warning {
  background: #fff3cd;
  color: #856404;
}

.footer-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #6c757d;
}

.connection-status i {
  font-size: 1rem;
}

.connection-status i.bi-wifi {
  color: #28a745;
}

.connection-status i.bi-wifi-off {
  color: #dc3545;
}

.api-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-right: 1rem;
  font-size: 0.875rem;
}

.api-label {
  color: #6c757d;
  font-weight: 500;
}

.api-value {
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 500;
}

.api-value.success {
  background: #d4edda;
  color: #155724;
}

.api-value.warning {
  background: #fff3cd;
  color: #856404;
}

.api-details-btn {
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 0.25rem;
  transition: all 0.2s ease;
}

.api-details-btn:hover {
  background: #e9ecef;
  color: #495057;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式设计 */
@media (max-width: 767px) {
  .workspace-footer {
    flex-direction: column;
    gap: 0.5rem;
    padding: 0.5rem;
  }
  
  .footer-left,
  .footer-center,
  .footer-right {
    flex: none;
    width: 100%;
  }
  
  .progress-bar {
    width: 150px;
  }
  
  .system-messages {
    max-height: 40px;
  }
}
</style>
