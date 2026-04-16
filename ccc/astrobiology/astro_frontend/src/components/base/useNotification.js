import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'

import { getApiErrorMessage } from '@/utils/apiError'

export const useNotification = () => {
  const showSuccess = (message) => {
    ElMessage.success(message)
  }

  const showError = (errorOrMessage, fallbackMessage = '操作失败') => {
    ElMessage.error(
      typeof errorOrMessage === 'string'
        ? errorOrMessage
        : getApiErrorMessage(errorOrMessage, fallbackMessage)
    )
  }

  const showWarning = (message) => {
    ElMessage.warning(message)
  }

  const showInfo = (message) => {
    ElMessage.info(message)
  }

  const showNotification = (options) => {
    ElNotification(options)
  }

  return {
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showNotification
  }
}

export const useConfirm = () => {
  const confirm = (message, title = '确认') => {
    return ElMessageBox.confirm(message, title, {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  }

  const alert = (message, title = '提示') => {
    return ElMessageBox.alert(message, title)
  }

  const prompt = (message, title = '输入') => {
    return ElMessageBox.prompt(message, title, {
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
  }

  return {
    confirm,
    alert,
    prompt
  }
}
