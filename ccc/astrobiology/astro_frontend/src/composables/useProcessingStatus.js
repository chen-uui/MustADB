import { ElMessage, ElMessageBox } from 'element-plus'

import PDFService from '@/services/pdfService'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess, getApiMessage } from '@/utils/apiResponse'

export function useProcessingStatus({
  loading,
  documents,
  stats,
  currentPage,
  loadDocuments,
  loadStats,
  showProgressModal,
  processingFiles,
  progressModalRef
}) {
  let progressCloseTimeout = null
  let testInterval = null
  let pollTimeout = null
  let pollingRetryCount = 0

  const clearPollTimeout = () => {
    if (pollTimeout) {
      clearTimeout(pollTimeout)
      pollTimeout = null
    }
  }

  const updateProgress = (payload) => {
    progressModalRef.value?.updateProgress(payload)
  }

  const handleProcessingError = (payload) => {
    progressModalRef.value?.handleProcessingError(payload)
  }

  const handleProcessingComplete = (payload) => {
    progressModalRef.value?.handleProcessingComplete(payload)
  }

  const closeProgressModal = () => {
    clearPollTimeout()
    PDFService.cancelProcessing().catch(() => {})
    showProgressModal.value = false
    progressModalRef.value?.reset()
  }

  const scheduleCloseProgressModal = (delay = 1500) => {
    if (progressCloseTimeout) {
      clearTimeout(progressCloseTimeout)
    }
    progressCloseTimeout = setTimeout(() => {
      closeProgressModal()
    }, delay)
  }

  const schedulePoll = (handler, delay = 3000) => {
    clearPollTimeout()
    pollTimeout = setTimeout(handler, delay)
  }

  const refreshProcessingData = async () => {
    await loadDocuments(currentPage.value)
    await loadStats(true)
  }

  const finishBatchProgress = async (processed, successMessage) => {
    updateProgress({
      processed,
      total: processingFiles.value.length || processed
    })
    progressModalRef.value?.completeProcessing()
    await refreshProcessingData()
    if (successMessage) {
      ElMessage.success(successMessage)
    }
    scheduleCloseProgressModal(1500)
  }

  const pollProcessingProgress = (expectedTotal, successMessage) => {
    pollingRetryCount = 0

    const poll = async () => {
      try {
        const statusResponse = await PDFService.getProcessingStatus()
        const payload = statusResponse.data || {}

        if (!payload.success) {
          throw new Error(payload.message || payload.error || '获取处理状态失败')
        }

        const processed = payload.processed || 0
        const total = payload.total || expectedTotal || processingFiles.value.length || 0
        const progressPct = total > 0 ? Math.round((processed / total) * 100) : 0

        updateProgress({
          processed,
          total,
          current_file: payload.current_file || '正在处理文档...',
          progress: progressPct
        })

        if (payload.finished || (total > 0 && processed >= total) || (payload.pending === 0 && total > 0)) {
          await finishBatchProgress(processed || total, successMessage)
          return
        }

        schedulePoll(poll, 3000)
      } catch (error) {
        pollingRetryCount += 1
        console.warn('Failed to poll processing progress:', error)

        if (pollingRetryCount >= 3) {
          const message = getApiErrorMessage(error, '获取处理状态失败')
          handleProcessingError({
            file: '状态轮询',
            message
          })
          ElMessage.error(message)
          scheduleCloseProgressModal(4000)
          return
        }

        schedulePoll(poll, 3000)
      }
    }

    schedulePoll(poll, 3000)
  }

  const onProcessingComplete = async (result) => {
    console.log('Processing completed:', result)
    await refreshProcessingData()

    if (result?.processed) {
      stats.processedFiles = Math.min(stats.totalFiles, result.processed)
      stats.processingRate = stats.totalFiles > 0 ? Math.round((stats.processedFiles / stats.totalFiles) * 100) : 0
    }
  }

  const processAllDocuments = async () => {
    const pendingDocs = documents.value.filter((doc) => !doc.processed)
    if (pendingDocs.length === 0) {
      ElMessage.info('没有待处理的文档')
      return
    }

    try {
      await ElMessageBox.confirm('确定要批量处理所有未处理文档吗？', '批量处理确认', {
        type: 'warning',
        confirmButtonText: '开始处理',
        cancelButtonText: '取消'
      })
    } catch {
      return
    }

    try {
      loading.value = true
      processingFiles.value = pendingDocs.map((doc) => ({ name: doc.title, size: 0 }))
      showProgressModal.value = true
      progressModalRef.value?.reset()
      updateProgress({
        processed: 0,
        total: pendingDocs.length,
        current_file: '正在启动批量处理...',
        progress: 0
      })

      const response = ensureApiSuccess(await PDFService.processPending(), '启动批量处理失败')
      pollProcessingProgress(response.total || pendingDocs.length, getApiMessage(response, '批量处理完成'))
    } catch (error) {
      const message = getApiErrorMessage(error, '批量处理失败')
      handleProcessingError({
        file: '批量处理任务',
        message
      })
      ElMessage.error(message)
      scheduleCloseProgressModal(4000)
    } finally {
      loading.value = false
    }
  }

  const processStale = async () => {
    try {
      await ElMessageBox.confirm('确定要执行增量修复吗？系统会补处理缺失或异常的文档索引。', '增量修复确认', {
        type: 'warning',
        confirmButtonText: '开始修复',
        cancelButtonText: '取消'
      })
    } catch {
      return
    }

    try {
      loading.value = true
      processingFiles.value = documents.value.map((doc) => ({ name: doc.title, size: 0 }))
      showProgressModal.value = true
      progressModalRef.value?.reset()
      updateProgress({
        processed: 0,
        total: documents.value.length || stats.totalFiles,
        current_file: '正在启动增量修复...',
        progress: 0
      })

      const response = ensureApiSuccess(await PDFService.processStale(), '启动增量修复失败')
      const total = response.total || documents.value.length || stats.totalFiles
      pollProcessingProgress(total, getApiMessage(response, '增量修复完成'))
    } catch (error) {
      const message = getApiErrorMessage(error, '增量修复失败')
      handleProcessingError({
        file: '增量修复任务',
        message
      })
      ElMessage.error(message)
      scheduleCloseProgressModal(4000)
    } finally {
      loading.value = false
    }
  }

  const reprocessAllDocuments = async () => {
    try {
      await ElMessageBox.confirm(
        '确定要重新处理全部文档吗？这会重建所有向量索引，耗时可能较长。',
        '全量重处理确认',
        {
          type: 'warning',
          confirmButtonText: '开始重处理',
          cancelButtonText: '取消'
        }
      )
    } catch {
      return
    }

    try {
      await loadStats(true)
      const totalDocuments = stats.totalFiles
      if (totalDocuments === 0) {
        ElMessage.info('没有文档需要重新处理')
        return
      }

      loading.value = true
      processingFiles.value = new Array(totalDocuments).fill(null).map((_, index) => ({
        name: `文档 ${index + 1}`,
        size: 0
      }))
      showProgressModal.value = true
      progressModalRef.value?.reset()
      updateProgress({
        processed: 0,
        total: totalDocuments,
        current_file: '正在启动全量重处理...',
        progress: 0
      })

      const response = ensureApiSuccess(await PDFService.reprocessAll({ confirm: true }), '启动全量重处理失败')
      pollProcessingProgress(response.total || totalDocuments, getApiMessage(response, '全量重处理完成'))
    } catch (error) {
      const message = getApiErrorMessage(error, '全量重处理失败')
      handleProcessingError({
        file: '全量重处理任务',
        message
      })
      ElMessage.error(message)
      scheduleCloseProgressModal(4000)
    } finally {
      loading.value = false
    }
  }

  const testProgressModal = () => {
    if (testInterval) {
      clearInterval(testInterval)
    }

    processingFiles.value = [
      { name: '示例文档 1.pdf', status: 'pending', progress: 0 },
      { name: '示例文档 2.pdf', status: 'processing', progress: 50 },
      { name: '示例文档 3.pdf', status: 'completed', progress: 100 },
      { name: '示例文档 4.pdf', status: 'error', error: '处理失败' }
    ]
    showProgressModal.value = true
    progressModalRef.value?.reset()
    updateProgress({
      processed: 1,
      total: processingFiles.value.length,
      current_file: '正在测试进度弹窗...',
      progress: 25
    })

    let progressCount = 1
    testInterval = setInterval(() => {
      progressCount += 1
      updateProgress({
        processed: Math.min(progressCount, processingFiles.value.length),
        total: processingFiles.value.length,
        current_file: `测试文档 ${Math.min(progressCount, processingFiles.value.length)}`,
        progress: Math.min(progressCount * 25, 100)
      })

      if (progressCount >= processingFiles.value.length) {
        clearInterval(testInterval)
        testInterval = null
        progressModalRef.value?.completeProcessing()
        scheduleCloseProgressModal(2000)
      }
    }, 500)
  }

  const cleanup = () => {
    clearPollTimeout()
    if (progressCloseTimeout) {
      clearTimeout(progressCloseTimeout)
      progressCloseTimeout = null
    }
    if (testInterval) {
      clearInterval(testInterval)
      testInterval = null
    }
  }

  return {
    updateProgress,
    handleProcessingError,
    handleProcessingComplete,
    closeProgressModal,
    onProcessingComplete,
    processAllDocuments,
    processStale,
    reprocessAllDocuments,
    testProgressModal,
    cleanup
  }
}
