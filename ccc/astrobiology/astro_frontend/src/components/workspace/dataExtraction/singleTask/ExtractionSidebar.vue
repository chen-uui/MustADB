<template>
  <aside class="sidebar">
    <section class="queue-section">
      <header>
        <div>
          <div class="badge">STEP 3</div>
          <h4>抽取队列</h4>
        </div>
        <button class="ghost" @click="$emit('open-preview')">
          <i class="bi bi-list-ul"></i>
          查看聚合结果
        </button>
      </header>

      <div class="queue-meta">
        <span>队列中 {{ queue.length }} 个片段</span>
        <label class="refresh-toggle">
          <input type="checkbox" :checked="autoRefresh" @change="toggleAutoRefresh($event)" />
          自动刷新
        </label>
      </div>

      <!-- 进度条 -->
      <div v-if="queue.length > 0" class="progress-container">
        <div class="progress-info">
          <span class="progress-text">
            {{ progressText }}
          </span>
          <span class="progress-percentage">{{ progressPercentage }}%</span>
        </div>
        <div class="progress-bar-wrapper">
          <div class="progress-bar" :style="{ width: `${progressPercentage}%` }"></div>
        </div>
      </div>

      <div v-if="!queue.length" class="empty">
        <i class="bi bi-inboxes"></i>
        <p>尚未加入片段，请在左侧选择后加入队列。</p>
      </div>

      <ul v-else class="queue">
        <li v-for="item in queue" :key="item.id" :class="['queue-item', `status-${item.status}`]">
          <div class="item-main">
            <div class="title">{{ item.title || item.documentId }}</div>
            <div class="meta">
              <span>Chunk #{{ item.chunkIndex }}</span>
              <span>得分 {{ item.score?.toFixed(3) ?? '—' }}</span>
            </div>
          </div>
          <div class="item-actions">
            <span class="status-chip">{{ statusLabel(item.status) }}</span>
            <button
              v-if="item.status === 'failed'"
              class="ghost"
              @click="$emit('retry-segment', item.id)"
            >重试</button>
            <button class="icon" @click="$emit('remove-segment', item.id)">
              <i class="bi bi-x"></i>
            </button>
          </div>

          <div v-if="item.status === 'failed' && item.error" class="error-msg">
            {{ item.error || '抽取失败，请重试' }}
          </div>

          <div v-if="item.status === 'success' && item.result" class="success-msg">
            <div class="field-grid">
              <div v-for="(value, key) in item.result.fields" :key="key" class="field">
                <label>{{ key }}</label>
                <p>{{ value }}</p>
              </div>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <section class="summary-section">
      <header>
        <h4>实时聚合</h4>
        <button class="mini" @click="$emit('open-preview')">
          <i class="bi bi-eye"></i>
          查看全部
        </button>
      </header>

      <div v-if="!aggregatedResults.length" class="empty">
        <i class="bi bi-diagram-3"></i>
        <p>抽取完成后，系统会自动将相同数据聚合展示。</p>
      </div>

      <ul v-else class="summary-list">
        <li v-for="entity in aggregatedResults" :key="entity.entityId" class="summary-card">
          <div class="card-header">
            <div class="entity-label">{{ entity.label || entity.entityId }}</div>
            <span class="count">来自 {{ entity.segments.length }} 个片段</span>
          </div>
          <div class="fields">
            <div v-for="(value, field) in entity.fields" :key="field" class="field">
              <label>{{ field }}</label>
              <p>{{ value }}</p>
            </div>
          </div>
        </li>
      </ul>
    </section>
  </aside>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  queue: {
    type: Array,
    default: () => []
  },
  aggregatedResults: {
    type: Array,
    default: () => []
  },
  autoRefresh: {
    type: Boolean,
    default: true
  },
  taskStatus: {
    type: String,
    default: 'idle'
  }
})

const emit = defineEmits(['toggle-auto-refresh', 'open-preview', 'retry-segment', 'remove-segment'])

const statusLabel = (status) => {
  const map = {
    queued: '排队中',
    running: '抽取中',
    success: '完成',
    failed: '失败'
  }
  return map[status] || status
}

const toggleAutoRefresh = (event) => {
  emit('toggle-auto-refresh', event.target.checked)
}

// 计算进度统计
const progressStats = computed(() => {
  const total = props.queue.length
  const completed = props.queue.filter(item => item.status === 'success').length
  const failed = props.queue.filter(item => item.status === 'failed').length
  const processing = props.queue.filter(item => item.status === 'running').length
  const queued = props.queue.filter(item => item.status === 'queued').length
  
  return { total, completed, failed, processing, queued }
})

// 进度百分比
const progressPercentage = computed(() => {
  const { total, completed, failed } = progressStats.value
  if (total === 0) return 0
  // 成功和失败都算已完成
  return Math.round(((completed + failed) / total) * 100)
})

