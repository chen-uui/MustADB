<template>
  <header class="task-header">
    <div class="status-block">
      <div class="label">当前任务</div>
      <div class="title">{{ keywordsLabel }}</div>
      <div class="meta">
        <span class="chip" :class="`status-${task.status}`">{{ statusText }}</span>
        <span v-if="task.startedAt" class="timestamp">{{ formattedStartedAt }}</span>
      </div>
    </div>

    <div class="actions">
      <button
        class="ghost"
        :disabled="!task.canCancel"
        @click="$emit('cancel-task')"
      >
        <i class="bi bi-stop-circle"></i>
        取消任务
      </button>
      <button class="primary" @click="$emit('restart-task')">
        <i class="bi bi-arrow-clockwise"></i>
        重置
      </button>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    default: () => ({})
  }
})

const keywordsLabel = computed(() => {
  if (!props.task.keywords?.length) {
    return '尚未开始'
  }
  return props.task.keywords.join('，')
})

const statusText = computed(() => {
  const map = {
    idle: '等待中',
    searching: '检索中',
    search_complete: '检索完成',
    running: '抽取中',
    cancelled: '已取消',
    completed: '已完成',
    failed: '失败'
  }
  return map[props.task.status] || '未知状态'
})

const formattedStartedAt = computed(() => {
  if (!props.task.startedAt) {
    return ''
  }
  const date = new Date(props.task.startedAt)
  return `开始于 ${date.toLocaleString()}`
})
</script>

<style scoped>
.task-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 18px 48px rgba(79, 97, 255, 0.1);
  border: 1px solid rgba(79, 97, 255, 0.12);
}

.status-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.label {
  font-size: 0.9rem;
  color: rgba(60, 72, 130, 0.7);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.title {
  font-size: 1.4rem;
  font-weight: 600;
  color: #2b3489;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.85rem;
  background: rgba(88, 107, 255, 0.12);
  color: #515bda;
  font-weight: 500;
}

.chip.status-searching,
.chip.status-running {
  background: rgba(76, 175, 255, 0.18);
  color: #055b96;
}

.chip.status-completed {
  background: rgba(38, 222, 129, 0.18);
  color: #147a44;
}

.chip.status-cancelled,
.chip.status-failed {
  background: rgba(255, 99, 132, 0.16);
  color: #c03a52;
}

.timestamp {
  font-size: 0.85rem;
  color: rgba(50, 63, 120, 0.65);
}

.actions {
  display: flex;
  gap: 12px;
}

.actions button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  padding: 10px 22px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.actions button i {
  font-size: 1.1rem;
}

.actions button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.actions .primary {
  background: linear-gradient(135deg, #5168ff, #6f8dff);
  color: white;
  box-shadow: 0 14px 30px rgba(82, 109, 255, 0.35);
}

.actions .primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 40px rgba(82, 109, 255, 0.45);
}

.actions .ghost {
  background: rgba(82, 102, 255, 0.08);
  color: #4a5bf9;
  border: 1px solid rgba(82, 102, 255, 0.18);
}

.actions .ghost:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(82, 102, 255, 0.18);
}

@media (max-width: 768px) {
  .task-header {
    flex-direction: column;
    gap: 18px;
    align-items: flex-start;
  }

  .actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>

