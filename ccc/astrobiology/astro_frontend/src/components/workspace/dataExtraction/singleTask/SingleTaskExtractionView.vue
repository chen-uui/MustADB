<template>
  <div class="single-task-extraction">
    <TaskStatusHeader
      :task="currentTask"
      @cancel-task="handleCancelTask"
      @restart-task="handleRestartTask"
    />

    <div class="content-area">
      <SearchConfigPanel
        class="panel"
        :filters="filters"
        :is-searching="searchState.isSearching"
        :disabled="currentTask.status === 'running'"
        @update:filters="updateFilters"
        @submit-search="handleSearch"
      />

      <div class="main-layout">
        <div class="main-column">
          <SegmentResultsList
            :segments="segmentResults"
            :loading="searchState.isSearching"
            :selected-ids="selectedSegmentIds"
            :total-segments="pagination.total"
            :all-segment-ids="allSegmentIds"
            :unprocessed-segment-ids="unprocessedSegmentIds"
            :task-status="currentTask.status"
            @toggle-select="handleToggleSegment"
            @select-all="handleSelectAll"
            @select-all-page="handleSelectAllPage"
            @select-all-total="handleSelectAllTotal"
            @enqueue-selected="handleEnqueueSelected"
            @enqueue-single="handleEnqueueSingle"
          />
          <div v-if="hasMoreSegments" class="load-more">
            <button
              class="load-more-btn"
              :disabled="isLoadingMore || searchState.isSearching"
              @click="handleLoadMore"
            >
              <i v-if="!isLoadingMore" class="bi bi-arrow-down-circle"></i>
              <i v-else class="bi bi-arrow-repeat loading"></i>
              {{ isLoadingMore ? '正在加载...' : `加载更多 (${segmentResults.length}/${pagination.total})` }}
            </button>
          </div>
        </div>

        <ExtractionSidebar
          class="side-column"
          :queue="extractionQueue"
          :aggregated-results="aggregatedResults"
          :auto-refresh="autoRefresh"
          :task-status="currentTask.status"
          :is-refreshing="queueState.isRefreshing"
          @toggle-auto-refresh="toggleAutoRefresh"
          @open-preview="previewOpen = true"
          @retry-segment="handleRetrySegment"
          @remove-segment="handleRemoveSegment"
        />
      </div>
    </div>

    <AggregatedResultsModal
      :model-value="previewOpen"
      :results="aggregatedResults"
      :is-loading="queueState.isRefreshing"
      @update:model-value="previewOpen = $event"
      @export="handleExportResults"
    />
  </div>
</template>

<script setup>
import { reactive, ref, watch, onMounted, onBeforeUnmount, computed, inject } from 'vue'
import TaskStatusHeader from '@/components/workspace/dataExtraction/singleTask/TaskStatusHeader.vue'
import SearchConfigPanel from '@/components/workspace/dataExtraction/singleTask/SearchConfigPanel.vue'
import SegmentResultsList from '@/components/workspace/dataExtraction/singleTask/SegmentResultsList.vue'
import ExtractionSidebar from '@/components/workspace/dataExtraction/singleTask/ExtractionSidebar.vue'
import AggregatedResultsModal from '@/components/workspace/dataExtraction/singleTask/AggregatedResultsModal.vue'
import { PDFService } from '@/services/pdfService.js'
import { useNotification } from '@/composables/useNotification'

const { showInfo, showWarning, showError, showSuccess } = useNotification()

// 尝试获取父组件提供的更新统计函数
const updateExtractionStats = inject('updateExtractionStats', null)

const pdfService = PDFService
const SESSION_STORAGE_KEY = 'singleTaskSessionId'

const currentTask = reactive({
  status: 'idle',
  keywords: [],
  threshold: 0.5,
  startedAt: null,
  canCancel: false
})

const filters = reactive({
  keywords: [],
  threshold: 0.5,
  sortBy: 'score_desc'
})

const searchState = reactive({
  isSearching: false,
  lastUpdated: null
})

const queueState = reactive({
  isRefreshing: false,
  lastPolledAt: null
})

const autoRefresh = ref(true)
const previewOpen = ref(false)
const sessionId = ref(null)
let pollTimer = null

const segmentResults = ref([])
const selectedSegmentIds = ref(new Set())
const allSegmentIds = ref([]) // 存储所有片段的ID，用于全选功能
const unprocessedSegmentIds = ref([]) // 存储未处理片段的ID，用于选择剩余片段
const extractionQueue = ref([])
const aggregatedResults = ref([])
const pagination = reactive({ page: 1, pageSize: 50, total: 0 })
const isLoadingMore = ref(false)