// 进度文本
const progressText = computed(() => {
  const { total, completed, failed, processing, queued } = progressStats.value
  const completedTotal = completed + failed
  
  if (completedTotal === 0) {
    if (processing > 0) {
      return `正在处理 ${processing} 个片段`
    }
    return `${queued} 个片段等待中`
  }
  
  const parts = [`已完成 ${completedTotal}/${total}`]
  if (completed > 0) {
    parts.push(`成功 ${completed}`)
  }
  if (failed > 0) {
    parts.push(`失败 ${failed}`)
  }
  if (processing > 0) {
    parts.push(`处理中 ${processing}`)
  }
  if (queued > 0) {
    parts.push(`等待中 ${queued}`)
  }
  
  return parts.join(' · ')
})
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px;
  height: 100%;
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

section {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 16px;
  padding: 18px 20px;
  border: 1px solid rgba(93, 111, 255, 0.12);
  box-shadow: 0 14px 32px rgba(86, 105, 255, 0.12);
}

section header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

section h4 {
  margin: 6px 0 0;
  font-size: 1.1rem;
  color: #2a3191;
}

.ghost,
.mini {
  border-radius: 999px;
  border: 1px solid rgba(86, 104, 255, 0.18);
  background: rgba(240, 244, 255, 0.85);
  color: #4855d8;
  padding: 6px 14px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 600;
}

.ghost:hover,
.mini:hover {
  background: rgba(240, 244, 255, 1);
}

.queue-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  color: rgba(40, 53, 120, 0.65);
  font-size: 0.9rem;
}

.refresh-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.progress-container {
  margin-bottom: 16px;
  padding: 12px 14px;
  background: rgba(240, 244, 255, 0.6);
  border-radius: 12px;
  border: 1px solid rgba(93, 111, 255, 0.08);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-text {
  font-size: 0.9rem;
  color: #2a3191;
  font-weight: 500;
}

.progress-percentage {
  font-size: 0.95rem;
  font-weight: 700;
  color: #4c55d8;
}

.progress-bar-wrapper {
  height: 8px;
  background: rgba(93, 111, 255, 0.1);
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #5d6fff, #667eea);
  border-radius: 999px;
  transition: width 0.3s ease;
  box-shadow: 0 2px 8px rgba(93, 111, 255, 0.3);
}

.empty {
  padding: 32px 12px;
  text-align: center;
  color: rgba(40, 53, 120, 0.6);
}

.empty i {
  font-size: 1.8rem;
  display: block;
  margin-bottom: 8px;
  color: rgba(88, 107, 255, 0.5);
}

.queue {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 260px;
  overflow-y: auto;
  padding-right: 6px;
}

.queue-item {
  border-radius: 14px;
  padding: 14px;
  background: rgba(247, 249, 255, 0.9);
  border: 1px solid rgba(93, 111, 255, 0.1);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.item-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-weight: 600;
  color: #313b92;
}

.meta {
  font-size: 0.85rem;
  color: rgba(41, 52, 120, 0.65);
  display: flex;
  gap: 8px;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #6479ff, #839dff);
}

.queue-item.status-running .status-chip {
  background: linear-gradient(135deg, #00c0ff, #0099f2);
}

.queue-item.status-failed .status-chip {
  background: linear-gradient(135deg, #ff6b6b, #ff4f7d);
}

.queue-item.status-success .status-chip {
  background: linear-gradient(135deg, #34d399, #10b981);
}

.error-msg {
  font-size: 0.85rem;
  color: #d24f63;
  background: rgba(255, 99, 132, 0.12);
  padding: 10px 12px;
  border-radius: 10px;
}

.success-msg {
  background: rgba(52, 211, 153, 0.12);
  padding: 12px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 0.8rem;
  color: rgba(32, 44, 98, 0.65);
}

.field p {
  margin: 0;
  font-size: 0.92rem;
  color: #1f2a68;
  font-weight: 600;
}

.summary-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 220px;
  overflow-y: auto;
  padding-right: 6px;
}

.summary-card {
  background: rgba(247, 249, 255, 0.95);
  border-radius: 14px;
  padding: 14px;
  border: 1px solid rgba(90, 108, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.entity-label {
  font-weight: 600;
  color: #2f39a0;
}

.count {
  font-size: 0.85rem;
  color: rgba(35, 46, 120, 0.65);
}

.fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fields label {
  font-size: 0.8rem;
  color: rgba(35, 46, 120, 0.6);
}

.fields p {
  margin: 0;
  font-size: 0.92rem;
  color: #1f2a68;
}

.icon {
  border: none;
  background: transparent;
  color: rgba(55, 68, 150, 0.55);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.icon:hover {
  color: rgba(55, 68, 150, 0.85);
}

@media (max-width: 768px) {
  .sidebar {
    padding: 0;
  }
}
</style>

