<template>
  <div class="min-h-screen pt-24 pb-12 px-4 md:px-8">
    <div class="container mx-auto max-w-7xl">
      <!-- Breadcrumb -->
      <nav class="flex items-center gap-2 text-sm text-white/50 mb-8 animate-fade-in-up">
        <a href="#" @click.prevent="goHome" class="hover:text-starlight-blue transition-colors">Home</a>
        <i class="bi bi-chevron-right text-xs"></i>
        <span class="text-white/80">Document Details</span>
      </nav>

      <!-- Header Section -->
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-12 animate-fade-in-up delay-100">
        <div>
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-glass-border mb-4">
            <i class="bi bi-file-earmark-pdf text-starlight-blue"></i>
            <span class="text-xs font-medium text-white/80">PDF Document</span>
          </div>
          <h1 class="text-3xl md:text-5xl font-bold text-white mb-2 tracking-tight">
            {{ document.title || 'Loading Document...' }}
          </h1>
          <p class="text-white/50 text-lg font-light">
            Uploaded on {{ formatDate(document.created_at) }}
          </p>
        </div>
        
        <AstroButton variant="secondary" @click="goBack">
          <i class="bi bi-arrow-left mr-2"></i>
          Back to List
        </AstroButton>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-fade-in-up delay-200">
        <!-- Sidebar -->
        <div class="lg:col-span-4 space-y-6">
          <!-- Info Card -->
          <AstroCard>
            <h3 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <i class="bi bi-info-circle text-starlight-blue"></i>
              Metadata
            </h3>
            
            <div class="space-y-4">
              <div class="flex justify-between items-center py-3 border-b border-white/5">
                <span class="text-white/50 text-sm">File Size</span>
                <span class="text-white font-mono">{{ formatFileSize(document.file_size) }}</span>
              </div>
              <div class="flex justify-between items-center py-3 border-b border-white/5">
                <span class="text-white/50 text-sm">Chunks</span>
                <span class="text-white font-mono">{{ chunks.length }}</span>
              </div>
              <div class="flex justify-between items-center py-3 border-b border-white/5">
                <span class="text-white/50 text-sm">Status</span>
                <span 
                  class="px-2 py-1 rounded text-xs font-bold uppercase tracking-wider"
                  :class="getStatusClass(document.status)"
                >
                  {{ document.status || 'Unknown' }}
                </span>
              </div>
            </div>
          </AstroCard>

          <!-- Actions Card -->
          <AstroCard>
            <h3 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
              <i class="bi bi-gear text-starlight-blue"></i>
              Actions
            </h3>
            
            <div class="space-y-3">
              <AstroButton variant="primary" block @click="downloadFile">
                <i class="bi bi-download mr-2"></i> Download PDF
              </AstroButton>
              <AstroButton variant="secondary" block @click="reprocessFile">
                <i class="bi bi-arrow-clockwise mr-2"></i> Reprocess
              </AstroButton>
              <AstroButton variant="danger" block @click="deleteFile" class="mt-4">
                <i class="bi bi-trash mr-2"></i> Delete Document
              </AstroButton>
            </div>
          </AstroCard>
        </div>

        <!-- Main Content -->
        <div class="lg:col-span-8 space-y-6">
          <!-- Search Bar -->
          <div class="relative group">
            <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <i class="bi bi-search text-white/30 group-focus-within:text-starlight-blue transition-colors"></i>
            </div>
            <input 
              type="text" 
              v-model="searchText"
              placeholder="Search within document content..." 
              class="w-full bg-white/5 border border-glass-border rounded-xl py-4 pl-12 pr-4 text-white placeholder-white/30 focus:outline-none focus:border-starlight-blue/50 focus:bg-white/10 transition-all"
            >
          </div>

          <!-- Content List -->
          <div class="space-y-4">
            <div v-if="chunks.length === 0" class="text-center py-20 opacity-50">
              <i class="bi bi-file-earmark-text text-4xl mb-4 block"></i>
              <p>No content chunks available yet.</p>
            </div>

            <AstroCard 
              v-for="(chunk, index) in filteredChunks" 
              :key="index"
              class="group hover:border-starlight-blue/30 transition-colors"
            >
              <div class="flex justify-between items-start mb-4">
                <span class="px-2 py-1 rounded bg-starlight-blue/10 text-starlight-blue text-xs font-mono">
                  Page {{ chunk.page_number }}
                </span>
                <button 
                  class="text-white/30 hover:text-starlight-blue transition-colors"
                  @click="searchSimilar(chunk.content)"
                  title="Find similar content"
                >
                  <i class="bi bi-search"></i>
                </button>
              </div>
              
              <div 
                class="text-white/80 leading-relaxed font-light"
                v-html="chunk.highlighted ? chunk.highlightedContent : chunk.content"
              ></div>
            </AstroCard>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import PDFService from '@/services/pdfService.js'
