<template>
  <div class="pending-review">
    <!-- Page header -->
    <div class="page-header">
      <h1>待审核陨石</h1>
      <p class="page-description">管理和审核待处理的陨石数据</p>
    </div>

    <!-- Toolbar -->
    <PendingReviewToolbar
      :selected-count="selectedItems.length"
      :loading="loading"
      :search-query="searchQuery"
      @refresh="refreshData"
      @batch-approve="batchApprove"
      @batch-reject="batchReject"
      @approve-all="approveAll"
      @reject-all="rejectAll"
      @toggle-filters="showFilters = !showFilters"
      @update:search-query="searchQuery = $event"
      @search="handleSearch"
    />

    <!-- Filters panel -->
    <div v-if="showFilters" class="filters-panel">
      <div class="filter-row">
        <div class="filter-group">
          <label>分类</label>
          <select v-model="filters.classification">
            <option value="">全部分类</option>
            <option v-for="cls in classificationOptions" :key="cls" :value="cls">
              {{ cls }}
            </option>
          </select>
        </div>
        <div class="filter-group">
          <label>来源</label>
          <select v-model="filters.origin">
            <option value="">全部来源</option>
            <option v-for="origin in originOptions" :key="origin" :value="origin">
              {{ origin }}
            </option>
          </select>
        </div>
        <div class="filter-group">
          <label>置信度</label>
          <div class="range-filter">
            <input 
              type="number" 
              v-model="filters.confidence_min" 
              placeholder="最小值"
              min="0" 
              max="1" 
              step="0.1"
            />
            <span>-</span>
            <input 
              type="number" 
              v-model="filters.confidence_max" 
              placeholder="最大值"
              min="0" 
              max="1" 
              step="0.1"
            />
          </div>
        </div>
        <div class="filter-actions">
          <button class="btn btn-primary" @click="applyFilters">应用筛选</button>
          <button class="btn btn-outline" @click="clearFilters">清除筛选</button>
        </div>
      </div>
    </div>

    <!-- Data table -->
    <PendingReviewTable
      :loading="loading"
      :meteorites="meteorites"
      :selected-items="selectedItems"
      :is-all-selected="isAllSelected"
      :get-sort-icon="getSortIcon"
      :format-date="formatDate"
      @toggle-select-all="toggleSelectAll"
      @sort="sortBy"
      @view="viewMeteorite"
      @approve="approveMeteorite"
      @reject="rejectMeteorite"
      @update:selected-items="selectedItems = $event"
    />

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination">
      <button 
        class="btn page-btn" 
        @click="goToPage(currentPage - 1)"
        :disabled="currentPage === 1"
      >
        涓婁竴椤?
      </button>
      
      <div class="page-numbers">
        <button 
          v-for="page in visiblePages" 
          :key="page"
          class="btn page-btn"
          :class="{ active: page === currentPage }"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
      </div>
      
      <button 
        class="btn page-btn" 
        @click="goToPage(currentPage + 1)"
        :disabled="currentPage === totalPages"
      >
        涓嬩竴椤?
      </button>
      
      <div class="page-info">
        绗?{{ currentPage }} 椤碉紝鍏?{{ totalPages }} 椤碉紝鎬昏 {{ totalCount }} 鏉¤褰?
      </div>
    </div>

    <!-- Details dialog -->
    <div v-if="showViewDialog" class="modal-overlay" @click="closeDialogs">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>陨石详情</h3>
          <button class="btn-close" @click="closeDialogs">×</button>
        </div>
        <div class="modal-body">
          <div class="detail-content">
            <div class="detail-section">
              <h4>基本信息</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>名称</label>
                  <span>{{ selectedMeteorite?.name }}</span>
                </div>
                <div class="detail-item">
                  <label>分类</label>
                  <span>{{ selectedMeteorite?.classification }}</span>
                </div>
                <div class="detail-item">
                  <label>鍙戠幇鍦扮偣</label>
                  <span>{{ selectedMeteorite?.discovery_location || '-' }}</span>
                </div>
                <div class="detail-item">
                  <label>来源</label>
                  <span>{{ selectedMeteorite?.origin || '-' }}</span>
                </div>
                <div class="detail-item">
                  <label>置信度</label>
                  <span>{{ selectedMeteorite?.confidence_score ? (selectedMeteorite.confidence_score * 100).toFixed(1) + '%' : '-' }}</span>
                </div>
                <div class="detail-item">
                  <label>鎻愪氦鏃堕棿</label>
                  <span>{{ formatDate(selectedMeteorite?.created_at) }}</span>
                </div>
              </div>
            </div>
            
            <div v-if="selectedMeteorite?.organic_compound_names?.length" class="detail-section">
              <h4>有机化合物</h4>
              <div class="compounds-list">
                <span 
                  v-for="compound in selectedMeteorite.organic_compound_names" 
                  :key="compound"
                  class="compound-tag"
                >
                  {{ compound }}
                </span>
              </div>
            </div>
            
            <div v-if="selectedMeteorite?.description" class="detail-section">
              <h4>描述</h4>
              <p class="detail-text">{{ selectedMeteorite.description }}</p>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-success" @click="approveMeteorite(selectedMeteorite)">
            <i class="icon-check"></i>
            通过审核
          </button>
          <button class="btn btn-danger" @click="rejectMeteorite(selectedMeteorite)">
            <i class="icon-close"></i>
            拒绝审核
          </button>
          <button class="btn btn-outline" @click="closeDialogs">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PDFService from '@/services/pdfService.js'
