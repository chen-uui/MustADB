<template>
  <div class="unified-review">
    <AdminWorkspaceHeader 
      :active-tab="'unified-review'"
      @navigate="handleNavigate"
    />
    <div class="unified-review-content">
      <!-- Page header -->
      <div class="page-header">
        <h1>Unified Review Center</h1>
        <p class="page-description">Review and manage pending PDF documents and meteorite data</p>
      </div>

      <!-- Type tabs -->
    <div class="type-tabs">
      <button 
        v-for="tab in tabs" 
        :key="tab.id"
        :class="['tab-button', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id; loadData()"
      >
        <i :class="tab.icon"></i>
        {{ tab.label }}
        <span class="badge" v-if="tab.count > 0">{{ tab.count }}</span>
      </button>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn btn-secondary" @click="loadData">
          <i class="bi bi-arrow-clockwise"></i>
          Refresh
        </button>
        <button 
          class="btn btn-success" 
          @click="batchApprove"
          :disabled="selectedItems.length === 0"
        >
          <i class="bi bi-check-circle"></i>
          Batch Approve ({{ selectedItems.length }})
        </button>
        <button 
          class="btn btn-danger" 
          @click="batchReject"
          :disabled="selectedItems.length === 0"
        >
          <i class="bi bi-x-circle"></i>
          Batch Reject ({{ selectedItems.length }})
        </button>
      </div>
      <div class="toolbar-right">
        <div class="search-box">
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Search..."
            @input="handleSearch"
          />
          <i class="bi bi-search"></i>
        </div>
      </div>
    </div>

    <!-- Data table -->
    <div class="table-container">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading...</p>
      </div>
      
      <div v-else-if="displayItems.length === 0" class="empty-state">
        <div class="empty-icon">&#128237;</div>
        <h3>No Pending Items</h3>
        <p>All items have been reviewed</p>
      </div>
      
      <table v-else class="review-table">
        <thead>
          <tr>
            <th class="checkbox-col">
              <input 
                type="checkbox" 
                :checked="isAllSelected"
                @change="toggleSelectAll($event.target.checked)"
              />
            </th>
            <th>Type</th>
            <th>Title/Name</th>
            <th v-if="activeTab === 'all' || activeTab === 'pdf'">Authors</th>
            <th v-if="activeTab === 'all' || activeTab === 'meteorite'">Classification</th>
            <th>Upload Date</th>
            <th class="actions-col">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="item in displayItems" 
            :key="`${item.type}-${item.id}`"
            :class="{ 'selected': selectedItems.includes(`${item.type}-${item.id}`) }"
          >
            <td class="checkbox-col">
              <input 
                type="checkbox" 
                :value="`${item.type}-${item.id}`"
                v-model="selectedItems"
              />
            </td>
            <td>
              <span :class="['type-badge', item.type]">
                {{ item.type.toUpperCase() }}
              </span>
            </td>
            <td class="name-col">
              <strong>{{ item.type === 'pdf' ? item.title : item.name }}</strong>
              <div v-if="item.type === 'meteorite' && item.organic_compounds_summary" class="organic-hint">
                {{ item.organic_compounds_summary }}
              </div>
            </td>
            <td v-if="activeTab === 'all' || activeTab === 'pdf'">
              {{ item.authors || '-' }}
            </td>
            <td v-if="activeTab === 'all' || activeTab === 'meteorite'">
              <span v-if="item.classification" class="classification-badge">
                {{ item.classification }}
              </span>
              <span v-else>-</span>
            </td>
            <td>{{ formatDate(item.upload_date || item.created_at) }}</td>
            <td class="actions-col">
              <div class="action-buttons">
                <button 
                  class="btn-icon btn-view" 
                  @click="viewItem(item)"
                  title="View Details"
                >
                  <i class="bi bi-eye"></i>
                </button>
                <button 
                  class="btn-icon btn-approve" 
                  @click="approveItem(item)"
                  title="Approve"
                >
                  <i class="bi bi-check"></i>
                </button>
                <button 
                  class="btn-icon btn-reject" 
                  @click="rejectItem(item)"
                  title="Reject"
                >
                  <i class="bi bi-x"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Reject dialog -->
    <ReviewRejectDialog
      :visible="showRejectDialog"
      :item="currentRejectItem"
      :reason="rejectReason"
      @close="closeRejectDialog"
      @confirm="confirmReject"
      @update:reason="rejectReason = $event"
    />
    <ReviewDetailDialog
      :visible="showDetailDialog"
      :item="selectedItem"
      @close="closeDetailDialog"
      @approve="approveItem(selectedItem)"
      @reject="rejectItem(selectedItem)"
    />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiMethods } from '@/utils/apiClient.js'
