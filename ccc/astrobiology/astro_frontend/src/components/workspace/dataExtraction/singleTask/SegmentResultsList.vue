<template>
  <section class="segment-results">
    <header class="segment-header">
      <div>
        <div class="badge">STEP 2</div>
        <h3>检索结果</h3>
        <p>筛选想要抽取的片段，可批量加入队列</p>
      </div>

      <div class="header-actions">
        <div class="select-all-group">
          <label class="select-all">
            <input
              ref="selectAllRef"
              type="checkbox"
              :checked="allSelected"
              :disabled="!segments.length || taskStatus === 'running'"
              @change="onSelectAll($event.target.checked)"
            />
            全选
          </label>
            <div class="select-all-menu">
            <button
              class="select-all-btn"
              :class="{ active: selectAllMode === 'page' }"
              :disabled="!segments.length || taskStatus === 'running'"
              @click="handleSelectAllModeChange('page')"
            >
              单页全选
            </button>
            <button
              class="select-all-btn"
              :class="{ active: selectAllMode === 'all' }"
              :disabled="!segments.length || taskStatus === 'running'"
              @click="handleSelectAllModeChange('all')"
              :title="selectAllMode === 'all' && unprocessedSegmentIds.length > 0 ? `选择剩余的 ${unprocessedSegmentIds.length} 个未处理片段` : ''"
            >
              {{ unprocessedSegmentIds.length > 0 && unprocessedSegmentIds.length < allSegmentIds.length ? `选择剩余 (${unprocessedSegmentIds.length})` : '全部全选' }}
            </button>
          </div>
        </div>
        <button
          class="primary"
          :disabled="!selectedIds.size || taskStatus === 'running'"
          @click="$emit('enqueue-selected')"
        >
          <i class="bi bi-play-circle"></i>
          加入抽取队列
        </button>
      </div>
    </header>

    <transition name="fade" mode="out-in">
      <div v-if="loading" key="loading" class="loading-state">
        <i class="bi bi-arrow-repeat"></i>
        正在检索片段...
        <div class="progress-container">
          <div class="progress-bar"></div>
        </div>
        <p class="hint">正在加载候选片段，包含向量检索与重排序，可能需要数十秒。</p>
      </div>

      <div v-else-if="!segments.length" key="empty" class="empty-state">
        <i class="bi bi-search"></i>
        <p>暂无检索结果，请调整关键词或排序后再试。</p>
      </div>

      <div v-else key="list" class="result-list">
        <article
          v-for="segment in segments"
          :key="segment.id"
          class="segment-card"
          :class="{
            selected: selectedIds.has(segment.id),
            running: taskStatus === 'running'
          }"
        >
          <div class="card-header">
            <label class="checkbox">
              <input
                type="checkbox"
                :checked="selectedIds.has(segment.id)"
                :disabled="taskStatus === 'running'"
                @change="$emit('toggle-select', segment.id)"
              />
            </label>

            <div class="meta">
              <span class="doc">{{ segment.title || segment.documentId }}</span>
              <span class="sep">·</span>
              <span>文档 ID {{ segment.documentId || '—' }}</span>
              <span v-if="segment.authors?.length" class="sep">·</span>
              <span v-if="segment.authors?.length" class="authors">
                作者 {{ segment.authors.join('、') }}
              </span>
              <span class="sep">·</span>
              <span>第 {{ segment.page || '—' }} 页</span>
              <span class="sep">·</span>
              <span class="chip">得分 {{ segment.score?.toFixed(3) ?? '—' }}</span>
            </div>

            <div class="actions">
              <button
                class="ghost"
                :disabled="taskStatus === 'running'"
                @click="$emit('enqueue-single', segment.id)"
              >
                <i class="bi bi-lightning-charge"></i>
                抽取
              </button>
              <button class="ghost" @click="toggleExpand(segment.id)">
                <i class="bi" :class="expanded.has(segment.id) ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                {{ expanded.has(segment.id) ? '收起内容' : '查看内容' }}
              </button>
            </div>
          </div>

          <transition name="collapse">
            <div v-if="expanded.has(segment.id)" class="content">
              <p v-html="highlightKeyword(segment.content, segment.highlight)"></p>
            </div>
          </transition>
        </article>
      </div>
    </transition>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  segments: {
    type: Array,
    default: () => []
  },
  selectedIds: {
    type: Object,
    default: () => new Set()
  },
  totalSegments: {
    type: Number,
    default: 0
  },
  allSegmentIds: {
    type: Array,
    default: () => []
  },
  unprocessedSegmentIds: {
    type: Array,
    default: () => []
  },
  loading: Boolean,
  taskStatus: {
    type: String,
    default: 'idle'
  }
})