const updateFilters = (nextFilters) => {
  filters.keywords = [...nextFilters.keywords]
  if (typeof nextFilters.threshold === 'number') {
    filters.threshold = nextFilters.threshold
  }
  filters.sortBy = nextFilters.sortBy
}

const resetTaskState = () => {
  stopPolling()
  sessionId.value = null
  currentTask.status = 'idle'
  currentTask.keywords = []
  currentTask.threshold = filters.threshold
  currentTask.startedAt = null
  currentTask.canCancel = false
  segmentResults.value = []
  extractionQueue.value = []
  aggregatedResults.value = []
  selectedSegmentIds.value = new Set()
  allSegmentIds.value = []
  unprocessedSegmentIds.value = []
  pagination.page = 1
  pagination.total = 0
  isLoadingMore.value = false
  localStorage.removeItem(SESSION_STORAGE_KEY)
}

const applySessionPayload = (session) => {
  if (!session) {
    return
  }
  sessionId.value = session.sessionId
  if (session.sessionId) {
    localStorage.setItem(SESSION_STORAGE_KEY, session.sessionId)
  }
  currentTask.status = session.status || 'idle'
  currentTask.keywords = [...(session.keywords || [])]
  currentTask.threshold = typeof session.threshold === 'number' ? session.threshold : filters.threshold
  currentTask.startedAt = session.startedAt || session.createdAt || currentTask.startedAt
  currentTask.canCancel = ['searching', 'ready', 'running'].includes(currentTask.status)
  
  // 同步filters以便搜索面板显示
  filters.keywords = [...currentTask.keywords]
  filters.threshold = currentTask.threshold
  
  extractionQueue.value = Array.isArray(session.queue)
    ? session.queue.map((item) => ({ ...item }))
    : []
  aggregatedResults.value = Array.isArray(session.aggregatedResults)
    ? session.aggregatedResults.map((item) => ({
        ...item,
        segments: Array.isArray(item.segments) ? item.segments.map((seg) => ({ ...seg })) : []
      }))
    : []
  queueState.lastPolledAt = new Date().toISOString()
  if (session.totalSegments !== undefined) {
    pagination.total = session.totalSegments
  }
  // 更新所有片段ID（从状态轮询中获取）
  if (session.allSegmentIds && Array.isArray(session.allSegmentIds)) {
    allSegmentIds.value = session.allSegmentIds
  }
  // 更新未处理的片段ID
  if (session.unprocessedSegmentIds && Array.isArray(session.unprocessedSegmentIds)) {
    unprocessedSegmentIds.value = session.unprocessedSegmentIds
  }
  
  // 更新统计数据
  updateStats()
}

// 更新统计数据
const updateStats = () => {
  if (!updateExtractionStats) return
  
  // 计算已处理的片段数（成功和失败都算已处理）
  const processedSegments = extractionQueue.value.filter(
    item => item.status === 'success' || item.status === 'failed'
  ).length
  
  // 计算已提取的实体数（从聚合结果中统计）
  const extractedEntities = aggregatedResults.value.reduce(
    (total, entity) => total + (entity.segments?.length || 0), 0
  )
  
  // 获取状态文本
  const statusMap = {
    'idle': '未开始',
    'searching': '搜索中',
    'ready': '准备就绪',
    'running': '提取中',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消'
  }
  
  updateExtractionStats({
    status: statusMap[currentTask.status] || currentTask.status,
    processed_segments: processedSegments,
    extracted_entities: extractedEntities,
    aggregated_results: aggregatedResults.value.length
  })
}

// 监听相关数据变化，自动更新统计
watch([extractionQueue, aggregatedResults, () => currentTask.status], () => {
  updateStats()
}, { deep: true })