import AdminWorkspaceHeader from '@/components/workspace/AdminWorkspaceHeader.vue'
import ReviewDetailDialog from '@/components/review/ReviewDetailDialog.vue'
import ReviewRejectDialog from '@/components/review/ReviewRejectDialog.vue'
import { useReviewActions } from '@/composables/useReviewActions.js'
import { useReviewSelection } from '@/composables/useReviewSelection.js'
import { useNotification, useConfirm } from '@/components/base/useNotification.js'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess, unwrapApiPayload } from '@/utils/apiResponse'

const emit = defineEmits(['navigate'])

const handleNavigate = (path) => {
  emit('navigate', path)
}

const activeTab = ref('all')
const loading = ref(false)
const pdfs = ref([])
const meteorites = ref([])
const searchQuery = ref('')
const showDetailDialog = ref(false)
const selectedItem = ref(null)
const showRejectDialog = ref(false)
const currentRejectItem = ref(null)
const rejectReason = ref('')

const tabs = computed(() => [
  { id: 'all', label: 'All', icon: 'bi bi-list-ul', count: pdfs.value.length + meteorites.value.length },
  { id: 'pdf', label: 'PDFs', icon: 'bi bi-file-pdf', count: pdfs.value.length },
  { id: 'meteorite', label: 'Meteorites', icon: 'bi bi-rocket', count: meteorites.value.length }
])

const displayItems = computed(() => {
  let items = []
  
  if (activeTab.value === 'all' || activeTab.value === 'pdf') {
    items.push(...pdfs.value.map(pdf => ({ ...pdf, type: 'pdf' })))
  }
  
  if (activeTab.value === 'all' || activeTab.value === 'meteorite') {
    items.push(...meteorites.value.map(met => ({ ...met, type: 'meteorite' })))
  }
  
  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    items = items.filter(item => {
      if (item.type === 'pdf') {
        return item.title?.toLowerCase().includes(query) || 
               item.authors?.toLowerCase().includes(query) ||
               item.filename?.toLowerCase().includes(query)
      } else {
        return item.name?.toLowerCase().includes(query) ||
               item.classification?.toLowerCase().includes(query) ||
               item.discovery_location?.toLowerCase().includes(query)
      }
    })
  }
  
  return items
})

const {
  selectedItems,
  isAllSelected,
  toggleSelectAll: updateSelection
} = useReviewSelection({
  items: displayItems,
  getItemId: (item) => `${item.type}-${item.id}`
})

