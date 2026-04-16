<template>
  <div v-if="error" class="error-notification" :class="type">
    <div class="error-content">
      <div class="error-icon">
        <i :class="iconClass"></i>
      </div>
      <div class="error-text">
        <h4>{{ title }}</h4>
        <p>{{ message }}</p>
        <div v-if="details" class="error-details">
          <details>
            <summary>详细信息</summary>
            <pre>{{ details }}</pre>
          </details>
        </div>
      </div>
      <div class="error-actions">
        <button v-if="showRetry" @click="handleRetry" class="retry-btn">
          <i class="bi bi-arrow-clockwise"></i>
          重试
        </button>
        <button @click="handleDismiss" class="dismiss-btn">
          <i class="bi bi-x"></i>
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  error: {
    type: [Object, String, null],
    default: null
  },
  type: {
    type: String,
    default: 'error', // error, warning, info
    validator: (value) => ['error', 'warning', 'info'].includes(value)
  },
  showRetry: {
    type: Boolean,
    default: true
  },
  autoDismiss: {
    type: Boolean,
    default: false
  },
  dismissDelay: {
    type: Number,
    default: 5000
  }
})

const emit = defineEmits(['retry', 'dismiss'])

const title = computed(() => {
  if (typeof props.error === 'string') {
    return '发生错误'
  }
  return props.error?.title || getDefaultTitle()
})

const message = computed(() => {
  if (typeof props.error === 'string') {
    return props.error
  }
  return props.error?.message || props.error?.error || '未知错误'
})

const details = computed(() => {
  if (typeof props.error === 'object' && props.error?.details) {
    return props.error.details
  }
  return null
})

const iconClass = computed(() => {
  const icons = {
    error: 'bi bi-exclamation-triangle',
    warning: 'bi bi-exclamation-circle',
    info: 'bi bi-info-circle'
  }
  return icons[props.type] || icons.error
})

function getDefaultTitle() {
  const titles = {
    error: '发生错误',
    warning: '警告',
    info: '提示'
  }
  return titles[props.type] || titles.error
}

function handleRetry() {
  emit('retry', props.error)
}

function handleDismiss() {
  emit('dismiss')
}

// 自动关闭
if (props.autoDismiss) {
  setTimeout(() => {
    handleDismiss()
  }, props.dismissDelay)
}
</script>

<style scoped>
.error-notification {
  position: fixed;
  top: 20px;
  right: 20px;
  max-width: 400px;
  z-index: 10000;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.error-notification.error .error-content {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.error-notification.warning .error-content {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
}

.error-notification.info .error-content {
  background: #d1ecf1;
  border: 1px solid #bee5eb;
  color: #0c5460;
}

.error-icon {
  flex-shrink: 0;
  font-size: 1.5rem;
}

.error-text {
  flex: 1;
}

.error-text h4 {
  margin: 0 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
}

.error-text p {
  margin: 0 0 0.5rem 0;
  font-size: 0.9rem;
  line-height: 1.4;
}

.error-details {
  margin-top: 0.5rem;
}

.error-details details {
  font-size: 0.8rem;
}

.error-details summary {
  cursor: pointer;
  font-weight: 500;
}

.error-details pre {
  margin: 0.5rem 0 0 0;
  padding: 0.5rem;
  background: rgba(0, 0, 0, 0.1);
  border-radius: 0.25rem;
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.error-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex-shrink: 0;
}

.retry-btn, .dismiss-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  border: none;
  border-radius: 0.25rem;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-btn {
  background: #007bff;
  color: white;
}

.retry-btn:hover {
  background: #0056b3;
}

.dismiss-btn {
  background: rgba(0, 0, 0, 0.1);
  color: inherit;
}

.dismiss-btn:hover {
  background: rgba(0, 0, 0, 0.2);
}

@media (max-width: 768px) {
  .error-notification {
    top: 10px;
    right: 10px;
    left: 10px;
    max-width: none;
  }
  
  .error-content {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .error-actions {
    flex-direction: row;
    justify-content: flex-end;
  }
}
</style>
