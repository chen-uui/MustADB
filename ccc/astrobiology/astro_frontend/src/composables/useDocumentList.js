import { ElMessage, ElMessageBox } from 'element-plus'

import PDFService from '@/services/pdfService'
import { getApiErrorMessage } from '@/utils/apiError'

const STATS_CACHE_DURATION = 30000

const mapDocument = (doc) => ({
  id: doc.id,
  title: doc.title,
  size: `${((doc.file_size || 0) / 1024 / 1024).toFixed(1)}MB`,
  date: new Date(doc.upload_date).toISOString().split('T')[0],
  processed: doc.processed,
  category: doc.category,
  authors: doc.authors,
  year: doc.year,
  processing_error: doc.processing_error,
  processing_error_code: doc.processing_error_code
})

export function useDocumentList({
  workspaceMode = false,
  loading,
  stats,
  documents,
  currentPage,
  totalPages,
  pageSize,
  processingDoc,
  loadStartTime,
  loadEndTime,
  loadDuration
}) {
  let statsCache = null
  let statsCacheTime = 0

  const loadDocuments = async (page = 1) => {
    try {
      loading.value = true
      loadStartTime.value = performance.now()

      const response = await PDFService.getDocuments({
        page,
        page_size: pageSize
      })

      if (response.data?.documents) {
        documents.value = response.data.documents.map(mapDocument)
        const pagination = response.data.pagination
        currentPage.value = pagination?.current_page || page
        totalPages.value = pagination?.total_pages || 1
      } else {
        const data = response.data?.results || response.data || []
        documents.value = data.map(mapDocument)
        currentPage.value = page
        totalPages.value = Math.max(1, Math.ceil((response.data?.count || data.length) / pageSize))
      }

      if (workspaceMode) {
        console.log(
          'Workspace mode - document states:',
          documents.value.map((doc) => ({
            title: doc.title,
            processed: doc.processed,
            processing_error: doc.processing_error
          }))
        )
      }
    } catch (error) {
      console.error('Failed to load documents:', error)
      documents.value = []
      totalPages.value = 1
      currentPage.value = 1
      ElMessage.error(getApiErrorMessage(error, '加载文档列表失败'))
    } finally {
      loadEndTime.value = performance.now()
      loading.value = false
      if (loadDuration.value > 0) {
        console.log(`Document load duration: ${loadDuration.value.toFixed(2)}ms`)
      }
    }
  }

  const loadStats = async (forceRefresh = false) => {
    try {
      const now = Date.now()
      if (!forceRefresh && statsCache && now - statsCacheTime < STATS_CACHE_DURATION) {
        Object.assign(stats, statsCache)
        return
      }

      const docResponse = await PDFService.getStats()
      const docData = docResponse.data || {}

      stats.totalFiles = docData.total_documents ?? 0
      stats.uploadCount = docData.monthly_upload ?? 0
      stats.chunksCount = docData.total_chunks ?? 0
      stats.processedFiles = docData.processed_documents ?? 0
      stats.pendingFiles = docData.pending_documents ?? 0
      stats.processingRate = docData.processing_rate ?? 0

      statsCache = { ...stats }
      statsCacheTime = now
    } catch (error) {
      console.error('Failed to load document stats:', error)
      ElMessage.error(getApiErrorMessage(error, '加载文档统计失败'))
    }
  }

  const downloadPDF = async (id) => {
    try {
      const response = await PDFService.downloadPDF(id)
      const blob = response.data instanceof Blob ? response.data : new Blob([response.data])
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `document_${id}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download PDF:', error)
      ElMessage.error(getApiErrorMessage(error, '下载 PDF 失败'))
    }
  }

  const deleteDocument = async (id) => {
    try {
      await ElMessageBox.confirm('确定要删除这个 PDF 文档吗？此操作不可恢复。', '删除确认', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消'
      })
    } catch {
      return
    }

    try {
      loading.value = true
      await PDFService.deletePDF(id)
      documents.value = documents.value.filter((doc) => doc.id !== id)

      stats.totalFiles = Math.max(0, stats.totalFiles - 1)
      stats.processedFiles = Math.max(0, Math.min(stats.processedFiles, stats.totalFiles))
      stats.processingRate = stats.totalFiles > 0 ? Math.round((stats.processedFiles / stats.totalFiles) * 100) : 0

      ElMessage.success('文档已删除')
    } catch (error) {
      console.error('Failed to delete document:', error)
      ElMessage.error(getApiErrorMessage(error, '删除文档失败'))
      await loadDocuments(currentPage.value)
      await loadStats(true)
    } finally {
      loading.value = false
    }
  }

  const processDocument = async (id) => {
    processingDoc.value = id
    try {
      const result = await PDFService.processPDF(id)
      const docIndex = documents.value.findIndex((doc) => doc.id === id)
      if (docIndex !== -1) {
        documents.value[docIndex] = {
          ...documents.value[docIndex],
          processed: true,
          processing_error: null,
          processing_error_code: null
        }
      }

      if (stats.processedFiles < stats.totalFiles) {
        stats.processedFiles += 1
        stats.processingRate = Math.round((stats.processedFiles / stats.totalFiles) * 100)
      }

      ElMessage.success(result?.message || '文档处理完成')
    } catch (error) {
      console.error('Failed to process document:', error)
      ElMessage.error(getApiErrorMessage(error, '处理文档失败'))
      await loadDocuments(currentPage.value)
    } finally {
      processingDoc.value = null
    }
  }

  const syncFiles = async () => {
    try {
      await ElMessageBox.confirm(
        '确定要同步文件夹中的 PDF 文档吗？这会补齐新文件并清理已删除文件的索引记录。',
        '同步文件',
        {
          type: 'warning',
          confirmButtonText: '同步',
          cancelButtonText: '取消'
        }
      )
    } catch {
      return
    }

    try {
      loading.value = true
      const response = await PDFService.syncFiles()
      const payload = response.data || {}
      const added = payload.added_count ?? payload.added ?? 0
      const removed = payload.removed_count ?? payload.removed ?? 0
      const message = payload.message || `同步完成，新增 ${added} 个文档，移除 ${removed} 个文档`
      ElMessage.success(message)

      await loadDocuments(currentPage.value)
      await loadStats(true)
    } catch (error) {
      console.error('Failed to sync files:', error)
      ElMessage.error(getApiErrorMessage(error, '同步文件失败'))
    } finally {
      loading.value = false
    }
  }

  const cleanDocumentTitle = (title) => {
    if (!title) {
      return '未命名文档'
    }

    if (title.length > 36 && title[36] === ' ') {
      const uuidPattern = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\s/
      if (uuidPattern.test(title)) {
        return title.substring(37).trim()
      }
    }

    return title.replace(/\.pdf$/i, '')
  }

  return {
    loadDocuments,
    loadStats,
    downloadPDF,
    deleteDocument,
    processDocument,
    syncFiles,
    cleanDocumentTitle
  }
}