const { runBatchAction, clearSelection } = useReviewActions({ selectedItems })
const { showSuccess, showError } = useNotification()
const { confirm } = useConfirm()
const parseSelectionKey = (itemId) => {
  const separatorIndex = itemId.indexOf('-')
  if (separatorIndex === -1) {
    return { type: '', id: itemId }
  }

  return {
    type: itemId.slice(0, separatorIndex),
    id: itemId.slice(separatorIndex + 1)
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const type = activeTab.value === 'all' ? 'all' : activeTab.value
    const url = `/api/pdf/review/pending/`
    const response = await apiMethods.get(url, {
      params: { 
        type: type, 
        status: 'pending', 
        page: 1, 
        page_size: 100 
      }
    })

    const payload = unwrapApiPayload(response)

    if (payload) {
      // Expected backend shape: { pdfs: [], meteorites: [], total: 0, page: 1, page_size: 20 }
      pdfs.value = payload.pdfs || []
      meteorites.value = payload.meteorites || []
      
      pdfs.value = pdfs.value.map(pdf => ({
        id: pdf.id,
        type: 'pdf',
        title: pdf.title || pdf.filename || 'Untitled',
        filename: pdf.filename,
        authors: pdf.authors,
        uploaded_by: pdf.uploaded_by || 'N/A',
        upload_date: pdf.upload_date,
        status: pdf.review_status || 'pending',
        file_size: pdf.file_size,
        page_count: pdf.page_count,
        year: pdf.year,
        journal: pdf.journal,
        category: pdf.category || 'User Upload',
        detail_link: `/pdf-detail/${pdf.id}`
      }))
      
      meteorites.value = meteorites.value.map(meteorite => ({
        id: meteorite.id,
        type: 'meteorite',
        name: meteorite.name || 'Unknown Meteorite',
        title: meteorite.name || 'Unknown Meteorite',
        organic_compounds_summary: meteorite.organic_compounds_summary,
        uploaded_by: meteorite.assigned_reviewer || 'System',
        upload_date: meteorite.created_at,
        created_at: meteorite.created_at,
        status: meteorite.review_status || 'pending',
        classification: meteorite.classification || '',
        confidence_score: meteorite.confidence_score || 0,
        discovery_location: meteorite.discovery_location || '',
        origin: meteorite.origin || '',
        detail_link: `/admin/meteorite-detail/${meteorite.id}`
      }))
    } else {
      console.warn('Unexpected response format:', response)
      pdfs.value = []
      meteorites.value = []
    }
  } catch (error) {
    console.error('Failed to load pending reviews:', error)
    showError(error, '加载待审核数据失败')
    pdfs.value = []
    meteorites.value = []
  } finally {
    loading.value = false
  }
}

const approveItem = async (item) => {
  try {
    await confirm(`确认通过这个${item.type === 'pdf' ? ' PDF' : '陨石'}条目吗？`, '通过审核')
    const response = await apiMethods.post(
      `/api/pdf/review/approve/`,
      {
        type: item.type,
        id: item.id,
        notes: 'Approved by reviewer'
      }
    )

    ensureApiSuccess(response, '审核通过失败')
    showSuccess('审核通过成功')
    closeDetailDialog()
    await loadData()
  } catch (error) {
    if (error === 'cancel') return
    console.error('Approval error:', error)
    showError(error, '审核通过失败')
  }
}

const rejectItem = (item) => {
  currentRejectItem.value = item
  rejectReason.value = ''
  showRejectDialog.value = true
}

const closeRejectDialog = () => {
  showRejectDialog.value = false
  currentRejectItem.value = null
  rejectReason.value = ''
}

const batchApprove = async () => {
  if (selectedItems.value.length === 0) return

  try {
    await confirm(`确认通过选中的 ${selectedItems.value.length} 个条目吗？`, '批量通过')
    await runBatchAction({
      execute: (itemId) => {
        const { type, id } = parseSelectionKey(itemId)
        return apiMethods.post(
          `/api/pdf/review/approve/`,
          { type, id, notes: 'Batch approved' }
        )
      },
      afterSuccess: loadData
    })
    showSuccess('批量通过成功')
  } catch (error) {
    if (error === 'cancel') return
    console.error('Batch approval error:', error)
    showError(error, '批量通过失败')
  }
}

const batchReject = async () => {
  if (selectedItems.value.length === 0) return
  
  currentRejectItem.value = {
    type: 'batch',
    count: selectedItems.value.length
  }
  rejectReason.value = ''
  showRejectDialog.value = true
}

