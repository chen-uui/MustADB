import { ref } from 'vue'

export function useTaskProgress(getStatusFn, intervalMs = 3000) {
  const isRunning = ref(false)
  const percentage = ref(0)
  const processed = ref(0)
  const total = ref(0)
  const successful = ref(0)
  const failed = ref(0)
  const status = ref('')
  const raw = ref(null)

  let timer = null

  const start = (taskId) => {
    stop()
    if (!taskId || typeof getStatusFn !== 'function') return
    isRunning.value = true
    const tick = async () => {
      try {
        const res = await getStatusFn(taskId)
        if (res && res.success && res.data) {
          const d = res.data
          raw.value = d
          percentage.value = d.progress_percentage || 0
          processed.value = d.processed_documents || 0
          total.value = d.total_documents || 0
          successful.value = d.successful_extractions || 0
          failed.value = d.failed_extractions || 0
          status.value = d.status || ''
          if (['completed', 'failed', 'cancelled'].includes(d.status)) {
            stop()
          }
        }
      } catch (_) { /* silent */ }
    }
    timer = setInterval(tick, intervalMs)
    tick()
  }

  const stop = () => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    isRunning.value = false
  }

  return { isRunning, percentage, processed, total, successful, failed, status, raw, start, stop }
}
