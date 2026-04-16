<template>
  <div class="meteorite-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>陨石数据管理</h1>
      <p class="page-description">管理已审核通过的陨石数据</p>
    </div>

    <!-- 操作工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn btn-primary" @click="showCreateDialog = true">
          <i class="icon-plus"></i>
          添加陨石
        </button>
        <button class="btn btn-secondary" @click="refreshData">
          <i class="icon-refresh"></i>
          刷新
        </button>
        <button 
          class="btn btn-danger" 
          @click="batchDelete"
          :disabled="selectedItems.length === 0"
        >
          <i class="icon-delete"></i>
          批量删除 ({{ selectedItems.length }})
        </button>
        <button class="btn btn-warning" @click="navigateToPendingReview">
          <i class="icon-pending"></i>
          待审核管理
        </button>
        <button class="btn btn-outline" @click="navigateToRecycleBin">
          <i class="icon-trash"></i>
          回收站
        </button>
        <div class="search-box">
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="搜索陨石名称、分类或发现地点..."
            @input="handleSearch"
          />
          <i class="icon-search"></i>
        </div>
        <button class="btn btn-outline" @click="showFilters = !showFilters">
          <i class="icon-filter"></i>
          筛选
        </button>
      </div>
    </div>

    <!-- 筛选面板 -->
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

    <!-- 数据表格 -->
    <div class="table-container">
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>加载中...</p>
      </div>
      
      <div v-else-if="meteorites.length === 0" class="empty-state">
        <div class="empty-icon">📡</div>
        <h3>暂无陨石数据</h3>
        <p>点击"添加陨石"按钮开始添加数据</p>
      </div>

      <table v-else class="meteorite-table">
        <thead>
          <tr>
            <th class="checkbox-col">
              <input 
                type="checkbox" 
                :checked="isAllSelected"
                @change="toggleSelectAll"
              />
            </th>
            <th @click="sortBy('name')" class="sortable">
              名称
              <i :class="getSortIcon('name')"></i>
            </th>
            <th @click="sortBy('classification')" class="sortable">
              分类
              <i :class="getSortIcon('classification')"></i>
            </th>
            <th>发现地点</th>
            <th>来源</th>
            <th @click="sortBy('confidence_score')" class="sortable">
              置信度
              <i :class="getSortIcon('confidence_score')"></i>
            </th>
            <th @click="sortBy('created_at')" class="sortable">
              创建时间
              <i :class="getSortIcon('created_at')"></i>
            </th>
            <th class="actions-col">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="meteorite in meteorites" 
            :key="meteorite.id"
            :class="{ 'selected': selectedItems.includes(meteorite.id) }"
          >
            <td class="checkbox-col">
              <input 
                type="checkbox" 
                :value="meteorite.id"
                v-model="selectedItems"
              />
            </td>
            <td class="name-col">
              <div class="name-info">
                <strong>{{ meteorite.name }}</strong>
                <div v-if="meteorite.organic_compound_names" class="organic-compounds">
                  <span class="compound-tag" v-for="compound in meteorite.organic_compound_names.slice(0, 2)" :key="compound">
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
                  <div 
                    class="score-fill" 
                    :style="{ width: (meteorite.confidence_score * 100) + '%' }"
                  ></div>
                </div>
                <span class="score-text">{{ (meteorite.confidence_score * 100).toFixed(1) }}%</span>
              </div>
            </td>
            <td>{{ formatDate(meteorite.created_at) }}</td>
            <td class="actions-col">
              <div class="action-buttons">
                <button 
                  class="btn-icon btn-view" 
                  @click="viewMeteorite(meteorite)"
                  title="查看详情"
                >
                  <i class="icon-eye"></i>
                </button>
                <button 
                  class="btn-icon btn-edit" 
                  @click="editMeteorite(meteorite)"
                  title="编辑"
                >
                  <i class="icon-edit"></i>
                </button>
                
                <button 
                  class="btn-icon btn-delete" 
                  @click="deleteMeteorite(meteorite)"
                  title="删除"
                >
                  <i class="icon-delete"></i>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination">
      <button 
        class="btn btn-outline" 
        @click="goToPage(currentPage - 1)"
        :disabled="currentPage === 1"
      >
        上一页
      </button>
      <div class="page-numbers">
        <button 
          v-for="page in visiblePages" 
          :key="page"
          class="btn page-btn"
          :class="{ 'active': page === currentPage }"
          @click="goToPage(page)"
        >
          {{ page }}
        </button>
      </div>
      <button 
        class="btn btn-outline" 
        @click="goToPage(currentPage + 1)"
        :disabled="currentPage === totalPages"
      >
        下一页
      </button>
      <div class="page-info">
        共 {{ totalCount }} 条记录，第 {{ currentPage }} / {{ totalPages }} 页
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <div v-if="showCreateDialog || showEditDialog" class="modal-overlay" @click="closeDialogs">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ showCreateDialog ? '添加陨石' : '编辑陨石' }}</h3>
          <button class="btn-close" @click="closeDialogs">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveMeteorite">
            <div class="form-row">
              <div class="form-group">
                <label>名称 *</label>
                <input 
                  type="text" 
                  v-model="formData.name" 
                  required
                  placeholder="输入陨石名称"
                />
              </div>
              <div class="form-group">
                <label>分类 *</label>
                <input 
                  type="text" 
                  v-model="formData.classification" 
                  required
                  placeholder="输入陨石分类"
                />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>发现地点</label>
                <input 
                  type="text" 
                  v-model="formData.discovery_location" 
                  placeholder="输入发现地点"
                />
              </div>
              <div class="form-group">
                <label>来源</label>
                <input 
                  type="text" 
                  v-model="formData.origin" 
                  placeholder="输入来源信息"
                />
              </div>
            </div>
            <div class="form-group">
              <label>有机化合物</label>
              <textarea 
                v-model="formData.organic_compounds" 
                placeholder="输入有机化合物名称，多个用逗号分隔"
                rows="3"
              ></textarea>
            </div>
            <div class="form-group">
              <label>污染排除方法</label>
              <textarea 
                v-model="formData.contamination_exclusion_method" 
                placeholder="输入污染排除方法"
                rows="3"
              ></textarea>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>置信度分数</label>
                <input 
                  type="number" 
                  v-model="formData.confidence_score" 
                  min="0" 
                  max="1" 
                  step="0.01"
                  placeholder="0.0 - 1.0"
                />
              </div>
              <div class="form-group">
                <label>数据来源</label>
                <input 
                  type="text" 
                  v-model="formData.data_source" 
                  placeholder="输入数据来源"
                />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>参考文献</label>
                <textarea 
                  v-model="formData.references" 
                  placeholder="输入参考文献"
                  rows="2"
                ></textarea>
              </div>
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="closeDialogs">取消</button>
          <button class="btn btn-primary" @click="saveMeteorite" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 查看详情对话框 -->
    <div v-if="showViewDialog" class="modal-overlay" @click="showViewDialog = false">
      <div class="modal-content modal-large" @click.stop>
        <div class="modal-header">
          <h3>陨石详情</h3>
          <button class="btn-close" @click="showViewDialog = false">×</button>
        </div>
        <div class="modal-body">
          <div v-if="selectedMeteorite" class="detail-content">
            <div class="detail-section">
              <h4>基本信息</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>名称</label>
                  <span>{{ selectedMeteorite.name }}</span>
                </div>
                <div class="detail-item">
                  <label>分类</label>
                  <span class="classification-badge">{{ selectedMeteorite.classification }}</span>
                </div>
                <div class="detail-item">
                  <label>发现地点</label>
                  <span>{{ selectedMeteorite.discovery_location || '-' }}</span>
                </div>
                <div class="detail-item">
                  <label>来源</label>
                  <span>{{ selectedMeteorite.origin || '-' }}</span>
                </div>
                <div class="detail-item">
                  <label>置信度分数</label>
                  <div class="confidence-score">
                    <div class="score-bar">
                      <div 
                        class="score-fill" 
                        :style="{ width: (selectedMeteorite.confidence_score * 100) + '%' }"
                      ></div>
                    </div>
                    <span class="score-text">{{ (selectedMeteorite.confidence_score * 100).toFixed(1) }}%</span>
                  </div>
                </div>
                <div class="detail-item">
                  <label>审核状态</label>
                  <span :class="'status-badge status-' + selectedMeteorite.review_status">
                    {{ getStatusText(selectedMeteorite.review_status) }}
                  </span>
                </div>
              </div>
            </div>
            
            <div v-if="selectedMeteorite.organic_compound_names && selectedMeteorite.organic_compound_names.length > 0" class="detail-section">
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
            
            <div v-if="selectedMeteorite.contamination_exclusion_method" class="detail-section">
              <h4>污染排除方法</h4>
              <p class="detail-text">{{ selectedMeteorite.contamination_exclusion_method }}</p>
            </div>
            
            <div v-if="selectedMeteorite.references" class="detail-section">
              <h4>参考文献</h4>
              <p class="detail-text">{{ selectedMeteorite.references }}</p>
            </div>
            
            <div class="detail-section">
              <h4>系统信息</h4>
              <div class="detail-grid">
                <div class="detail-item">
                  <label>数据来源</label>
                  <span>{{ selectedMeteorite.data_source || '-' }}</span>
                </div>
                <div class="detail-item">
                  <label>创建时间</label>
                  <span>{{ formatDate(selectedMeteorite.created_at) }}</span>
                </div>
                <div class="detail-item">
                  <label>更新时间</label>
                  <span>{{ formatDate(selectedMeteorite.updated_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="showViewDialog = false">关闭</button>
          <button class="btn btn-primary" @click="editMeteorite(selectedMeteorite)">编辑</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PDFService from '@/services/pdfService.js'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess, getApiMessage } from '@/utils/apiResponse'

export default {
  name: 'MeteoriteManagement',
  setup() {
    // 响应式数据
    const loading = ref(false)
    const saving = ref(false)
    const meteorites = ref([])
    const selectedItems = ref([])
    const searchQuery = ref('')
    const showFilters = ref(false)
    const showCreateDialog = ref(false)
    const showEditDialog = ref(false)
    const showViewDialog = ref(false)
    const selectedMeteorite = ref(null)
    
    // 分页数据
    const currentPage = ref(1)
    const pageSize = ref(20)
    const totalCount = ref(0)
    const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))
    
    // 排序数据
    const sortField = ref('created_at')
    const sortOrder = ref('desc')
    
    // 筛选数据
    const filters = reactive({
      classification: '',
      origin: '',
      review_status: '',
      confidence_min: '',
      confidence_max: ''
    })
    
    // 选项数据
    const classificationOptions = ref([])
    const originOptions = ref([])
    
    // 表单数据
    const formData = reactive({
      name: '',
      classification: '',
      discovery_location: '',
      origin: '',
      organic_compounds: '',
      contamination_exclusion_method: '',
      confidence_score: 0.5,
      data_source: '',
      references: ''
    })
    
    // 计算属性
    const isAllSelected = computed(() => {
      return meteorites.value.length > 0 && selectedItems.value.length === meteorites.value.length
    })
    
    const visiblePages = computed(() => {
      const pages = []
      const start = Math.max(1, currentPage.value - 2)
      const end = Math.min(totalPages.value, currentPage.value + 2)
      
      for (let i = start; i <= end; i++) {
        pages.push(i)
      }
      return pages
    })
    
    // 方法
    const buildQueryParams = (overrides = {}) => {
      const params = {
        page: currentPage.value,
        page_size: pageSize.value,
        ordering: sortOrder.value === 'desc' ? `-${sortField.value}` : sortField.value
      }

      if (searchQuery.value) {
        params.search = searchQuery.value
      }

      Object.keys(filters).forEach(key => {
        if (filters[key] && key !== 'review_status') {
          params[key] = filters[key]
        }
      })

      return {
        ...params,
        ...overrides
      }
    }

    const loadMeteorites = async (overrides = {}) => {
      loading.value = true
      try {
        const params = buildQueryParams(overrides)
        const data = await PDFService.getApprovedMeteorites(params, { cache: false })
        
        meteorites.value = data?.results || []
        totalCount.value = data?.count || 0
      } catch (error) {
        console.error('加载陨石数据失败:', error)
        ElMessage.error(getApiErrorMessage(error, '加载数据失败'))
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
        console.error('加载选项数据失败:', error)
      }
    }
    
    const refreshData = () => {
      loadMeteorites()
      loadOptions()
    }
    
    const handleSearch = () => {
      currentPage.value = 1
      loadMeteorites()
    }
    
    const sortBy = (field) => {
      if (sortField.value === field) {
        sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
      } else {
        sortField.value = field
        sortOrder.value = 'asc'
      }
      loadMeteorites()
    }
    
    const getSortIcon = (field) => {
      if (sortField.value !== field) return 'icon-sort'
      return sortOrder.value === 'asc' ? 'icon-sort-up' : 'icon-sort-down'
    }
    
    const toggleSelectAll = () => {
      if (isAllSelected.value) {
        selectedItems.value = []
      } else {
        selectedItems.value = meteorites.value.map(m => m.id)
      }
    }
    
    const applyFilters = () => {
      currentPage.value = 1
      loadMeteorites()
    }
    
    const clearFilters = () => {
      Object.keys(filters).forEach(key => {
        filters[key] = ''
      })
      applyFilters()
    }
    
    const goToPage = (page) => {
      if (page >= 1 && page <= totalPages.value) {
        currentPage.value = page
        loadMeteorites()
      }
    }
    
    const viewMeteorite = (meteorite) => {
      selectedMeteorite.value = meteorite
      showViewDialog.value = true
    }
    
    const editMeteorite = (meteorite) => {
      selectedMeteorite.value = meteorite
      Object.keys(formData).forEach(key => {
        if (key === 'organic_compounds') {
          formData[key] = meteorite.organic_compound_names ? meteorite.organic_compound_names.join(', ') : ''
        } else {
          formData[key] = meteorite[key] || ''
        }
      })
      showViewDialog.value = false
      showEditDialog.value = true
    }
    
    const deleteMeteorite = async (meteorite) => {
      try {
        await ElMessageBox.confirm(`确定要删除陨石“${meteorite.name}”吗？`, '删除记录', {
          type: 'warning'
        })
        const payload = ensureApiSuccess(await PDFService.deleteApprovedMeteorite(meteorite.id), '删除失败')
        meteorites.value = meteorites.value.filter(item => item.id !== meteorite.id)
        totalCount.value = Math.max(totalCount.value - 1, 0)
        if (meteorites.value.length === 0 && currentPage.value > 1) {
          currentPage.value -= 1
        }
        ElMessage.success(getApiMessage(payload, '删除成功'))
        await loadMeteorites()
      } catch (error) {
        if (error === 'cancel') return
        console.error('删除陨石失败:', error)
        ElMessage.error(getApiErrorMessage(error, '删除失败'))
      }
    }
    
    const batchDelete = async () => {
      if (selectedItems.value.length === 0) return

      try {
        await ElMessageBox.confirm(`确定要删除选中的 ${selectedItems.value.length} 个陨石吗？`, '批量删除', {
          type: 'warning'
        })
        await Promise.all(
          selectedItems.value.map(async (id) =>
            ensureApiSuccess(await PDFService.deleteApprovedMeteorite(id), '批量删除失败')
          )
        )
        selectedItems.value = []
        ElMessage.success('批量删除成功')
        await loadMeteorites()
      } catch (error) {
        if (error === 'cancel') return
        console.error('批量删除失败:', error)
        ElMessage.error(getApiErrorMessage(error, '批量删除失败'))
      }
    }
    
    const quickChangeStatus = async (meteorite, newStatus) => {
      try {
        let response;
        
        if (newStatus === 'approved') {
          // 批准：使用新的API将数据从待审核移到已批准
          response = await PDFService.approveMeteorite(meteorite.id, {
            notes: `通过快捷审核按钮批准 - ${new Date().toLocaleString()}`
          })
        } else if (newStatus === 'rejected') {
          // 拒绝：使用新的API将数据从待审核移到回收站
          response = await PDFService.rejectMeteorite(meteorite.id, {
            rejection_reason: 'data_quality',
            notes: `通过快捷审核按钮拒绝 - ${new Date().toLocaleString()}`
          })
        } else {
          // 对于其他状态变更，暂时保持原有逻辑
          response = await PDFService.updateMeteorite(meteorite.id, {
            review_status: newStatus
          })
        }

        const payload = ensureApiSuccess(response, '修改审核状态失败')
        await loadMeteorites()

        const actionText = newStatus === 'approved' ? '批准' :
          newStatus === 'rejected' ? '拒绝' : '更新状态'
        ElMessage.success(getApiMessage(payload, `${actionText}成功`))
      } catch (error) {
        console.error('修改审核状态失败:', error)
        ElMessage.error(getApiErrorMessage(error, '修改审核状态失败'))
      }
    }
    
    const saveMeteorite = async () => {
      saving.value = true
      try {
        const data = { ...formData }
        if (data.organic_compounds) {
          data.organic_compounds = data.organic_compounds.split(',').map(s => s.trim()).filter(s => s)
        }
        
        const isEditing = showEditDialog.value
        let response
        if (showEditDialog.value) {
          response = await PDFService.updateApprovedMeteorite(selectedMeteorite.value.id, data)
        } else {
          response = await PDFService.createMeteorite(data)
        }

        const payload = ensureApiSuccess(response, '保存失败')
        const savedName = payload?.name || data.name
        closeDialogs()
        ElMessage.success(getApiMessage(payload, '保存成功'))
        currentPage.value = 1
        if (!isEditing && savedName) {
          searchQuery.value = savedName
          await loadMeteorites({ page: 1, search: savedName })
        } else {
          await loadMeteorites({ page: 1 })
        }
      } catch (error) {
        console.error('保存陨石失败:', error)
        ElMessage.error(getApiErrorMessage(error, '保存失败'))
      } finally {
        saving.value = false
      }
    }
    
    const closeDialogs = () => {
      showCreateDialog.value = false
      showEditDialog.value = false
      showViewDialog.value = false
      selectedMeteorite.value = null
      
      // 重置表单
      Object.keys(formData).forEach(key => {
        if (key === 'confidence_score') {
          formData[key] = 0.5
        } else {
          formData[key] = ''
        }
      })
    }
    
    const getStatusText = (status) => {
      const statusMap = {
        'pending': '待审核',
        'approved': '已通过',
        'rejected': '已拒绝'
      }
      return statusMap[status] || status
    }
    
    const formatDate = (dateString) => {
      if (!dateString) return '-'
      return new Date(dateString).toLocaleString('zh-CN')
    }
    
    const navigateToRecycleBin = () => {
      // 触发导航事件到回收站页面
      window.dispatchEvent(new CustomEvent('navigate-to-pdf', {
        detail: { page: 'recycle-bin' }
      }))
    }
    
    const navigateToPendingReview = () => {
      // 触发导航事件到统一审核页面
      window.dispatchEvent(new CustomEvent('navigate-to-pdf', {
        detail: { page: '/admin/unified-review' }
      }))
    }
    
    // 生命周期
    onMounted(() => {
      loadMeteorites()
      loadOptions()
    })
    
    // 监听搜索查询变化
    watch(searchQuery, () => {
      if (searchQuery.value === '') {
        handleSearch()
      }
    })
    
    return {
      // 响应式数据
      loading,
      saving,
      meteorites,
      selectedItems,
      searchQuery,
      showFilters,
      showCreateDialog,
      showEditDialog,
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
      formData,
      
      // 计算属性
      isAllSelected,
      visiblePages,
      
      // 方法
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
      editMeteorite,
      deleteMeteorite,
      batchDelete,
      quickChangeStatus,
      saveMeteorite,
      closeDialogs,
      getStatusText,
      formatDate,
      navigateToRecycleBin,
      navigateToPendingReview
    }
  }
}
</script>

