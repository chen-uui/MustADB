import { ref, createApp } from 'vue'
import ErrorNotification from '@/components/ErrorNotification.vue'
import { extractApiError, getApiErrorMessage } from '@/utils/apiError'

// 全局通知容器
const notifications = ref([])
let notificationId = 0

const normalizeOptions = (options, fallbackKey = 'details') => {
  if (options === null || options === undefined) {
    return {}
  }
  if (typeof options === 'object') {
    return options
  }
  return { [fallbackKey]: String(options) }
}

// 创建通知实例
function createNotification(options) {
  options = normalizeOptions(options, 'message')
  const id = ++notificationId
  
  // 创建通知组件实例
  const notificationApp = createApp(ErrorNotification, {
    ...options,
    message: options.message || '',  // 确保 message 属性存在
    title: options.title || '',      // 确保 title 属性存在
    type: options.type || 'info',    // 确保 type 合法
    autoClose: options.autoClose !== false,
    duration: typeof options.duration === 'number' ? options.duration : 3000,
    persistent: !!options.persistent,
    actions: Array.isArray(options.actions) ? options.actions : [],
    onClose: () => {
      removeNotification(id)
    }
  })
  
  // 创建DOM容器
  const container = document.createElement('div')
  container.id = `notification-${id}`
  document.body.appendChild(container)
  
  // 挂载组件
  const instance = notificationApp.mount(container)
  
  // 存储通知信息
  const notification = {
    id,
    instance,
    container,
    app: notificationApp
  }
  
  notifications.value.push(notification)
  
  return notification
}

// 移除通知
function removeNotification(id) {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    const notification = notifications.value[index]
    
    // 卸载组件
    notification.app.unmount()
    
    // 移除DOM容器
    if (notification.container && notification.container.parentNode) {
      notification.container.parentNode.removeChild(notification.container)
    }
    
    // 从数组中移除
    notifications.value.splice(index, 1)
  }
}

// 清除所有通知
function clearAllNotifications() {
  notifications.value.forEach(notification => {
    notification.app.unmount()
    if (notification.container && notification.container.parentNode) {
      notification.container.parentNode.removeChild(notification.container)
    }
  })
  notifications.value = []
}

// 通知系统组合式API
export function useNotification() {
  
  // 显示成功通知
  const showSuccess = (message, options = {}) => {
    const normalized = normalizeOptions(options)
    return createNotification({
      type: 'success',
      title: normalized.title || '操作成功',
      message,
      autoClose: normalized.autoClose !== false,
      duration: normalized.duration || 3000,
      ...normalized
    })
  }
  
  // 显示警告通知
  const showWarning = (message, options = {}) => {
    const normalized = normalizeOptions(options)
    return createNotification({
      type: 'warning',
      title: normalized.title || '注意',
      message,
      autoClose: normalized.autoClose !== false,
      duration: normalized.duration || 4000,
      ...normalized
    })
  }
  
  // 显示错误通知
  const showError = (errorOrMessage, options = {}) => {
    const normalized = normalizeOptions(options)
    const message =
      typeof errorOrMessage === 'string'
        ? errorOrMessage
        : getApiErrorMessage(errorOrMessage, normalized.message || '操作失败')

    return createNotification({
      type: 'error',
      title: normalized.title || '操作失败',
      message,
      autoClose: normalized.autoClose !== false,
      duration: normalized.duration || 6000,
      persistent: normalized.persistent || false,
      details: normalized.details,
      actions: normalized.actions,
      ...normalized
    })
  }
  
  // 显示信息通知
  const showInfo = (message, options = {}) => {
    const normalized = normalizeOptions(options)
    return createNotification({
      type: 'info',
      title: normalized.title || '提示',
      message,
      autoClose: normalized.autoClose !== false,
      duration: normalized.duration || 4000,
      ...normalized
    })
  }
  
  // 显示任务状态通知
  const showTaskStatus = (taskId, status, details = {}) => {
    const statusConfig = {
      'running': {
        type: 'info',
        title: '任务进行中',
        message: `任务 ${taskId} 正在执行中...`,
        autoClose: false,
        persistent: true
      },
      'completed': {
        type: 'success',
        title: '任务完成',
        message: `任务 ${taskId} 已成功完成`,
        details: details.statistics ? JSON.stringify(details.statistics, null, 2) : null
      },
      'failed': {
        type: 'error',
        title: '任务失败',
        message: `任务 ${taskId} 执行失败`,
        details: details.error || '未知错误',
        persistent: true,
        actions: [
          {
            label: '重试',
            type: 'primary',
            handler: () => details.onRetry && details.onRetry()
          },
          {
            label: '查看日志',
            type: 'secondary',
            handler: () => details.onViewLog && details.onViewLog()
          }
        ]
      },
      'cancelled': {
        type: 'warning',
        title: '任务已取消',
        message: `任务 ${taskId} 已被取消`,
        details: details.reason || '用户取消'
      },
      'paused': {
        type: 'warning',
        title: '任务已暂停',
        message: `任务 ${taskId} 已暂停`,
        autoClose: false,
        persistent: true
      }
    }
    
    const config = statusConfig[status] || statusConfig['running']
    return createNotification(config)
  }
  
  // 显示网络错误通知
  const showNetworkError = (error, options = {}) => {
    const normalizedError = extractApiError(error, '网络连接失败')

    return showError(normalizedError.message, {
      title: '网络错误',
      details: normalizedError.detail,
      persistent: true,
      actions: [
        {
          label: '重试',
          type: 'primary',
          handler: () => options.onRetry && options.onRetry()
        },
        {
          label: '刷新页面',
          type: 'secondary',
          handler: () => window.location.reload()
        }
      ],
      ...options
    })
  }
  
  return {
    showSuccess,
    showWarning,
    showError,
    showInfo,
    showTaskStatus,
    showNetworkError,
    clearAllNotifications,
    notifications: notifications.value
  }
}

// 全局通知实例（用于在非组件中使用）
export const notification = useNotification()
