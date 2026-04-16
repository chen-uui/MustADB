<template>
  <div class="table-container">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <div v-else-if="meteorites.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <h3>暂无待审核数据</h3>
      <p>所有陨石数据都已处理完成</p>
    </div>

    <table v-else class="meteorite-table">
      <thead>
        <tr>
          <th class="checkbox-col">
            <input type="checkbox" :checked="isAllSelected" @change="$emit('toggle-select-all', $event.target.checked)" />
          </th>
          <th class="sortable" @click="$emit('sort', 'name')">
            名称
            <i :class="getSortIcon('name')"></i>
          </th>
          <th class="sortable" @click="$emit('sort', 'classification')">
            分类
            <i :class="getSortIcon('classification')"></i>
          </th>
          <th>发现地点</th>
          <th>来源</th>
          <th class="sortable" @click="$emit('sort', 'confidence_score')">
            置信度
            <i :class="getSortIcon('confidence_score')"></i>
          </th>
          <th class="sortable" @click="$emit('sort', 'created_at')">
            提交时间
            <i :class="getSortIcon('created_at')"></i>
          </th>
          <th class="actions-col">操作</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="meteorite in meteorites"
          :key="meteorite.id"
          :class="{ selected: selectedItems.includes(meteorite.id) }"
        >
          <td class="checkbox-col">
            <input
              type="checkbox"
              :checked="selectedItems.includes(meteorite.id)"
              @change="toggleRowSelection(meteorite.id, $event.target.checked)"
            />
          </td>
          <td class="name-col">
            <div class="name-info">
              <strong>{{ meteorite.name }}</strong>
              <div v-if="meteorite.organic_compound_names" class="organic-compounds">
                <span
                  v-for="compound in meteorite.organic_compound_names.slice(0, 2)"
                  :key="compound"
                  class="compound-tag"
                >
                  {{ compound }}
                </span>
                <span v-if="meteorite.organic_compound_names.length > 2" class="more-compounds">
                  +{{ meteorite.organic_compound_names.length - 2 }}
                </span>
              </div>
            </div>
          </td>
          <td>
            <span class="classification-badge">{{ meteorite.classification }}</span>
          </td>
          <td>{{ meteorite.discovery_location || '-' }}</td>
          <td>{{ meteorite.origin || '-' }}</td>
          <td>
            <div class="confidence-score">
              <div class="score-bar">
                <div class="score-fill" :style="{ width: `${meteorite.confidence_score * 100}%` }"></div>
              </div>
              <span class="score-text">{{ (meteorite.confidence_score * 100).toFixed(1) }}%</span>
            </div>
          </td>
          <td>{{ formatDate(meteorite.created_at) }}</td>
          <td class="actions-col">
            <div class="action-buttons">
              <button class="btn-icon btn-view" title="查看详情" @click="$emit('view', meteorite)">
                <i class="icon-eye"></i>
              </button>
              <button class="btn-icon btn-approve" title="通过审核" @click="$emit('approve', meteorite)">
                <i class="icon-check"></i>
              </button>
              <button class="btn-icon btn-reject" title="拒绝审核" @click="$emit('reject', meteorite)">
                <i class="icon-close"></i>
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  },
  meteorites: {
    type: Array,
    default: () => []
  },
  selectedItems: {
    type: Array,
    default: () => []
  },
  isAllSelected: {
    type: Boolean,
    default: false
  },
  getSortIcon: {
    type: Function,
    required: true
  },
  formatDate: {
    type: Function,
    required: true
  }
})

const emit = defineEmits(['toggle-select-all', 'sort', 'view', 'approve', 'reject', 'update:selectedItems'])

const toggleRowSelection = (id, checked) => {
  const nextSelected = checked
    ? [...props.selectedItems, id]
    : props.selectedItems.filter((itemId) => itemId !== id)

  emit('update:selectedItems', nextSelected)
}
</script>

<style scoped>
.table-container {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.meteorite-table {
  width: 100%;
  border-collapse: collapse;
}

.meteorite-table th,
.meteorite-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e9ecef;
}

.meteorite-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #495057;
}

.meteorite-table tr:hover {
  background: #f8f9fa;
}

.meteorite-table tr.selected {
  background: #e3f2fd;
}

.sortable {
  cursor: pointer;
  user-select: none;
}

.sortable i {
  margin-left: 4px;
  opacity: 0.5;
}

.checkbox-col {
  width: 40px;
}

.name-col {
  min-width: 200px;
}

.name-info strong {
  display: block;
  margin-bottom: 4px;
}

.organic-compounds {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.compound-tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 6px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.more-compounds {
  background: #f5f5f5;
  color: #666;
  padding: 2px 6px;
  border-radius: 12px;
  font-size: 11px;
}

.classification-badge {
  background: #fff3e0;
  color: #f57c00;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.confidence-score {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-bar {
  width: 60px;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
  transition: width 0.3s ease;
}

.score-text {
  font-size: 12px;
  font-weight: 500;
  color: #495057;
}

.actions-col {
  width: 120px;
}

.action-buttons {
  display: flex;
  gap: 4px;
}

.btn-icon {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.btn-view {
  background: #e3f2fd;
  color: #1976d2;
}

.btn-view:hover {
  background: #bbdefb;
}

.btn-approve {
  background: #e8f5e9;
  color: #2e7d32;
}

.btn-approve:hover {
  background: #c8e6c9;
}

.btn-reject {
  background: #ffebee;
  color: #d32f2f;
}

.btn-reject:hover {
  background: #ffcdd2;
}

.icon-eye::before { content: '👁'; }
.icon-check::before { content: '✓'; }
.icon-close::before { content: '✕'; }
.icon-sort::before { content: '↕'; }
.icon-sort-up::before { content: '↑'; }
.icon-sort-down::before { content: '↓'; }
</style>
