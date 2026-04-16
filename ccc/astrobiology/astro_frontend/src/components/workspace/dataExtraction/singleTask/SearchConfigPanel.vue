<template>
  <div class="search-config">
    <header class="panel-header">
      <div>
        <div class="badge">STEP 1</div>
        <h3>设置关键词与排序</h3>
        <p>指定检索条件，系统会返回排序后的候选片段</p>
      </div>
      <div class="actions">
        <label class="toggle" :class="{ disabled }">
          <input
            type="checkbox"
            :checked="localAutoRefresh"
            :disabled="disabled"
            @change="toggleAutoRefresh"
          />
          <span>自动刷新进度</span>
        </label>
        <button
          class="primary"
          :disabled="isSearching || disabled || !canSubmit"
          @click="emitSearch"
        >
          <i v-if="!isSearching" class="bi bi-search"></i>
          <i v-else class="bi bi-arrow-repeat loading"></i>
          {{ isSearching ? '检索中...' : '开始检索' }}
        </button>
      </div>
    </header>

    <section class="body">
      <div class="field">
        <div class="field-header">
          <label>关键词</label>
          <div class="preset-keywords">
            <span class="preset-label">快速选择：</span>
            <button
              v-for="preset in presetKeywords"
              :key="preset.id"
              type="button"
              class="preset-btn"
              :class="{ active: activePreset === preset.id }"
              :disabled="disabled || isSearching"
              @click="applyPreset(preset)"
              :title="preset.description"
            >
              <i :class="preset.icon"></i>
              {{ preset.name }}
            </button>
          </div>
        </div>
        <KeywordChipsInput
          class="chips-input"
          :model-value="localFilters.keywords"
          :disabled="disabled"
          placeholder="请输入关键词，按回车或逗号添加，或使用上方预设"
          @update:model-value="updateKeywords"
          @draft-change="updateDraft"
        />
      </div>

      <div class="field sort">
        <label>排序</label>
        <div class="sort-options">
          <button
            v-for="option in sortOptions"
            :key="option.value"
            type="button"
            class="sort-btn"
            :class="{ active: localFilters.sortBy === option.value }"
            :disabled="disabled"
            @click="localFilters.sortBy = option.value"
          >
            <i :class="option.icon"></i>
            {{ option.label }}
          </button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, watch, computed } from 'vue'
import KeywordChipsInput from '@/components/workspace/dataExtraction/singleTask/KeywordChipsInput.vue'

const props = defineProps({
  filters: {
    type: Object,
    default: () => ({ keywords: [], sortBy: 'score_desc' })
  },
  isSearching: Boolean,
  disabled: Boolean
})

const emit = defineEmits(['update:filters', 'submit-search', 'toggle-auto-refresh'])

const localFilters = reactive({
  keywords: [...props.filters.keywords],
  sortBy: props.filters.sortBy
})

const localAutoRefresh = ref(props.filters.autoRefresh ?? true)
const localDraft = ref('')
const syncingFromProps = ref(false)
const activePreset = ref(null)

const canSubmit = computed(() => {
  return localFilters.keywords.length > 0 || localDraft.value.trim().length > 0
})

const sortOptions = [
  { value: 'score_desc', label: '按得分高 → 低', icon: 'bi bi-arrow-down' },
  { value: 'score_asc', label: '按得分低 → 高', icon: 'bi bi-arrow-up' },
  { value: 'page_asc', label: '按页码顺序', icon: 'bi bi-journal-text' }
]

// 预设关键词模板
const presetKeywords = [
  {
    id: 'searchable_data',
    name: '陨石搜索数据',
    description: '专门提取可用于陨石搜索功能的可检索数据（名称、分类、地点、来源、有机化合物）',
    icon: 'bi bi-search',
    keywords: [
      // 核心：陨石名称和标识
      'meteorite name', 'named meteorite',
      'Murchison', 'Tissint', 'Nakhla', 'Orgueil', 'Allende', 'Tagish Lake',
      'ALH 84001', 'EETA 79001', 'Winchcombe',
      // 核心：分类类型
      'meteorite classification', 'chondrite type',
      'CM2', 'CR2', 'CI', 'H5', 'L6', 'shergottite', 'nakhlite',
      // 核心：发现地点
      'discovery location', 'fell in', 'found in',
      'Antarctica', 'Australia', 'Morocco', 'Mars meteorite',
      // 核心：来源
      'Martian meteorite', 'lunar meteorite', 'asteroid',
      // 核心：有机化合物
      'organic compounds', 'amino acids', 'PAHs', 'organics'
    ]
  },
  {
    id: 'all_fields',
    name: '全部字段',
    description: '包含陨石名称、分类、发现地点、来源和有机化合物',
    icon: 'bi bi-stars',
    keywords: ['meteorite name', 'classification', 'discovery location', 'origin source', 'organic compounds']
  },
  {
    id: 'organic_focus',
    name: '有机化合物',
    description: '重点关注陨石中的有机物质',
    icon: 'bi bi-heart-pulse',
    keywords: ['meteorite', 'organic compounds', 'organic matter', 'amino acids', 'carbohydrates', 'PAHs', 'chondrite']
  },
  {
    id: 'classification',
    name: '分类信息',
    description: '重点关注陨石分类和类型',
    icon: 'bi bi-bar-chart',
    keywords: ['meteorite classification', 'chondrite', 'CM2', 'CR2', 'CI', 'H5', 'L6', 'shergottite', 'nakhlite']
  },
  {
    id: 'location',
    name: '发现地点',
    description: '重点关注陨石发现地点和来源',
    icon: 'bi bi-geo-alt',
    keywords: ['meteorite', 'discovery location', 'fall location', 'find location', 'Antarctica', 'Australia', 'Morocco']
  },
  {
    id: 'name_only',
    name: '陨石名称',
    description: '仅搜索具体的陨石名称',
    icon: 'bi bi-tag',
    keywords: ['meteorite name', 'Murchison', 'Tissint', 'Nakhla', 'Orgueil', 'Allende', 'ALH', 'EETA']
  }
]

