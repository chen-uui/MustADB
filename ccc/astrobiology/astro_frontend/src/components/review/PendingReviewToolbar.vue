<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <button class="btn btn-secondary" @click="$emit('refresh')">
        <i class="icon-refresh"></i>
        刷新
      </button>
      <button class="btn btn-success" :disabled="selectedCount === 0" @click="$emit('batch-approve')">
        <i class="icon-check"></i>
        批量通过 ({{ selectedCount }})
      </button>
      <button class="btn btn-danger" :disabled="selectedCount === 0" @click="$emit('batch-reject')">
        <i class="icon-close"></i>
        批量拒绝 ({{ selectedCount }})
      </button>
      <button class="btn btn-success btn-approve-all" :disabled="loading" @click="$emit('approve-all')">
        <i class="icon-check-all"></i>
        一键通过全部
      </button>
      <button class="btn btn-danger btn-reject-all" :disabled="loading" @click="$emit('reject-all')">
        <i class="icon-close-all"></i>
        一键拒绝全部
      </button>
    </div>
    <div class="toolbar-right">
      <div class="search-box">
        <input
          :value="searchQuery"
          type="text"
          placeholder="搜索..."
          @input="handleInput"
        />
        <i class="icon-search"></i>
      </div>
      <button class="btn btn-outline" @click="$emit('toggle-filters')">
        <i class="icon-filter"></i>
        筛选
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  selectedCount: {
    type: Number,
    default: 0
  },
  loading: {
    type: Boolean,
    default: false
  },
  searchQuery: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'refresh',
  'batch-approve',
  'batch-reject',
  'approve-all',
  'reject-all',
  'toggle-filters',
  'update:searchQuery',
  'search'
])

const handleInput = (event) => {
  emit('update:searchQuery', event.target.value)
  emit('search')
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  gap: 16px;
}

.toolbar-left {
  display: flex;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-box {
  position: relative;
}

.search-box input {
  width: 300px;
  padding: 8px 40px 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.search-box .icon-search {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-outline {
  background: white;
  color: #495057;
  border: 1px solid #ced4da;
}

.btn-approve-all {
  margin-left: 8px;
}

.btn-reject-all {
  margin-left: 8px;
}

.icon-refresh::before { content: '↻'; }
.icon-check::before { content: '✓'; }
.icon-close::before { content: '✕'; }
.icon-check-all::before { content: '✓'; }
.icon-close-all::before { content: '✕'; }
.icon-search::before { content: '⌕'; }
.icon-filter::before { content: '☰'; }

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left,
  .toolbar-right {
    justify-content: center;
    flex-wrap: wrap;
  }

  .search-box input {
    width: 100%;
  }
}
</style>