const handleSearch = async () => {
  if (!filters.keywords.length) {
    showWarning('请至少输入一个关键词')
    return
  }

  searchState.isSearching = true
  currentTask.status = 'searching'
  currentTask.keywords = [...filters.keywords]
  currentTask.threshold = filters.threshold
  currentTask.startedAt = new Date().toISOString()
  pagination.page = 1
  pagination.total = 0
  segmentResults.value = []

  try {
    const response = await pdfService.singleTaskSearch({
      keywords: filters.keywords,
      threshold: filters.threshold,
      sortBy: filters.sortBy,
      page: pagination.page,
      pageSize: pagination.pageSize
    })

    if (!response?.success) {
      throw new Error(response?.error || '搜索失败')
    }

    const session = response.data?.session
    const segmentsPayload = response.data?.segments || {}

    applySessionPayload(session)
    segmentResults.value = segmentsPayload.items || []
    pagination.page = segmentsPayload.page || 1
    pagination.pageSize = segmentsPayload.pageSize || pagination.pageSize
    pagination.total = segmentsPayload.total || segmentResults.value.length
    // 保存所有片段的ID，用于全选功能
    allSegmentIds.value = segmentsPayload.allSegmentIds || []
    // 保存未处理的片段ID（优先从响应中获取，如果没有则初始化为全部）
    unprocessedSegmentIds.value = segmentsPayload.unprocessedSegmentIds || segmentsPayload.allSegmentIds || []
    if (!segmentResults.value.length) {
      showWarning('没有检索到相关片段，请尝试调整关键词或排序')
    }
    selectedSegmentIds.value = new Set()
    currentTask.status = session?.status || 'ready'
    currentTask.canCancel = true
    searchState.lastUpdated = new Date().toISOString()
    if (segmentResults.value.length) {
      showSuccess(`检索完成，共找到 ${pagination.total} 个片段`)
    }
    startPolling()
  } catch (error) {
    console.error('搜索片段失败', error)
    showError('搜索片段失败，请稍后重试', { details: error?.message })
    resetTaskState()
  } finally {
    searchState.isSearching = false
    console.debug('[SingleTask] search done, loading:', searchState.isSearching)
  }
}

const handleToggleSegment = (segmentId) => {
  const ids = new Set(selectedSegmentIds.value)
  if (ids.has(segmentId)) {
    ids.delete(segmentId)
  } else {
    ids.add(segmentId)
  }
  selectedSegmentIds.value = ids
}

const handleSelectAll = (checked) => {
  if (!checked) {
    // 取消全选
    selectedSegmentIds.value = new Set()
  }
}

const handleSelectAllPage = (checked) => {
  if (checked) {
    // 单页全选：只选择当前页显示的片段
    const currentPageIds = segmentResults.value.map((item) => item.id)
    currentPageIds.forEach(id => selectedSegmentIds.value.add(id))
  }
}

const handleSelectAllTotal = (checked) => {
  if (checked) {
    // 优先选择未处理的片段，如果没有则选择所有片段
    if (unprocessedSegmentIds.value.length > 0) {
      // 选择所有未处理的片段（智能模式）
      selectedSegmentIds.value = new Set(unprocessedSegmentIds.value)
    } else if (allSegmentIds.value.length > 0) {
      // 如果没有未处理片段列表，则选择所有片段（向后兼容）
      selectedSegmentIds.value = new Set(allSegmentIds.value)
    } else {
      // 最后兜底：只选中当前页的
      selectedSegmentIds.value = new Set(segmentResults.value.map((item) => item.id))
    }
  }
}

const enqueueSegments = async (segmentIds) => {
  if (!segmentIds.length) {
    showInfo('请先选择片段')
    return
  }

  if (!sessionId.value) {
    showWarning('请先执行检索')
    return
  }

  try {
    const response = await pdfService.singleTaskEnqueue(sessionId.value, segmentIds)
    if (!response?.success) {
      throw new Error(response?.error || '加入队列失败')
    }
    applySessionPayload(response.data)
    currentTask.status = response.data?.status || 'running'
    showSuccess('已加入抽取队列')
    startPolling()
  } catch (error) {
    console.error('片段入队失败', error)
    showError('片段入队失败', { details: error?.message })
  }
}

const handleEnqueueSelected = () => {
  enqueueSegments(Array.from(selectedSegmentIds.value))
}

const handleEnqueueSingle = (segmentId) => {
  enqueueSegments([segmentId])
}

const handleRetrySegment = (segmentId) => {
  enqueueSegments([segmentId])
}

const handleRemoveSegment = () => {
  showWarning('当前版本暂不支持移除队列中的片段，如需停止请取消整个任务')
}

const handleCancelTask = async () => {
  if (!sessionId.value) {
    resetTaskState()
    return
  }

  try {
    const response = await pdfService.singleTaskCancel(sessionId.value)
    if (!response?.success) {
      throw new Error(response?.error || '取消失败')
    }
    stopPolling()
    showInfo('任务已取消')
    resetTaskState()
  } catch (error) {
    console.error('取消任务失败', error)
    showError('取消任务失败', { details: error?.message })
  }
}

const handleRestartTask = () => {
  resetTaskState()
}

const toggleAutoRefresh = (value) => {
  autoRefresh.value = value
  startPolling()
}

const handleExportResults = () => {
  showInfo('导出功能开发中，敬请期待')
}

