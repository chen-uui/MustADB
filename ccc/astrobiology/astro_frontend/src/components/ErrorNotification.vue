<template>
  <div v-if="visible" class="error-notification" :class="notificationClass">
    <div class="notification-header">
      <i :class="iconClass"></i>
      <span class="notification-title">{{ title }}</span>
      <button @click="close" class="close-btn">×</button>
    </div>
    <div class="notification-content">
      <p class="notification-message">{{ message }}</p>
      <div v-if="details" class="notification-details">
        <button @click="toggleDetails" class="details-toggle">
          {{ showDetails ? '隐藏详情' : '查看详情' }}
          <i :class="showDetails ? 'fas fa-chevron-up' : 'fas fa-chevron-down'"></i>
        </button>
        <div v-if="showDetails" class="details-content">
          <pre>{{ details }}</pre>
        </div>
      </div>
      <div v-if="actions && actions.length > 0" class="notification-actions">
        <button 
          v-for="action in actions" 
          :key="action.label"
          @click="action.handler"
          :class="['action-btn', action.type || 'primary']"
        >
          {{ action.label }}
        </button>
      </div>
    </div>
    <div v-if="autoClose" class="progress-bar">
      <div class="progress-fill" :style="{ width: progressWidth + '%' }"></div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ErrorNotification',
  props: {
    type: {
      type: String,
      default: 'error',
      validator: value => ['success', 'warning', 'error', 'info'].includes(value)
    },
    title: {
      type: String,
      default: ''
    },
    message: {
      type: String,
      required: true
    },
    details: {
      type: String,
      default: ''
    },
    actions: {
      type: Array,
      default: () => []
    },
    autoClose: {
      type: Boolean,
      default: true
    },
    duration: {
      type: Number,
      default: 5000
    },
    persistent: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      visible: false,
      showDetails: false,
      progressWidth: 100,
      timer: null,
      progressTimer: null
    }
  },
  computed: {
    notificationClass() {
      return [
        `notification-${this.type}`,
        { 'notification-persistent': this.persistent }
      ]
    },
    iconClass() {
      const icons = {
        success: 'fas fa-check-circle',
        warning: 'fas fa-exclamation-triangle',
        error: 'fas fa-times-circle',
        info: 'fas fa-info-circle'
      }
      return icons[this.type] || icons.info
    }
  },
  methods: {
    show() {
      this.visible = true
      if (this.autoClose && !this.persistent) {
        this.startAutoClose()
      }
    },
    close() {
      this.visible = false
      this.clearTimers()
      this.$emit('close')
    },
    toggleDetails() {
      this.showDetails = !this.showDetails
    },
    startAutoClose() {
      this.progressWidth = 100
      
      // 进度条动画
      this.progressTimer = setInterval(() => {
        this.progressWidth -= (100 / (this.duration / 100))
        if (this.progressWidth <= 0) {
          this.progressWidth = 0
          clearInterval(this.progressTimer)
        }
      }, 100)
      
      // 自动关闭定时器
      this.timer = setTimeout(() => {
        this.close()
      }, this.duration)
    },
    clearTimers() {
      if (this.timer) {
        clearTimeout(this.timer)
        this.timer = null
      }
      if (this.progressTimer) {
        clearInterval(this.progressTimer)
        this.progressTimer = null
      }
    }
  },
  mounted() {
    this.show()
  },
  beforeUnmount() {
    this.clearTimers()
  }
}
</script>

<style scoped>
.error-notification {
  position: fixed;
  top: 20px;
  right: 20px;
  min-width: 320px;
  max-width: 500px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  overflow: hidden;
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

.notification-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
}

.notification-header i {
  font-size: 18px;
  margin-right: 8px;
}

.notification-title {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #6b7280;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #374151;
}

.notification-content {
  padding: 12px 16px;
}

.notification-message {
  margin: 0 0 12px 0;
  font-size: 14px;
  line-height: 1.5;
  color: #374151;
}

.notification-details {
  margin-top: 12px;
}

.details-toggle {
  background: none;
  border: none;
  color: #3b82f6;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.details-toggle:hover {
  color: #2563eb;
}

.details-content {
  margin-top: 8px;
  padding: 8px;
  background: #f9fafb;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
}

.details-content pre {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
  white-space: pre-wrap;
  word-break: break-word;
}

.notification-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.primary {
  background: #3b82f6;
  color: white;
}

.action-btn.primary:hover {
  background: #2563eb;
}

.action-btn.secondary {
  background: #e5e7eb;
  color: #374151;
}

.action-btn.secondary:hover {
  background: #d1d5db;
}

.progress-bar {
  height: 3px;
  background: #e5e7eb;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: currentColor;
  transition: width 0.1s linear;
}

/* 不同类型的样式 */
.notification-success {
  border-left: 4px solid #10b981;
  color: #10b981;
}

.notification-warning {
  border-left: 4px solid #f59e0b;
  color: #f59e0b;
}

.notification-error {
  border-left: 4px solid #ef4444;
  color: #ef4444;
}

.notification-info {
  border-left: 4px solid #3b82f6;
  color: #3b82f6;
}

.notification-persistent {
  border: 2px solid currentColor;
}
</style>