const emit = defineEmits(['toggle-select', 'select-all', 'select-all-page', 'select-all-total', 'enqueue-selected', 'enqueue-single'])

const selectAllRef = ref(null)
const expanded = ref(new Set())
const selectAllMode = ref('all') // 'page' 或 'all'

// 检查是否所有片段都被选中（根据当前模式）
const allSelected = computed(() => {
  if (!props.segments.length) {
    return false
  }
  
  if (selectAllMode.value === 'page') {
    // 单页模式：检查当前页所有片段是否都被选中
    return props.segments.length > 0 && props.segments.every(s => props.selectedIds.has(s.id))
  } else {
    // 全部模式：检查所有片段（包括未加载的）是否都被选中
    if (props.allSegmentIds.length > 0) {
      return props.allSegmentIds.every(id => props.selectedIds.has(id))
    }
    // 如果没有allSegmentIds，则只检查当前页的（向后兼容）
    return props.segments.length > 0 && props.segments.every(s => props.selectedIds.has(s.id))
  }
})

const isIndeterminate = computed(() => {
  const selectedCount = props.selectedIds.size
  if (selectedCount === 0) {
    return false
  }
  
  if (selectAllMode.value === 'page') {
    // 单页模式：检查当前页是否有部分选中
    const currentPageIds = new Set(props.segments.map(s => s.id))
    const selectedInCurrentPage = Array.from(currentPageIds).filter(id => props.selectedIds.has(id)).length
    return selectedInCurrentPage > 0 && selectedInCurrentPage < currentPageIds.size
  } else {
    // 全部模式：检查全部是否有部分选中
    if (props.allSegmentIds.length > 0) {
      const totalCount = props.allSegmentIds.length
      return selectedCount > 0 && selectedCount < totalCount
    }
    // 向后兼容
    const currentPageIds = new Set(props.segments.map(s => s.id))
    const selectedInCurrentPage = Array.from(currentPageIds).filter(id => props.selectedIds.has(id)).length
    return selectedInCurrentPage > 0 && selectedInCurrentPage < currentPageIds.size
  }
})

const onSelectAll = (checked) => {
  if (checked) {
    // 根据当前模式发送相应事件
    if (selectAllMode.value === 'page') {
      emit('select-all-page', true)
    } else {
      emit('select-all-total', true)
    }
  } else {
    // 取消全选
    emit('select-all', false)
  }
}

const handleSelectAllModeChange = (mode) => {
  selectAllMode.value = mode
  // 切换模式后，如果当前已经有选中项，根据新模式重新全选
  if (props.selectedIds.size > 0) {
    if (mode === 'page') {
      emit('select-all-page', true)
    } else {
      emit('select-all-total', true)
    }
  }
}

const toggleExpand = (segmentId) => {
  const next = new Set(expanded.value)
  if (next.has(segmentId)) {
    next.delete(segmentId)
  } else {
    next.add(segmentId)
  }
  expanded.value = next
}

const highlightKeyword = (content, keyword) => {
  const base = typeof content === 'string' ? content : ''
  if (!keyword) {
    return base
  }
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  return base.replace(regex, '<mark>$1</mark>')
}

watch(
  () => isIndeterminate.value,
  (value) => {
    if (selectAllRef.value) {
      selectAllRef.value.indeterminate = value
    }
  },
  { immediate: true }
)