const applyPreset = (preset) => {
  if (props.disabled || props.isSearching) return
  
  // 应用预设关键词
  localFilters.keywords = [...preset.keywords]
  localDraft.value = ''
  activePreset.value = preset.id
  emitFilters()
}

watch(
  () => props.filters,
  (next) => {
    syncingFromProps.value = true
    localFilters.keywords = [...next.keywords]
    localFilters.sortBy = next.sortBy
    if (typeof next.autoRefresh === 'boolean') {
      localAutoRefresh.value = next.autoRefresh
    }
    if (!next.keywords?.length) {
      localDraft.value = ''
    }
    Promise.resolve().then(() => {
      syncingFromProps.value = false
    })
  },
  { deep: true }
)

const emitFilters = () => {
  if (syncingFromProps.value) {
    return
  }
  emit('update:filters', {
    keywords: [...localFilters.keywords],
    sortBy: localFilters.sortBy
  })
}

const updateKeywords = (keywords) => {
  localFilters.keywords = keywords
  // 如果用户手动修改关键词，清除预设标记
  activePreset.value = null
  emitFilters()
}

const updateDraft = (value) => {
  localDraft.value = value
}

const commitDraft = () => {
  const trimmed = localDraft.value.trim()
  if (!trimmed) {
    return
  }
  if (!localFilters.keywords.includes(trimmed)) {
    localFilters.keywords = [...localFilters.keywords, trimmed]
  }
  localDraft.value = ''
  emitFilters()
}

const emitSearch = () => {
  commitDraft()
  emitFilters()
  emit('submit-search')
}

const toggleAutoRefresh = (event) => {
  localAutoRefresh.value = event.target.checked
  emit('toggle-auto-refresh', event.target.checked)
}

watch(
  () => localFilters.sortBy,
  () => {
    emitFilters()
  }
)
</script>

<style scoped>
.search-config {
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
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

.panel-header h3 {
  margin: 8px 0 4px;
  font-size: 1.45rem;
  color: #242b74;
}

.panel-header p {
  margin: 0;
  color: rgba(36, 43, 116, 0.65);
}

.actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(76, 86, 255, 0.1);
  color: #3e4ade;
  font-size: 0.9rem;
}

.toggle.disabled {
  opacity: 0.6;
}

.toggle input {
  accent-color: #5969ff;
}

.actions .primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  background: linear-gradient(130deg, #5168ff, #7b90ff);
  box-shadow: 0 16px 36px rgba(81, 104, 255, 0.28);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.actions .primary:disabled {
  cursor: not-allowed;
  opacity: 0.55;
  box-shadow: none;
}

.actions .primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 20px 42px rgba(81, 104, 255, 0.35);
}

.actions .loading {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field label {
  font-weight: 600;
  color: #2b3489;
}

.field-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preset-keywords {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.preset-label {
  font-size: 0.875rem;
  color: rgba(43, 52, 137, 0.7);
  font-weight: 500;
}

.preset-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(79, 100, 255, 0.25);
  background: white;
  color: #4b57d8;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.preset-btn:hover:not(:disabled) {
  background: rgba(79, 100, 255, 0.08);
  border-color: rgba(79, 100, 255, 0.4);
}

.preset-btn.active {
  background: linear-gradient(135deg, #4f66ff, #6d86ff);
  color: white;
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(79, 100, 255, 0.2);
}

.preset-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.preset-btn i {
  font-size: 0.875rem;
}

.chips-input {
  width: 100%;
}

.sort-options {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.sort-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 999px;
  border: 1px solid rgba(79, 100, 255, 0.2);
  background: rgba(247, 249, 255, 0.9);
  color: #4b57d8;
  cursor: pointer;
  transition: all 0.2s ease;
}

.sort-btn.active {
  background: linear-gradient(135deg, #4f66ff, #6d86ff);
  color: white;
  box-shadow: 0 12px 28px rgba(79, 100, 255, 0.28);
  border-color: transparent;
}

.sort-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>