import AstroCard from '@/components/ui/AstroCard.vue'
import AstroButton from '@/components/ui/AstroButton.vue'
import { useNotification, useConfirm } from '@/components/base/useNotification.js'
import { getApiErrorMessage } from '@/utils/apiError'
import { ensureApiSuccess } from '@/utils/apiResponse'

const props = defineProps({
  documentId: {
    type: [String, Number],
    required: true
  }
})

const emit = defineEmits(['navigate'])

const document = ref({})
const chunks = ref([])
const searchText = ref('')
const loading = ref(false)
const { showSuccess, showError } = useNotification()
const { confirm } = useConfirm()
const normalizedDocumentId = computed(() => {
  if (props.documentId === null || props.documentId === undefined) {
    return ''
  }
  return String(props.documentId).trim()
})

// Formatters
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown Date'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const getStatusClass = (status) => {
  const map = {
    'completed': 'bg-green-500/20 text-green-400',
    'processing': 'bg-blue-500/20 text-blue-400',
    'failed': 'bg-red-500/20 text-red-400',
    'pending': 'bg-yellow-500/20 text-yellow-400'
  }
  return map[status] || 'bg-white/10 text-white/50'
}

const resolveDocumentStatus = (payload) => {
  if (payload?.processing_error) {
    return 'failed'
  }
  if (payload?.processed === true) {
    return 'completed'
  }
  if (payload?.processing === true) {
    return 'processing'
  }
  return payload?.status || 'pending'
}

// Filter Logic
const filteredChunks = computed(() => {
  if (!searchText.value) return chunks.value

  const query = searchText.value.toLowerCase()
  return chunks.value
    .filter(chunk => chunk.content.toLowerCase().includes(query))
    .map(chunk => {
      const content = chunk.content
      const index = content.toLowerCase().indexOf(query)
      const before = content.substring(0, index)
      const match = content.substring(index, index + query.length)
      const after = content.substring(index + query.length)
      
      return {
        ...chunk,
        highlighted: true,
        highlightedContent: `${before}<span class="bg-starlight-blue/30 text-white px-1 rounded">${match}</span>${after}`
      }
    })
})

// Actions
const loadData = async () => {
  if (!normalizedDocumentId.value) {
    showError('文档标识无效，无法加载详情', '加载文档详情失败')
    return
  }

  loading.value = true
  try {
    const [docResponse, chunkResponse] = await Promise.all([
      PDFService.getDocument(normalizedDocumentId.value),
      PDFService.getDocumentChunks(normalizedDocumentId.value)
    ])

    const docPayload = ensureApiSuccess(docResponse, '获取文档详情失败')
    document.value = {
      ...docPayload,
      status: resolveDocumentStatus(docPayload)
    }

    const chunkPayload = ensureApiSuccess(chunkResponse, '获取文档分块失败')
    const chunkList = chunkPayload?.results ?? chunkPayload?.chunks ?? chunkPayload ?? []
    chunks.value = Array.isArray(chunkList) ? chunkList : []
  } catch (err) {
    console.error('加载文档详情失败:', err)
    showError(err, '加载文档详情失败')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  if (typeof window !== 'undefined' && window.history.length > 1) {
    window.history.back()
    return
  }
  emit('navigate', '/admin/documents')
}

const goHome = () => emit('navigate', '/')

const downloadFile = async () => {
  try {
    const url = await PDFService.getDownloadUrl(normalizedDocumentId.value)
    window.open(url, '_blank')
  } catch (error) {
    console.error('下载文档失败:', error)
    showError(error, '下载文档失败')
  }
}

const reprocessFile = async () => {
  try {
    const payload = ensureApiSuccess(await PDFService.processPDF(normalizedDocumentId.value), '重新处理失败')
    showSuccess(payload.message || '已开始重新处理文档')
    await loadData()
  } catch (error) {
    console.error('重新处理文档失败:', error)
    showError(error, '重新处理失败')
  }
}

const deleteFile = async () => {
  try {
    await confirm('确定要删除该文档吗？此操作不可恢复。', '删除文档')
    ensureApiSuccess(await PDFService.deletePDF(normalizedDocumentId.value), '删除文档失败')
    showSuccess('文档已删除')
    goBack()
  } catch (error) {
    if (error === 'cancel') {
      return
    }
    console.error('删除文档失败:', error)
    showError(error, '删除文档失败')
  }
}

const searchSimilar = (content) => {
  const excerpt = String(content || '').trim().slice(0, 400)
  if (!excerpt) {
    showError('当前分块内容为空，无法发起相似内容检索。', '相似内容检索失败')
    return
  }

  const question = `请基于以下文段查找相似内容，并总结相关研究线索：\n\n${excerpt}`
  const target = `/workspace?tab=qa&question=${encodeURIComponent(question)}`
  window.location.assign(target)
}

watch(normalizedDocumentId, () => {
  loadData()
}, { immediate: true })
</script>

<style scoped>
.delay-100 { animation-delay: 0.1s; }
.delay-200 { animation-delay: 0.2s; }
</style>