import { useReviewActions } from '@/composables/useReviewActions.js'
import { useReviewFilters } from '@/composables/useReviewFilters.js'
import { useReviewSelection } from '@/composables/useReviewSelection.js'
import PendingReviewTable from '@/components/review/PendingReviewTable.vue'
import PendingReviewToolbar from '@/components/review/PendingReviewToolbar.vue'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess, getApiMessage } from '@/utils/apiResponse'

export default {
  name: 'PendingReview',
  components: {
    PendingReviewTable,
    PendingReviewToolbar
  },
  emits: ['navigate'],
  setup() {
    // Reactive state
    const loading = ref(false)
    const meteorites = ref([])
    const showViewDialog = ref(false)
    const selectedMeteorite = ref(null)
    const classificationOptions = ref([])
    const originOptions = ref([])
    
    const {
      searchQuery,
      showFilters,
      currentPage,
      pageSize,
      totalCount,
      totalPages,
      sortField,
      sortOrder,
      filters,
      visiblePages,
      handleSearch: runSearch,
      sortBy: updateSort,
      getSortIcon: resolveSortIcon,
      applyFilters: applyReviewFilters,
      clearFilters: clearReviewFilters,
      goToPage: changePage
    } = useReviewFilters()

    const {
      selectedItems,
      isAllSelected,
      toggleSelectAll: updateSelection,
      clearSelection
    } = useReviewSelection({
      items: meteorites,
      getItemId: (meteorite) => meteorite.id
    })

    const { runBatchAction } = useReviewActions({ selectedItems })

    const handleReviewError = (error, context = {}) => {
      if (context.phase === 'options') {
        console.error('加载筛选选项失败:', error)
        return
      }

      console.error('加载待审核数据失败:', error)
      ElMessage.error(getApiErrorMessage(error, '加载待审核数据失败'))
    }

    // Methods
    const loadMeteorites = async () => {
      loading.value = true
      try {
        const params = new URLSearchParams()
        params.append('page', currentPage.value)
        params.append('page_size', pageSize.value)
        
        if (sortField.value) {
          const ordering = sortOrder.value === 'desc' ? `-${sortField.value}` : sortField.value
          params.append('ordering', ordering)
        }
        
        if (searchQuery.value) {
          params.append('search', searchQuery.value)
        }
        
        Object.keys(filters.value).forEach(key => {
          if (filters.value[key]) {
            params.append(key, filters.value[key])
          }
        })
        
        const data = await PDFService.getPendingMeteorites(params)
        
        meteorites.value = data?.results || []
        totalCount.value = data?.count || 0
      } catch (error) {
        console.error('加载待审核数据失败:', error)
        ElMessage.error(getApiErrorMessage(error, '加载待审核数据失败'))
      } finally {
        loading.value = false
      }
    }

    const loadOptions = async () => {
      try {
        const data = await PDFService.getMeteoriteOptions()
        classificationOptions.value = data?.classifications || []
        originOptions.value = data?.origins || []
      } catch (error) {
        console.error('加载选项失败:', error)
      }
    }

    const refreshData = () => {
      currentPage.value = 1
      clearSelection()
      loadMeteorites()
    }

    const handleSearch = () => runSearch(loadMeteorites)

    const sortBy = (field) => updateSort(field, loadMeteorites)

    const getSortIcon = (field) => resolveSortIcon(field)

    const toggleSelectAll = (checked) => updateSelection(checked)

    const applyFilters = () => applyReviewFilters(loadMeteorites)

    const clearFilters = () => clearReviewFilters(loadMeteorites)

    const goToPage = (page) => changePage(page, loadMeteorites)

    const viewMeteorite = (meteorite) => {
      selectedMeteorite.value = meteorite
      showViewDialog.value = true
    }

    const approveMeteorite = async (meteorite) => {
      try {
        await ElMessageBox.confirm(`确认通过陨石“${meteorite.name}”吗？`, '通过审核', {
          type: 'warning'
        })
        const payload = ensureApiSuccess(
          await PDFService.approveMeteorite(meteorite.id, {
            reviewer_notes: '通过审核'
          }),
          '审核通过失败'
        )
        ElMessage.success(getApiMessage(payload, '审核通过成功'))
        closeDialogs()
        await loadMeteorites()
      } catch (error) {
        if (error === 'cancel') return
        console.error('审核通过失败:', error)
        ElMessage.error(getApiErrorMessage(error, '审核通过失败'))
      }
    }

    const rejectMeteorite = async (meteorite) => {
      try {
        await ElMessageBox.confirm(`确认拒绝陨石“${meteorite.name}”吗？`, '拒绝审核', {
          type: 'warning'
        })
        const payload = ensureApiSuccess(
          await PDFService.rejectMeteorite(meteorite.id, {
            reviewer_notes: '拒绝审核',
            reason: '数据不符合要求',
            rejection_reason: '数据不符合要求'
          }),
          '审核拒绝失败'
        )
        ElMessage.success(getApiMessage(payload, '审核拒绝成功'))
        closeDialogs()
        await loadMeteorites()
      } catch (error) {
        if (error === 'cancel') return
        console.error('审核拒绝失败:', error)
        ElMessage.error(getApiErrorMessage(error, '审核拒绝失败'))
      }
    }

    const batchApprove = async () => {
      if (selectedItems.value.length === 0) return

      try {
        await ElMessageBox.confirm(`确定要批量通过 ${selectedItems.value.length} 条记录吗？`, '批量通过', {
          type: 'warning'
        })

        await runBatchAction({
          execute: (id) =>
            PDFService.approveMeteorite(id, {
              reviewer_notes: '批量通过审核'
            }),
          afterSuccess: loadMeteorites
        })

        ElMessage.success('批量审核通过成功')
      } catch (error) {
        if (error === 'cancel') return
        console.error('批量审核通过失败:', error)
        ElMessage.error(getApiErrorMessage(error, '批量审核通过失败'))
      }
    }

    const batchReject = async () => {
      if (selectedItems.value.length === 0) return

      try {
        await ElMessageBox.confirm(`确定要批量拒绝 ${selectedItems.value.length} 条记录吗？`, '批量拒绝', {
          type: 'warning'
        })

        await runBatchAction({
          execute: (id) =>
            PDFService.rejectMeteorite(id, {
              reviewer_notes: '批量拒绝审核',
              reason: '数据不符合要求',
              rejection_reason: '数据不符合要求'
            }),
          afterSuccess: loadMeteorites
        })

        ElMessage.success('批量审核拒绝成功')
      } catch (error) {
        if (error === 'cancel') return
        console.error('批量审核拒绝失败:', error)
        ElMessage.error(getApiErrorMessage(error, '批量审核拒绝失败'))
      }
    }

    const approveAll = async () => {
      try {
        await ElMessageBox.confirm('确定要一键通过全部待审核陨石吗？此操作不可撤销。', '一键通过', {
          type: 'warning'
        })

        loading.value = true
        const result = ensureApiSuccess(
          await PDFService.approveAllMeteorite('一键通过全部审核'),
          '一键通过失败'
        )

        if (result.success_count > 0) {
          ElMessage.success(`成功通过 ${result.success_count} 条记录`)
          await loadMeteorites()
        } else {
          ElMessage.info(result.message || '没有可通过的记录')
        }

        if (result.errors?.length) {
          ElMessage.warning(`其中 ${result.errors.length} 条处理失败，请查看日志`)
          console.warn('部分记录处理失败:', result.errors)
        }
      } catch (error) {
        if (error === 'cancel') return
        console.error('一键通过失败:', error)
        ElMessage.error(getApiErrorMessage(error, '一键通过失败'))
      } finally {
        loading.value = false
      }
    }

    const rejectAll = async () => {
      try {
        const { value: reason } = await ElMessageBox.prompt('请输入拒绝原因', '一键拒绝', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          inputValue: '数据不符合要求'
        })
        if (!reason?.trim()) {
          ElMessage.warning('请输入拒绝原因')
          return
        }

        await ElMessageBox.confirm('确定要一键拒绝全部待审核陨石吗？此操作不可撤销。', '一键拒绝', {
          type: 'warning'
        })

        loading.value = true
        const result = ensureApiSuccess(
          await PDFService.rejectAllMeteorite(reason.trim(), 'data_quality', '一键拒绝全部审核'),
          '一键拒绝失败'
        )

        if (result.success_count > 0) {
          ElMessage.success(`成功拒绝 ${result.success_count} 条记录`)
          await loadMeteorites()
        } else {
          ElMessage.info(result.message || '没有可拒绝的记录')
        }

        if (result.errors?.length) {
          ElMessage.warning(`其中 ${result.errors.length} 条处理失败，请查看日志`)
          console.warn('部分记录处理失败:', result.errors)
        }
      } catch (error) {
        if (error === 'cancel') return
        console.error('一键拒绝失败:', error)
        ElMessage.error(getApiErrorMessage(error, '一键拒绝失败'))
      } finally {
        loading.value = false
      }
    }

    const closeDialogs = () => {
      showViewDialog.value = false
      selectedMeteorite.value = null
    }

    const formatDate = (dateString) => {
      if (!dateString) return '-'
      return new Date(dateString).toLocaleString('zh-CN')
    }

    // Lifecycle
    onMounted(() => {
      loadMeteorites()
      loadOptions()
    })

    // React to search changes
    watch(searchQuery, () => {
      if (searchQuery.value === '') {
        handleSearch()
      }
    })

    return {
      // Reactive state
      loading,
      meteorites,
      selectedItems,
      searchQuery,
      showFilters,
      showViewDialog,
      selectedMeteorite,
      currentPage,
      pageSize,
      totalCount,
      totalPages,
      sortField,
      sortOrder,
      filters,
      classificationOptions,
      originOptions,
      
      // Derived state
      isAllSelected,
      visiblePages,
      
      // Methods
      loadMeteorites,
      refreshData,
      handleSearch,
      sortBy,
      getSortIcon,
      toggleSelectAll,
      applyFilters,
      clearFilters,
      goToPage,
      viewMeteorite,
      approveMeteorite,
      rejectMeteorite,
      batchApprove,
      batchReject,
      approveAll,
      rejectAll,
      closeDialogs,
      formatDate
    }
  }
}
</script>