const hasMoreSegments = computed(() => segmentResults.value.length < pagination.total)

const fetchStatus = async (silent = false) => {
  if (!sessionId.value) {
    return false
  }

  if (!silent) {
    queueState.isRefreshing = true
  }

  try {
    const response = await pdfService.singleTaskStatus(sessionId.value)
    if (!response?.success) {
      throw new Error(response?.error || '获取状态失败')
    }
    applySessionPayload(response.data)
    return true
  } catch (error) {
    console.error('轮询任务状态失败', error)
    if (error?.response?.status === 404) {
      resetTaskState()
      return false
    }
    if (!silent) {
      showError('刷新状态失败', { details: error?.message })
    }
    return false
  } finally {
    queueState.isRefreshing = false
  }
}

const startPolling = () => {
  stopPolling()
  if (!autoRefresh.value || !sessionId.value) {
    return
  }
  pollTimer = window.setInterval(() => fetchStatus(true), 5000)
  fetchStatus(true)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(autoRefresh, () => {
  startPolling()
})

watch(sessionId, () => {
  startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
})

onMounted(async () => {
  // 初始化时更新统计
  updateStats()
  
  const storedId = localStorage.getItem(SESSION_STORAGE_KEY)
  if (storedId) {
    sessionId.value = storedId
    const ok = await fetchStatus()
    if (ok) {
      // 加载第一页片段数据
      try {
        const segmentsResponse = await pdfService.singleTaskSegments(storedId, 1, pagination.pageSize)
        if (segmentsResponse?.success && segmentsResponse.data?.segments) {
          const payload = segmentsResponse.data.segments
          segmentResults.value = payload.items || []
          pagination.page = payload.page || 1
          pagination.total = payload.total || 0
          allSegmentIds.value = payload.allSegmentIds || []
          unprocessedSegmentIds.value = payload.unprocessedSegmentIds || allSegmentIds.value
        }
      } catch (error) {
        console.error('加载片段列表失败:', error)
      }
      startPolling()
    } else {
      resetTaskState()
    }
  }
})

const handleLoadMore = async () => {
  if (!sessionId.value || isLoadingMore.value || !hasMoreSegments.value) {
    return
  }

  const nextPage = pagination.page + 1
  isLoadingMore.value = true

  try {
    const response = await pdfService.singleTaskSegments(sessionId.value, nextPage, pagination.pageSize)
    if (!response?.success) {
      throw new Error(response?.error || '加载更多片段失败')
    }
    const payload = response.data?.segments || {}
    const items = payload.items || []
    segmentResults.value = segmentResults.value.concat(items)
    pagination.page = payload.page || nextPage
    pagination.pageSize = payload.pageSize || pagination.pageSize
    pagination.total = payload.total || pagination.total
    // 更新所有片段ID（虽然应该是一样的，但为了确保一致性）
    if (payload.allSegmentIds && payload.allSegmentIds.length > 0) {
      allSegmentIds.value = payload.allSegmentIds
    }
  } catch (error) {
    console.error('加载更多片段失败', error)
    showError('加载更多片段失败', { details: error?.message })
  } finally {
    isLoadingMore.value = false
  }
}
</script>

<style scoped>
.single-task-extraction {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
  background: linear-gradient(145deg, #eef1ff 0%, #f9fbff 100%);
  min-height: 100%;
}

.content-area {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel {
  background: rgba(255, 255, 255, 0.88);
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(76, 92, 255, 0.08);
  border: 1px solid rgba(79, 97, 255, 0.08);
  backdrop-filter: blur(10px);
}

.main-layout {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: 24px;
}

.main-column,
.side-column {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 20px;
  box-shadow: 0 20px 50px rgba(87, 109, 254, 0.08);
  border: 1px solid rgba(95, 116, 255, 0.08);
  min-height: 460px;
}

.main-column {
  display: flex;
  flex-direction: column;
}

.load-more {
  padding: 12px 16px 20px;
  display: flex;
  justify-content: center;
}

.load-more-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: 999px;
  border: 1px solid rgba(82, 100, 255, 0.24);
  background: rgba(240, 244, 255, 0.9);
  color: #4a57e0;
  cursor: pointer;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.load-more-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 26px rgba(80, 102, 255, 0.18);
}

.load-more-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
  box-shadow: none;
}

.load-more-btn .loading {
  animation: spin 1s linear infinite;
}

@media (max-width: 1200px) {
  .main-layout {
    grid-template-columns: 1fr;
  }

  .side-column {
    min-height: auto;
  }
}
</style>

