<template>
  <div class="toolbar">
    <div class="toolbar-left">
      <button class="btn btn-secondary" @click="$emit('refresh')">
        <i class="icon-refresh"></i>
        刷新
      </button>
      <button class="btn btn-warning" :disabled="selectedCount === 0" @click="$emit('batch-restore')">
        <i class="icon-restore"></i>
        批量恢复 ({{ selectedCount }})
      </button>
      <button class="btn btn-danger" :disabled="selectedCount === 0" @click="$emit('batch-delete')">
        <i class="icon-delete"></i>
        永久删除 ({{ selectedCount }})
      </button>
      <button class="btn btn-outline" @click="$emit('back')">
        <i class="icon-back"></i>
        返回管理
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
  searchQuery: {
    type: String,
    default: ''
  }
})

const emit = defineEmits([
  'refresh',
  'batch-restore',
  'batch-delete',
  'back',
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

.btn-warning {
  background: #ffc107;
  color: #212529;
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

.icon-refresh::before { content: '↻'; }
.icon-restore::before { content: '↺'; }
.icon-delete::before { content: '🗑'; }
.icon-back::before { content: '←'; }
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
