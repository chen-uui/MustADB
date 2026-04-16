<template>
  <div class="direct-processing-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>直接文档处理</h1>
      <p class="page-description">
        上传PDF文档，使用AI直接分析整篇论文，提取陨石数据、有机化合物信息和科学洞察
      </p>
      
      <!-- 功能说明卡片 -->
      <div class="feature-comparison-card">
        <div class="comparison-header">
          <i class="bi bi-info-circle"></i>
          <span>功能说明：直接处理 vs 数据提取</span>
        </div>
        <div class="comparison-content">
          <div class="feature-item">
            <div class="feature-title">
              <i class="bi bi-lightning-charge"></i>
              <strong>直接处理（当前功能）</strong>
            </div>
            <ul class="feature-list">
              <li>AI自动分析整篇文档，无需关键词</li>
              <li>适合探索性分析，发现未知信息</li>
              <li>提取陨石数据、有机化合物、矿物关系等</li>
              <li>提供科学洞察和综合分析</li>
            </ul>
          </div>
          <div class="feature-item">
            <div class="feature-title">
              <i class="bi bi-search"></i>
              <strong>数据提取</strong>
            </div>
            <ul class="feature-list">
              <li>基于关键词搜索相关片段</li>
              <li>精确提取特定信息</li>
              <li>适合已知要查找的内容</li>
              <li>可批量处理多个片段</li>
            </ul>
          </div>
        </div>
      </div>
    </div>

    <!-- 文档上传区域 -->
    <el-card class="upload-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📄 文档上传</span>
        </div>
      </template>
      
      <!-- 简化的文件上传区域 -->
      <div class="simple-upload-area">
        <input 
          ref="fileInput"
          type="file" 
          accept=".pdf" 
          @change="handleFileSelect"
          style="display: none;"
        />
        
        <div 
          class="upload-zone"
          @click="triggerFileSelect"
          @dragover.prevent
          @drop.prevent="handleFileDrop"
        >
          <el-icon class="upload-icon"><upload-filled /></el-icon>
          <div class="upload-text">
            将PDF文件拖到此处，或<em>点击选择文件</em>
          </div>
          <div class="upload-tip">
            支持PDF格式，单个文件不超过50MB
          </div>
        </div>
      </div>

      <!-- 已选择文件列表 -->
      <div v-if="fileList.length > 0" class="selected-files">
        <h4>已选择的文件 ({{ fileList.length }}个)：</h4>
        <ul class="file-list">
          <li v-for="(file, index) in fileList" :key="index" class="file-item">
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">({{ formatFileSize(file.size || file.raw?.size || 0) }})</span>
            <span class="file-status">{{ file.status || 'ready' }}</span>
            <el-button size="small" type="danger" @click="removeFile(index)">删除</el-button>
          </li>
        </ul>
      </div>

      <!-- 调试信息 -->
      <div v-if="fileList.length > 0" class="debug-info">
        <details>
          <summary>调试信息 (点击查看)</summary>
          <!-- 优化：只在开发环境显示调试信息，减少生产环境性能开销 -->
          <pre v-if="isDev">{{ JSON.stringify(fileList.map(f => ({ name: f.name, status: f.status, hasRaw: !!f.raw })), null, 2) }}</pre>
        </details>
      </div>

      <!-- 上传按钮 -->
      <div class="upload-actions">
        <el-button type="primary" @click="submitUpload" :loading="uploading">
          {{ uploading ? '上传中...' : '开始上传' }}
        </el-button>
        <el-button @click="clearFiles">清空文件</el-button>
      </div>
    </el-card>

    <!-- 处理选项 -->
    <el-card class="options-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>⚙️ 处理选项</span>
        </div>
      </template>
      
      <el-form :model="processingOptions" label-width="120px">
        <el-form-item label="分析重点">
          <el-radio-group v-model="processingOptions.focus">
            <el-radio label="comprehensive">综合分析</el-radio>
            <el-radio label="meteorite">陨石数据</el-radio>
            <el-radio label="organic">有机化合物</el-radio>
            <el-radio label="mineral">矿物关系</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="详细程度">
          <el-radio-group v-model="processingOptions.detail_level">
            <el-radio label="high">高</el-radio>
            <el-radio label="medium">中</el-radio>
            <el-radio label="low">低</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="输出语言">
          <el-radio-group v-model="processingOptions.language">
            <el-radio label="chinese">中文</el-radio>
            <el-radio label="english">English</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="置信度阈值">
          <el-slider
            v-model="processingOptions.confidence_threshold"
            :min="0.1"
            :max="1.0"
            :step="0.1"
            show-stops
            show-tooltip
          />
        </el-form-item>
        
        <el-form-item label="启用验证">
          <el-switch v-model="processingOptions.enable_validation" />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 处理进度 -->
    <el-card v-if="processingTasks.length > 0" class="progress-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📊 处理进度</span>
        </div>
      </template>
      
      <div v-for="task in processingTasks" :key="task.task_id" class="task-item">
        <div class="task-header">
          <span class="task-name">{{ task.document_name }}</span>
          <el-tag :type="getTaskStatusType(task.status)">
            {{ getTaskStatusText(task.status) }}
          </el-tag>
        </div>

        <TaskProgressBar
          :show="true"
          :title="'处理进度'"
          :percentage="task.progress || 0"
          :processed="undefined"
          :total="undefined"
          :successful="0"
          :failed="task.error_message ? 1 : 0"
          :status-text="getTaskStatusText(task.status)"
        />
        
        <el-progress
          :percentage="task.progress"
          :status="getProgressStatus(task.status)"
          :show-text="true"
        />
        
        <div v-if="task.current_step" class="task-step">
          当前步骤: {{ task.current_step }}
        </div>
        
        <div v-if="task.error_message" class="task-error">
          <el-alert
            :title="task.error_message"
            type="error"
            :closable="false"
          />
        </div>
      </div>
    </el-card>

    <!-- 处理结果 -->
    <el-card v-if="processingResults.length > 0" class="results-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📋 处理结果</span>
        </div>
      </template>
      
      <div v-for="result in processingResults" :key="result.id" :data-result-id="result.id" class="result-item">
        <div class="result-header">
          <h3>{{ result.document_title }}</h3>
          <div class="result-meta">
            <el-tag type="success">置信度: {{ (result.confidence_score * 100).toFixed(1) }}%</el-tag>
            <el-tag type="info">处理时间: {{ formatTime(result.processing_time) }}</el-tag>
          </div>
        </div>
        
        <el-tabs v-model="result.activeTab" class="result-tabs">
          <el-tab-pane label="陨石数据" name="meteorite">
            <div class="temp-display">
              <h4>陨石数据</h4>
              <pre>{{ JSON.stringify(result.meteorite_data, null, 2) }}</pre>
            </div>
          </el-tab-pane>
          <el-tab-pane label="有机化合物" name="organic">
            <div class="temp-display">
              <h4>有机化合物</h4>
              <pre>{{ JSON.stringify(result.organic_compounds, null, 2) }}</pre>
            </div>
          </el-tab-pane>
          <el-tab-pane label="矿物关系" name="mineral">
            <div class="temp-display">
              <h4>矿物关系</h4>
              <pre>{{ JSON.stringify(result.mineral_relationships, null, 2) }}</pre>
            </div>
          </el-tab-pane>
          <el-tab-pane label="科学洞察" name="insights">
            <div class="temp-display">
              <h4>科学洞察</h4>
              <pre>{{ JSON.stringify(result.scientific_insights, null, 2) }}</pre>
            </div>
          </el-tab-pane>
          <el-tab-pane label="验证结果" name="validation">
            <div class="temp-display">
              <h4>验证结果</h4>
              <pre>{{ JSON.stringify(result.validation_checks, null, 2) }}</pre>
            </div>
          </el-tab-pane>
        </el-tabs>
        
        <div class="result-actions">
          <el-button type="primary" @click="exportResult(result)">
            导出结果
          </el-button>
          <el-button @click="viewDetails(result)">
            查看详情
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 处理历史 -->
    <el-card class="history-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📚 处理历史</span>
        </div>
      </template>
      
      <el-table :data="processingHistory" style="width: 100%">
        <el-table-column prop="document_title" label="文档标题" width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getTaskStatusType(scope.row.status)">
              {{ getTaskStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence_score" label="置信度" width="100">
          <template #default="scope">
            {{ (scope.row.confidence_score * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="processing_time" label="处理时间" width="120">
          <template #default="scope">
            {{ formatTime(scope.row.processing_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button size="small" @click="viewHistoryResult(scope.row)">
              查看
            </el-button>
            <el-button size="small" type="danger" @click="deleteHistoryResult(scope.row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { useNotification } from '@/composables/useNotification'
import { API_CONFIG } from '@/config/api'
import { apiMethods } from '@/utils/apiClient'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess, getApiMessage } from '@/utils/apiResponse'
import TaskProgressBar from '@/components/common/TaskProgressBar.vue'
// import MeteoriteDataDisplay from '@/components/MeteoriteDataDisplay.vue'
// import OrganicCompoundsDisplay from '@/components/OrganicCompoundsDisplay.vue'
// import MineralRelationshipsDisplay from '@/components/MineralRelationshipsDisplay.vue'
// import ScientificInsightsDisplay from '@/components/ScientificInsightsDisplay.vue'
// import ValidationResultsDisplay from '@/components/ValidationResultsDisplay.vue'

// 响应式数据
const fileInput = ref()
const fileList = ref([])
const uploading = ref(false)
const processingTasks = ref([])
const processingResults = ref([])
const processingHistory = ref([])

// 处理选项
const processingOptions = reactive({
  focus: 'comprehensive',
  detail_level: 'high',
  language: 'chinese',
  confidence_threshold: 0.6,
  enable_validation: true
})

// 上传配置
const uploadUrl = ref(API_CONFIG.ENDPOINTS.DIRECT_PROCESS)
const uploadHeaders = ref({
  'Authorization': `Bearer ${localStorage.getItem('token')}`
})
const uploadData = ref({})

// 开发环境判断
const isDev = computed(() => {
  // 在客户端环境中判断是否为开发环境
  return import.meta.env && import.meta.env.DEV
})

// 通知系统
const { showSuccess, showError, showWarning, showInfo } = useNotification()
const notifySuccess = (message, options = {}) => {
  showSuccess(message, options)
  ElMessage.success(message)
}
const normalizeDirectProcessingErrorMessage = (message, fallbackTitle) => {
  if (!message) {
    return fallbackTitle
  }
  if (/Invalid PDF file|Only PDF files are allowed/i.test(message)) {
    return 'PDF 文件无效、已损坏或格式不受支持'
  }
  if (/No file uploaded/i.test(message)) {
    return '未选择要上传的 PDF 文件'
  }
  if (/Method not allowed/i.test(message)) {
    return '请求方法不支持，请稍后重试'
  }
  return message
}
const notifyError = (error, fallbackTitle = '操作失败') => {
  const message = normalizeDirectProcessingErrorMessage(
    getApiErrorMessage(error, fallbackTitle),
    fallbackTitle
  )
  showError(error, { title: fallbackTitle })
  ElMessage.error(message)
  return message
}

// 生命周期
onMounted(() => {
  console.log('DirectProcessing组件已挂载')
  loadProcessingHistory()
  // 不再自动启动轮询，只有在有进行中的任务时才启动
  // startProgressPolling()
  console.log('组件已挂载，当前任务数:', processingTasks.value.length)
})

onUnmounted(() => {
  stopProgressPolling()
})

// 上传前检查
const beforeUpload = (file) => {
  const isPDF = file.type === 'application/pdf'
  const isLt50M = file.size / 1024 / 1024 < 50

  if (!isPDF) {
    ElMessage.error('只能上传PDF格式的文件!')
    return false
  }
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过50MB!')
    return false
  }
  return true
}

// 提交上传
const submitUpload = async () => {
  console.log('Current fileList:', fileList.value)
  console.log('fileList length:', fileList.value?.length)
  
  if (!fileList.value || fileList.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件!')
    return
  }

  const file = fileList.value[0]
  console.log('File to upload:', file)
  
  if (!file.raw || !(file.raw instanceof File)) {
    ElMessage.warning('没有找到有效的文件，请重新选择!')
    return
  }

  uploading.value = true
  
  try {
    // 创建FormData
    const formData = new FormData()
    formData.append('file', file.raw)
    formData.append('options', JSON.stringify(processingOptions))
    
    console.log('Starting upload...')
    
    // 发送上传请求
    const axiosResp = await apiMethods.upload(API_CONFIG.ENDPOINTS.DIRECT_PROCESS, formData)
    const result = ensureApiSuccess(axiosResp, '文件上传失败')
    console.log('Upload result:', result)
    
    // 处理上传结果
    handleUploadSuccess(result, file, fileList.value)
    
  } catch (error) {
    console.error('Upload error:', error)
    handleUploadError(error)
  } finally {
    uploading.value = false
  }
}

// 上传成功
const handleUploadSuccessLegacy = (response, file, fileList) => {
  uploading.value = false
  
  if (response.task_id) {
    // 单个文件处理
    processingTasks.value.push({
      task_id: response.task_id,
      document_name: file.name,
      status: 'processing',
      progress: 0,
      current_step: '开始处理...'
    })
    
    notifySuccess(response.message || '文件上传成功，开始处理')
  } else if (response.task_ids) {
    // 批量处理
    response.task_ids.forEach((taskId, index) => {
      processingTasks.value.push({
        task_id: taskId,
        document_name: fileList[index].name,
        status: 'processing',
        progress: 0,
        current_step: '开始处理...'
      })
    })
    
    notifySuccess(response.message || `批量上传成功，开始处理${response.task_ids.length}个文件`)
  } else {
    notifyError(createUnexpectedUploadError(response), '文件上传失败')
    return
  }
  
  // 启动轮询检查任务进度
  startProgressPolling()
  
  clearFiles()
}

// 上传失败
const handleUploadSuccess = (response, file, fileList) => {
  uploading.value = false

  if (response.task_id) {
    processingTasks.value.push({
      task_id: response.task_id,
      document_name: file.name,
      status: 'processing',
      progress: 0,
      current_step: '开始处理...'
    })

    notifySuccess('文件上传成功，开始处理')
  } else if (response.task_ids) {
    response.task_ids.forEach((taskId, index) => {
      processingTasks.value.push({
        task_id: taskId,
        document_name: fileList[index].name,
        status: 'processing',
        progress: 0,
        current_step: '开始处理...'
      })
    })

    notifySuccess(`批量上传成功，开始处理 ${response.task_ids.length} 个文件`)
  } else {
    notifyError(createUnexpectedUploadError(response), '文件上传失败')
    return
  }

  startProgressPolling()
  clearFiles()
}

const handleUploadError = (error) => {
  uploading.value = false
  notifyError(error, '文件上传失败')
  console.error('Upload error:', error)
}

const createUnexpectedUploadError = (payload) => {
  const error = new Error('文件上传失败')
  error.response = {
    status: 200,
    data: payload
  }
  return error
}

// 上传进度
const handleUploadProgress = (event, file, fileList) => {
  // 可以在这里显示上传进度
}

// 触发文件选择
const triggerFileSelect = () => {
  fileInput.value.click()
}

// 处理文件选择
const handleFileSelect = (event) => {
  const files = event.target.files
  if (files && files.length > 0) {
    const file = files[0]
    console.log('File selected:', file)
    
    // 验证文件
    if (!validateFile(file)) {
      return
    }
    
    // 添加到文件列表
    fileList.value = [{
      name: file.name,
      size: file.size,
      raw: file,
      status: 'ready'
    }]
    
    console.log('File added to list:', fileList.value)
  }
}

// 处理拖拽文件
const handleFileDrop = (event) => {
  const files = event.dataTransfer.files
  if (files && files.length > 0) {
    const file = files[0]
    console.log('File dropped:', file)
    
    // 验证文件
    if (!validateFile(file)) {
      return
    }
    
    // 添加到文件列表
    fileList.value = [{
      name: file.name,
      size: file.size,
      raw: file,
      status: 'ready'
    }]
    
    console.log('File added to list:', fileList.value)
  }
}

// 验证文件
const validateFile = (file) => {
  const isPDF = file.type === 'application/pdf'
  const isLt50M = file.size / 1024 / 1024 < 50

  if (!isPDF) {
    ElMessage.error('只能上传PDF格式的文件!')
    return false
  }

  if (!isLt50M) {
    ElMessage.error('文件大小不能超过50MB!')
    return false
  }

  return true
}

// 移除单个文件
const removeFile = (index) => {
  fileList.value.splice(index, 1)
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 清空文件
const clearFiles = () => {
  fileList.value = []
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

// 获取任务状态类型
const getTaskStatusType = (status) => {
  const statusMap = {
    'pending': 'info',
    'processing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

// 获取任务状态文本
const getTaskStatusText = (status) => {
  const statusMap = {
    'pending': '待处理',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '处理失败'
  }
  return statusMap[status] || '未知'
}

// 获取进度状态
const getProgressStatus = (status) => {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
}

// 格式化时间
const formatTime = (seconds) => {
  if (seconds < 60) return `${seconds.toFixed(1)}秒`
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}分钟`
  return `${(seconds / 3600).toFixed(1)}小时`
}

// 导出结果
const exportResult = (result) => {
  const dataStr = JSON.stringify(result, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${result.document_title}_result.json`
  link.click()
  URL.revokeObjectURL(url)
  
  showSuccess('结果已导出')
}

// 查看详情
const viewDetails = async (result) => {
    try {
      // 获取完整的结果详情
      const axiosResp = await apiMethods.get(API_CONFIG.ENDPOINTS.DIRECT_PROCESS_RESULT(result.id))
      const data = ensureApiSuccess(axiosResp, '获取结果详情失败')
      if (data) {
      // 设置默认活动标签
      data.activeTab = 'meteorite'
      // 将结果添加到显示列表中
      if (!processingResults.value.find(r => r.id === result.id)) {
        processingResults.value.unshift(data)
      }
      showSuccess(`查看结果: ${result.document_title}`)
      } else {
        showError('获取结果详情失败')
      }
    } catch (error) {
      console.error('Error loading result details:', error)
      showError(error, '获取结果详情失败')
    }
  }

// 查看历史结果
const viewHistoryResult = async (result) => {
    try {
      // 获取完整的结果详情
      const axiosResp = await apiMethods.get(API_CONFIG.ENDPOINTS.DIRECT_PROCESS_RESULT(result.id))
      const data = ensureApiSuccess(axiosResp, '获取结果详情失败')
      if (data) {
      // 设置默认活动标签
      data.activeTab = 'meteorite'
      // 将结果添加到显示列表中
      if (!processingResults.value.find(r => r.id === result.id)) {
        processingResults.value.unshift(data)
      }
      showSuccess(`查看历史结果: ${result.document_title}`)
      } else {
        showError('获取结果详情失败')
      }
    } catch (error) {
      console.error('Error loading result details:', error)
      showError(error, '获取结果详情失败')
    }
  }

// 删除历史结果
const deleteHistoryResult = (result) => {
  ElMessageBox.confirm(
    '确定要删除这个处理结果吗？',
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
      try {
        // 调用删除API
        const axiosResp = await apiMethods.delete(API_CONFIG.ENDPOINTS.DIRECT_PROCESS_DELETE(result.id))
        const payload = ensureApiSuccess(axiosResp, '删除失败')
        notifySuccess('删除成功，历史记录已更新')
        processingResults.value = processingResults.value.filter(item => item.id !== result.id)
        processedResults.delete(result.id)
        await loadProcessingHistory()
      } catch (error) {
        console.error('Delete error:', error)
        notifyError(error, '删除失败')
      }
    })
}

// 加载处理历史
const loadProcessingHistory = async () => {
  try {
    console.log('开始加载处理历史')
    const axiosResp = await apiMethods.get(API_CONFIG.ENDPOINTS.DIRECT_PROCESS_HISTORY)
    const data = ensureApiSuccess(axiosResp, '加载处理历史失败')
    processingHistory.value = Array.isArray(data.results) ? data.results : []
    console.log('处理历史加载完成，历史记录数:', processingHistory.value.length)

    // 检查是否有正在处理的任务需要恢复
    const pendingTasks = processingHistory.value.filter(task =>
      task.status === 'processing' || task.status === 'pending'
    )

    if (pendingTasks.length > 0) {
      console.log('发现正在处理的任务，恢复轮询:', pendingTasks.length)
      // 将正在处理的任务添加到当前任务列表
      pendingTasks.forEach(task => {
        if (!processingTasks.value.find(t => t.task_id === task.id)) {
          processingTasks.value.push({
            task_id: task.id,
            document_name: task.document_title,
            status: task.status,
            progress: 0,
            current_step: '恢复处理...'
          })
        }
      })
    }
  } catch (error) {
    console.error('Failed to load processing history:', error)
    // 兜底：避免UI因异常数据而崩溃
    if (!Array.isArray(processingHistory.value)) {
      processingHistory.value = []
    }
    ElMessage.error(getApiErrorMessage(error, '加载处理历史失败，请稍后重试'))
  }
}

// 进度轮询
// 优化：使用ref存储定时器ID，确保可以正确清理
const progressTimer = ref(null)

const startProgressPolling = () => {
  // 如果已经启动轮询，不重复启动
  if (progressTimer.value) {
    if (import.meta.env.DEV) {
      console.log('轮询已启动，只启动一次')
    }
    return
  }
  
  if (import.meta.env.DEV) {
    console.log('启动进度轮询')
  }
  progressTimer.value = setInterval(() => {
    updateTaskProgress()
  }, 2000)
}

const stopProgressPolling = () => {
  if (progressTimer.value) {
    clearInterval(progressTimer.value)
    progressTimer.value = null
  }
}

const updateTaskProgress = async () => {
  // 优化：移除生产环境的console.log，减少性能开销
  // 只在开发环境记录日志
  if (import.meta.env.DEV) {
    console.log('开始更新任务进度，当前任务数:', processingTasks.value.length)
  }
  
  // 检查是否有processing状态的任务
  const hasProcessingTasks = processingTasks.value.some(t => t.status === 'processing')
  
  if (!hasProcessingTasks) {
    console.log('没有进行中的任务，停止轮询')
    stopProgressPolling()
    return
  }
  
  for (const task of processingTasks.value) {
    console.log(`检查任务 ${task.task_id}，状态: ${task.status}`)
    if (task.status === 'processing') {
      try {
        console.log(`轮询任务 ${task.task_id} 状态`)
        const axiosResp = await apiMethods.get(API_CONFIG.ENDPOINTS.DIRECT_PROCESS_STATUS(task.task_id))
        const data = ensureApiSuccess(axiosResp, '获取处理进度失败')
        console.log(`任务 ${task.task_id} 状态更新:`, data)
        
        task.status = data.status
        task.progress = data.progress
        task.current_step = data.current_step
        task.error_message = data.error_message
        
        // 如果任务完成，获取结果
        if (data.status === 'completed' && data.result_id) {
          console.log(`任务 ${task.task_id} 完成，结果ID: ${data.result_id}`)
          notifySuccess(`文件 ${task.document_name} 处理完成`)
          // 自动弹出结果（内部会调用loadProcessingResult）
          await showProcessingResult(data.result_id)
          // 任务完成后停止轮询这个任务
          task.status = 'completed'
        } else if (data.status === 'failed') {
          console.log(`任务 ${task.task_id} 失败`)
          notifyError(
            createUnexpectedUploadError({
              message: `文件 ${task.document_name} 处理失败`,
              detail: data.error_message || data.detail || '',
              error: data.error_message || data.detail || ''
            }),
            `文件 ${task.document_name} 处理失败`
          )
          task.status = 'failed'
        }
      } catch (error) {
        console.error('Failed to update task progress:', error)
        notifyError(error, `获取任务 ${task.document_name} 进度失败`)
      }
    } else {
      console.log(`任务 ${task.task_id} 状态为 ${task.status}，跳过轮询`)
    }
  }
  
  // 再次检查是否还有processing状态的任务
  const stillHasProcessingTasks = processingTasks.value.some(t => t.status === 'processing')
  if (!stillHasProcessingTasks) {
    console.log('所有任务已完成，停止轮询')
    stopProgressPolling()
  }
}

const loadProcessingResult = async (resultId) => {
  try {
    console.log(`开始加载处理结果 ${resultId}`)
    const axiosResp = await apiMethods.get(API_CONFIG.ENDPOINTS.DIRECT_PROCESS_RESULT(resultId))
    const data = ensureApiSuccess(axiosResp, '加载处理结果失败')
    console.log(`结果数据加载成功:`, data)
    
    // 设置默认活动标签
    data.activeTab = 'meteorite'
    
    processingResults.value.unshift(data)
    console.log(`结果已添加到显示列表，当前结果数: ${processingResults.value.length}`)
    
    // 自动刷新处理历史
    loadProcessingHistory()
    
    return data
  } catch (error) {
    console.error('Failed to load processing result:', error)
    showError(error, '加载处理结果失败')
    return null
  }
}

// 防重复调用的结果ID集合
const processedResults = new Set()

// 自动弹出处理结果
const showProcessingResult = async (resultId) => {
  try {
    // 防止重复处理同一个结果
    if (processedResults.has(resultId)) {
      console.log(`结果 ${resultId} 已经处理过，跳过`)
      return
    }
    processedResults.add(resultId)
    
    console.log(`开始处理结果 ${resultId}`)
    const result = await loadProcessingResult(resultId)
    if (result) {
      console.log(`结果 ${resultId} 加载成功，开始滚动`)
      
      // 等待DOM更新，增加等待时间
      await new Promise(resolve => setTimeout(resolve, 500))
      
      // 滚动到结果区域
      const resultElement = document.querySelector('.results-card')
      if (resultElement) {
        console.log('找到结果区域元素，开始滚动')
        resultElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
        console.log('已滚动到结果区域')
        
        // 添加额外的滚动确保
        setTimeout(() => {
          resultElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
          console.log('二次滚动确保')
        }, 100)
        
        // 高亮显示新结果
        setTimeout(() => {
          const resultCard = document.querySelector(`[data-result-id="${resultId}"]`)
          if (resultCard) {
            resultCard.style.border = '2px solid #409EFF'
            resultCard.style.boxShadow = '0 4px 12px rgba(64, 158, 255, 0.3)'
            resultCard.style.transition = 'all 0.3s ease'
            console.log('已高亮显示结果')
            
            // 3秒后移除高亮
            setTimeout(() => {
              resultCard.style.border = ''
              resultCard.style.boxShadow = ''
            }, 3000)
          } else {
            console.log('未找到结果卡片元素，尝试其他选择器')
            // 尝试其他选择器
            const altResultCard = document.querySelector(`.result-item[data-result-id="${resultId}"]`)
            if (altResultCard) {
              altResultCard.style.border = '2px solid #409EFF'
              altResultCard.style.boxShadow = '0 4px 12px rgba(64, 158, 255, 0.3)'
              altResultCard.style.transition = 'all 0.3s ease'
              console.log('使用备用选择器找到结果卡片')
              
              setTimeout(() => {
                altResultCard.style.border = ''
                altResultCard.style.boxShadow = ''
              }, 3000)
            }
          }
        }, 300)
      } else {
        console.log('未找到结果区域元素，等待更长时间后重试')
        // 等待更长时间后重试
        setTimeout(async () => {
          const retryElement = document.querySelector('.results-card')
          if (retryElement) {
            retryElement.scrollIntoView({ behavior: 'smooth', block: 'start' })
            console.log('重试后找到结果区域元素')
          } else {
            console.log('重试后仍未找到结果区域元素')
          }
        }, 1000)
      }
    } else {
      console.log(`结果 ${resultId} 加载失败`)
    }
  } catch (error) {
    console.error('Failed to show processing result:', error)
    // 如果出错，从已处理集合中移除，允许重试
    processedResults.delete(resultId)
  }
}
</script>

<style scoped>
.direct-processing-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h1 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-description {
  color: #7f8c8d;
  font-size: 16px;
}

.upload-card,
.options-card,
.progress-card,
.results-card,
.history-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  font-weight: bold;
  color: #2c3e50;
}

.upload-dragger {
  width: 100%;
}

.upload-actions {
  margin-top: 20px;
  text-align: center;
}

.task-item {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.task-name {
  font-weight: bold;
  color: #2c3e50;
}

.task-step {
  margin-top: 10px;
  color: #7f8c8d;
  font-size: 14px;
}

.task-error {
  margin-top: 10px;
}

.result-item {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.result-header h3 {
  margin: 0;
  color: #2c3e50;
}

.result-meta {
  display: flex;
  gap: 10px;
}

.result-tabs {
  margin-bottom: 20px;
}

.result-actions {
  text-align: center;
}

.el-table {
  margin-top: 20px;
}

/* 简化的上传区域样式 */
.simple-upload-area {
  margin-bottom: 20px;
}

.upload-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  width: 100%;
  height: 180px;
  text-align: center;
  cursor: pointer;
  position: relative;
  background-color: #fafafa;
  transition: border-color 0.3s;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.upload-zone:hover {
  border-color: #409eff;
}

.upload-icon {
  font-size: 67px;
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text {
  color: #606266;
  font-size: 14px;
  text-align: center;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  color: #909399;
  font-size: 12px;
  text-align: center;
  margin-top: 7px;
}

/* 文件列表样式 */
.selected-files {
  margin-top: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.selected-files h4 {
  margin: 0 0 10px 0;
  color: #495057;
  font-size: 14px;
  font-weight: 600;
}

.file-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  margin-bottom: 8px;
  background-color: #ffffff;
  border: 1px solid #dee2e6;
  border-radius: 4px;
}

.file-item:last-child {
  margin-bottom: 0;
}

.file-name {
  font-weight: 500;
  color: #495057;
  flex: 1;
}

.file-size {
  color: #6c757d;
  font-size: 12px;
  margin-right: 10px;
}

.file-status {
  color: #28a745;
  font-size: 12px;
  margin-right: 10px;
  font-weight: 500;
}

/* 调试信息样式 */
.debug-info {
  margin-top: 15px;
  padding: 10px;
  background-color: #f1f3f4;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.debug-info summary {
  cursor: pointer;
  font-size: 12px;
  color: #666;
  margin-bottom: 10px;
}

.debug-info pre {
  background-color: #ffffff;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
  font-size: 11px;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}

.temp-display {
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.temp-display h4 {
  color: #495057;
  margin-bottom: 15px;
  font-weight: 600;
}

.temp-display pre {
  background-color: #ffffff;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 15px;
  font-size: 12px;
  line-height: 1.4;
  max-height: 400px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.feature-comparison-card {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;
  border-radius: 12px;
  padding: 20px;
  margin-top: 24px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
}

.comparison-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 1rem;
  font-weight: 600;
  color: #0369a1;
}

.comparison-header i {
  font-size: 1.25rem;
}

.comparison-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.feature-item {
  background: white;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e0f2fe;
}

.feature-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 0.9375rem;
  color: #0c4a6e;
}

.feature-title i {
  font-size: 1.125rem;
  color: #0284c7;
}

.feature-list {
  margin: 0;
  padding-left: 20px;
  list-style: none;
}

.feature-list li {
  position: relative;
  padding-left: 20px;
  margin-bottom: 8px;
  font-size: 0.875rem;
  color: #475569;
  line-height: 1.5;
}

.feature-list li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #0284c7;
  font-weight: bold;
}

@media (max-width: 768px) {
  .comparison-content {
    grid-template-columns: 1fr;
  }
}
</style>
