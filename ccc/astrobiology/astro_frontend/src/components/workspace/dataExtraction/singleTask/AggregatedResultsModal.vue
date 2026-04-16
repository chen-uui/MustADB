<template>
  <Teleport to="body">
    <transition name="fade">
      <div v-if="modelValue" class="modal-overlay" @click.self="close">
        <div class="modal">
          <header>
            <div>
              <h3>实时抽取结果</h3>
              <p>系统已自动合并重复数据，可展开查看来源片段</p>
            </div>
            <div class="actions">
              <button class="ghost" :disabled="isLoading" @click="$emit('export')">
                <i class="bi bi-download"></i>
                导出
              </button>
              <button class="icon" @click="close">
                <i class="bi bi-x-lg"></i>
              </button>
            </div>
          </header>

          <div class="content">
            <div v-if="isLoading" class="loading">
              <i class="bi bi-arrow-repeat"></i>
              正在更新，请稍候...
            </div>

            <div v-else-if="!results.length" class="empty">
              <i class="bi bi-collection"></i>
              <p>暂无抽取结果，请稍后再试。</p>
            </div>

            <div v-else class="results">
              <details v-for="entity in results" :key="entity.entityId" open>
                <summary>
                  <div class="summary-main">
                    <span class="title">{{ entity.label || entity.entityId }}</span>
                    <span class="count">来自 {{ entity.segments.length }} 个片段</span>
                  </div>
                  <span class="timestamp" v-if="entity.updatedAt">最后更新 {{ formatTime(entity.updatedAt) }}</span>
                </summary>

                <div class="fields">
                  <div v-for="(value, field) in entity.fields" :key="field" class="field">
                    <label>{{ field }}</label>
                    <p>{{ value }}</p>
                  </div>
                </div>

                <div class="segments">
                  <h5>来源片段</h5>
                  <ul>
                    <li v-for="seg in entity.segments" :key="seg.id" class="segment-item">
                      <div class="segment-header">
                        <div class="meta">
                          <span class="meta-item">{{ seg.documentId }}</span>
                          <span class="meta-item">Chunk #{{ seg.chunkIndex }}</span>
                          <span class="meta-item">得分 {{ seg.score?.toFixed(3) ?? '—' }}</span>
                        </div>
                        <button class="toggle-content-btn" @click="toggleSegmentContent(seg.id)">
                          <i :class="expandedSegments.has(seg.id) ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                          {{ expandedSegments.has(seg.id) ? '收起内容' : '查看内容' }}
                        </button>
                      </div>
                      <div v-if="expandedSegments.has(seg.id)" class="content-full">
                        <p>{{ seg.content }}</p>
                      </div>
                    </li>
                  </ul>
                </div>
              </details>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  results: {
    type: Array,
    default: () => []
  },
  isLoading: Boolean
})

const emit = defineEmits(['update:model-value', 'export'])

const expandedSegments = ref(new Set())

const toggleSegmentContent = (segmentId) => {
  if (expandedSegments.value.has(segmentId)) {
    expandedSegments.value.delete(segmentId)
  } else {
    expandedSegments.value.add(segmentId)
  }
}

const close = () => {
  emit('update:model-value', false)
}

const formatTime = (value) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleString()
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(21, 26, 64, 0.52);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  width: min(960px, 92vw);
  max-height: 86vh;
  background: linear-gradient(160deg, #f8f9ff 0%, #ffffff 100%);
  border-radius: 24px;
  box-shadow: 0 36px 80px rgba(36, 44, 130, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

header {
  padding: 24px 28px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
  border-bottom: 1px solid rgba(86, 102, 255, 0.12);
}

header h3 {
  margin: 0 0 6px;
  font-size: 1.5rem;
  color: #232c7a;
}

header p {
  margin: 0;
  color: rgba(35, 44, 122, 0.65);
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ghost {
  border-radius: 999px;
  border: 1px solid rgba(86, 104, 255, 0.22);
  background: rgba(240, 244, 255, 0.9);
  color: #4653d9;
  padding: 8px 16px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.ghost:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.icon {
  border: none;
  background: transparent;
  color: rgba(38, 46, 120, 0.5);
  cursor: pointer;
}

.icon:hover {
  color: rgba(38, 46, 120, 0.85);
}

.content {
  padding: 0 28px 28px;
  overflow-y: auto;
  flex: 1;
}

.loading,
.empty {
  padding: 60px 20px;
  text-align: center;
  color: rgba(38, 46, 120, 0.6);
}

.loading i {
  animation: spin 1s linear infinite;
  display: block;
  font-size: 2rem;
  color: rgba(76, 96, 255, 0.6);
  margin-bottom: 12px;
}

.empty i {
  font-size: 2rem;
  color: rgba(76, 96, 255, 0.5);
  margin-bottom: 12px;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

details {
  border: 1px solid rgba(86, 104, 255, 0.15);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.95);
  overflow: hidden;
}

summary {
  list-style: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  cursor: pointer;
}

summary::-webkit-details-marker {
  display: none;
}

.summary-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-main .title {
  font-weight: 600;
  font-size: 1.1rem;
  color: #2a3394;
}

.summary-main .count {
  font-size: 0.85rem;
  color: rgba(32, 44, 120, 0.6);
}

.timestamp {
  font-size: 0.85rem;
  color: rgba(32, 44, 120, 0.6);
}

.fields {
  display: grid;
  gap: 12px;
  padding: 0 20px 16px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.field {
  background: rgba(246, 248, 255, 0.9);
  border-radius: 12px;
  padding: 12px;
  border: 1px solid rgba(86, 104, 255, 0.12);
}

.field label {
  font-size: 0.8rem;
  color: rgba(35, 46, 120, 0.6);
}

.field p {
  margin: 6px 0 0;
  color: #1f2a68;
  font-weight: 600;
}

.segments {
  padding: 0 20px 20px;
}

.segments h5 {
  margin: 0 0 8px;
  color: #2f399c;
}

.segments ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.segment-item {
  background: rgba(241, 244, 255, 0.9);
  border-radius: 12px;
  padding: 12px;
  border: 1px solid rgba(86, 104, 255, 0.12);
}

.segment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.segments .meta {
  display: flex;
  gap: 12px;
  color: rgba(35, 46, 120, 0.6);
  font-size: 0.85rem;
  flex-wrap: wrap;
}

.meta-item {
  padding: 2px 8px;
  background: rgba(86, 104, 255, 0.08);
  border-radius: 6px;
  font-weight: 500;
}

.toggle-content-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(86, 104, 255, 0.2);
  background: rgba(240, 244, 255, 0.9);
  color: #4653d9;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.toggle-content-btn:hover {
  background: rgba(240, 244, 255, 1);
  border-color: rgba(86, 104, 255, 0.3);
}

.content-full {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(86, 104, 255, 0.1);
}

.content-full p {
  margin: 0;
  color: rgba(31, 42, 104, 0.88);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