<style scoped>
.meteorite-management {
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
  padding: 6px 8px;
  border: 1px solid #ddd;
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
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.table-container {
  background: white;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  overflow: hidden;
  margin-bottom: 24px;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #666;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
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

.meteorite-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.meteorite-table th.sortable:hover {
  background: #e9ecef;
}

.meteorite-table tr:hover {
  background: #f8f9fa;
}

.meteorite-table tr.selected {
  background: #e3f2fd;
}

.checkbox-col {
  width: 40px;
}

.actions-col {
  width: 120px;
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
  background: #fff3cd;
  color: #856404;
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
  height: 6px;
  background: #e9ecef;
  border-radius: 3px;
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

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-pending {
  background: #fff3cd;
  color: #856404;
}

.status-approved {
  background: #d4edda;
  color: #155724;
}

.status-rejected {
  background: #f8d7da;
  color: #721c24;
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

.btn-edit {
  background: #fff3e0;
  color: #f57c00;
}

.btn-edit:hover {
  background: #ffe0b2;
}

.btn-delete {
  background: #ffebee;
  color: #d32f2f;
}

.btn-delete:hover {
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

/* 按钮样式 */
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

/* 模态框样式 */
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
  max-width: 600px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-large {
  max-width: 800px;
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  color: #666;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #e9ecef;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 表单样式 */
.form-row {
  display: flex;
  gap: 16px;
}

.form-group {
  flex: 1;
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
  color: #495057;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

/* 详情页面样式 */
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

/* 图标样式 */
.icon-plus::before { content: '+'; }
.icon-refresh::before { content: '↻'; }
.icon-delete::before { content: '🗑'; }
.icon-trash::before { content: '🗂'; }
.icon-search::before { content: '🔍'; }
.icon-filter::before { content: '⚙'; }
.icon-eye::before { content: '👁'; }
.icon-edit::before { content: '✏'; }
.icon-check::before { content: '✓'; }
.icon-close::before { content: '✕'; }
.icon-clock::before { content: '⏰'; }
.icon-sort::before { content: '↕'; }
.icon-sort-up::before { content: '↑'; }
.icon-sort-down::before { content: '↓'; }

/* 快捷审核状态按钮样式 */
.status-quick-actions {
  display: inline-flex;
  gap: 4px;
  margin: 0 4px;
}

.btn-approve {
  background-color: #28a745;
  color: white;
}

.btn-approve:hover {
  background-color: #218838;
}

.btn-reject {
  background-color: #dc3545;
  color: white;
}

.btn-reject:hover {
  background-color: #c82333;
}

.btn-pending {
  background-color: #ffc107;
  color: #212529;
}

.btn-pending:hover {
  background-color: #e0a800;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .meteorite-management {
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
  
  .form-row {
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