watch(
  () => props.segments,
  (newVal, oldVal) => {
    if (!oldVal || (newVal?.length || 0) <= (oldVal?.length || 0)) {
      expanded.value = new Set()
    }
  }
)
</script>

<style scoped>
.segment-results {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.segment-header {
  padding: 24px 28px 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(93, 116, 255, 0.12);
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  color: #4c55d8;
  background: rgba(76, 85, 216, 0.12);
  font-weight: 600;
}

.segment-header h3 {
  margin: 8px 0 4px;
  font-size: 1.35rem;
  color: #242b74;
}

.segment-header p {
  margin: 0;
  color: rgba(36, 43, 116, 0.65);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.select-all-group {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}

.select-all {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #4a54d6;
  font-weight: 500;
}

.select-all-menu {
  display: flex;
  gap: 4px;
  background: rgba(76, 85, 216, 0.06);
  border-radius: 8px;
  padding: 2px;
}

.select-all-btn {
  padding: 6px 12px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 0.875rem;
  color: rgba(36, 43, 116, 0.7);
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
}

.select-all-btn:hover:not(:disabled) {
  background: rgba(76, 85, 216, 0.1);
  color: #4a54d6;
}

.select-all-btn.active {
  background: #4a54d6;
  color: white;
  box-shadow: 0 2px 8px rgba(76, 85, 216, 0.25);
}

.select-all-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  color: white;
  font-weight: 600;
  background: linear-gradient(130deg, #5168ff, #7b90ff);
  box-shadow: 0 16px 36px rgba(81, 104, 255, 0.28);
}

.primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.loading-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: rgba(46, 60, 120, 0.6);
  font-size: 1rem;
  padding: 48px;
}

.loading-state i,
.empty-state i {
  font-size: 2rem;
  color: rgba(82, 100, 255, 0.6);
}

.loading-state i {
  animation: spin 1s linear infinite;
}

.progress-container {
  width: 220px;
  height: 6px;
  border-radius: 999px;
  background: rgba(99, 118, 255, 0.16);
  overflow: hidden;
}

.progress-bar {
  width: 40%;
  height: 100%;
  background: linear-gradient(90deg, #5d78ff, #34c1d1);
  border-radius: 999px;
  animation: progress-slide 1.2s ease-in-out infinite;
}

.hint {
  margin: 0;
  font-size: 0.85rem;
  color: rgba(42, 55, 130, 0.55);
}

@keyframes progress-slide {
  0% {
    transform: translateX(-100%);
  }
  50% {
    transform: translateX(60%);
  }
  100% {
    transform: translateX(160%);
  }
}

.result-list {
  height: 100%;
  overflow-y: auto;
  padding: 0 28px 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.segment-card {
  padding: 18px 20px;
  border-radius: 16px;
  border: 1px solid rgba(91, 114, 255, 0.12);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 12px 30px rgba(79, 99, 255, 0.1);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border 0.18s ease;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.segment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 40px rgba(79, 99, 255, 0.16);
}

.segment-card.selected {
  border-color: rgba(80, 102, 255, 0.4);
  box-shadow: 0 18px 40px rgba(80, 102, 255, 0.2);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.checkbox input {
  width: 18px;
  height: 18px;
  accent-color: #5168ff;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: rgba(42, 54, 130, 0.7);
}

.meta .doc {
  font-weight: 600;
  color: #2f3a93;
}

.chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(80, 99, 255, 0.12);
  color: #4453d8;
}

.actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.ghost {
  border: 1px solid rgba(80, 102, 255, 0.2);
  background: rgba(240, 244, 255, 0.85);
  color: #4a5bf5;
  border-radius: 999px;
  padding: 8px 16px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.content {
  color: rgba(32, 45, 105, 0.88);
  line-height: 1.6;
  font-size: 0.97rem;
  padding: 0 4px 8px;
}

mark {
  background: linear-gradient(130deg, rgba(255, 225, 139, 0.9), rgba(255, 206, 93, 0.9));
  border-radius: 4px;
  padding: 0 4px;
}

.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.2s ease;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}

@media (max-width: 768px) {
  .segment-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>