<style scoped>
/* Reuse shared meteorite management styles */
.pending-review {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.page-description {
  color: #666;
  font-size: 16px;
  margin: 0;
}

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

.filters-panel {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 24px;
}

.filter-row {
  display: flex;
  gap: 16px;
  align-items: end;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-group label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
}

.filter-group select,
.filter-group input {
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
  min-width: 120px;
}

.range-filter {
  display: flex;
  align-items: center;
  gap: 8px;
}

.range-filter input {
  width: 80px;
  min-width: 80px;
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

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
  position: sticky;
  top: 0;
  z-index: 10;
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
  position: relative;
}

.sortable:hover {
  background: #e9ecef;
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
  background: #e8f5e8;
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

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.page-numbers {
  display: flex;
  gap: 4px;
}

.page-btn {
  width: 36px;
  height: 36px;
  border: 1px solid #ddd;
  background: white;
  color: #495057;
}

.page-btn.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.page-info {
  color: #666;
  font-size: 14px;
}

/* Button styles */
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

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0056b3;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #545b62;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #218838;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #c82333;
}

.btn-outline {
  background: white;
  color: #495057;
  border: 1px solid #ced4da;
}

.btn-outline:hover {
  background: #f8f9fa;
}

/* One-click action button styles */
.btn-approve-all {
  margin-left: 8px;
  background: #28a745;
  border-color: #28a745;
}

.btn-approve-all:hover:not(:disabled) {
  background: #218838;
  border-color: #1e7e34;
}

.btn-reject-all {
  margin-left: 8px;
  background: #dc3545;
  border-color: #dc3545;
}

.btn-reject-all:hover:not(:disabled) {
  background: #c82333;
  border-color: #bd2130;
}

/* Dialog styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  color: #000;
}

.modal-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.detail-content {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #495057;
  border-bottom: 1px solid #e9ecef;
  padding-bottom: 8px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
  text-transform: uppercase;
}

.detail-item span {
  font-size: 14px;
  color: #495057;
}

.detail-text {
  color: #495057;
  line-height: 1.5;
  margin: 0;
}

.compounds-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* Icon styles */
.icon-refresh::before { content: '↻'; }
.icon-check::before { content: '✓'; }
.icon-close::before { content: '✕'; }
.icon-search::before { content: '⌕'; }
.icon-filter::before { content: '☰'; }
.icon-eye::before { content: '👁'; }
.icon-sort::before { content: '↕'; }
.icon-sort-up::before { content: '↑'; }
.icon-sort-down::before { content: '↓'; }

/* Responsive styles */
@media (max-width: 768px) {
  .pending-review {
    padding: 16px;
  }
  
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  
  .toolbar-left,
  .toolbar-right {
    justify-content: center;
  }
  
  .search-box input {
    width: 100%;
  }
  
  .filter-row {
    flex-direction: column;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .meteorite-table {
    font-size: 12px;
  }
  
  .meteorite-table th,
  .meteorite-table td {
    padding: 8px 4px;
  }
  
  .pagination {
    flex-wrap: wrap;
  }
}
</style>