const confirmReject = async () => {
  if (!rejectReason.value.trim()) {
    return
  }
  
  const item = currentRejectItem.value
  if (!item) return
  
  try {
    if (item.type === 'batch') {
      await runBatchAction({
        execute: (itemId) => {
          const { type, id } = parseSelectionKey(itemId)
          return apiMethods.post(
            `/api/pdf/review/reject/`,
            { type, id, notes: rejectReason.value.trim() }
          )
        },
        afterSuccess: loadData
      })
      showSuccess(`已拒绝 ${item.count} 个条目`)
    } else {
      // Single-item rejection
      const response = await apiMethods.post(
        `/api/pdf/review/reject/`,
        {
          type: item.type,
          id: item.id,
          notes: rejectReason.value.trim()
        }
      )

      ensureApiSuccess(response, '拒绝失败')
      showSuccess('拒绝成功')
    }
    
    closeRejectDialog()
    closeDetailDialog()
    if (item.type !== 'batch') {
      clearSelection()
      loadData()
    }
  } catch (error) {
    console.error('Rejection error:', error)
    showError(error, '拒绝失败')
  }
}

const viewItem = (item) => {
  selectedItem.value = item
  showDetailDialog.value = true
}

const closeDetailDialog = () => {
  showDetailDialog.value = false
  selectedItem.value = null
}

const toggleSelectAll = (checked) => updateSelection(checked)

const handleSearch = () => {
  // Search is handled by displayItems.
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('en-US')
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.unified-review {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
}

.unified-review-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
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

.type-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  border-bottom: 2px solid #e2e8f0;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  color: #64748b;
  transition: all 0.2s;
  position: relative;
  bottom: -2px;
}

.tab-button:hover {
  color: #3fbbc0;
}

.tab-button.active {
  color: #3fbbc0;
  border-bottom-color: #3fbbc0;
}

.badge {
  background: #3fbbc0;
  color: white;
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 600;
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

.search-box i {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
}

.table-container {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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

.review-table {
  width: 100%;
  border-collapse: collapse;
}

.review-table th,
.review-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e9ecef;
}

.review-table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #495057;
}

.review-table tr:hover {
  background: #f8f9fa;
}

.review-table tr.selected {
  background: #e3f2fd;
}

.type-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.type-badge.pdf {
  background: #dc3545;
  color: white;
}

.type-badge.meteorite {
  background: #28a745;
  color: white;
}

.classification-badge {
  background: #fff3e0;
  color: #f57c00;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
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

.btn-icon {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-view {
  background: #e3f2fd;
  color: #1976d2;
}

.btn-approve {
  background: #e8f5e9;
  color: #2e7d32;
}

.btn-reject {
  background: #ffebee;
  color: #d32f2f;
}

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

/* Reject dialog styles */
.reject-dialog {
  max-width: 500px;
}

.reject-warning {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 20px;
}

.reject-warning p {
  margin: 0 0 12px 0;
  color: #856404;
  font-weight: 500;
}

.reject-item-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.reject-item-info strong {
  color: #1a1a1a;
  font-size: 15px;
  flex: 1;
}

.item-type {
  background: #ffc107;
  color: #856404;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.reject-reason-section {
  margin-top: 20px;
}

.reject-reason-section label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #495057;
  margin-bottom: 8px;
  font-size: 14px;
}

.required {
  color: #dc3545;
}

.reject-reason-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ced4da;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.reject-reason-input:focus {
  outline: none;
  border-color: #3fbbc0;
  box-shadow: 0 0 0 3px rgba(63, 187, 192, 0.1);
}

.char-count {
  text-align: right;
  font-size: 12px;
  color: #6c757d;
  margin-top: 4px;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #6c757d;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #f0f0f0;
  color: #495057;
}

.modal-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  color: #1a1a1a;
}

.modal-header h3 i {
  color: #ffc107;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOut {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}
</style>

