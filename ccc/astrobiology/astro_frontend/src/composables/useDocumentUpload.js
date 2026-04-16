import { ElMessage } from 'element-plus'

import PDFService from '@/services/pdfService'
import { getApiErrorMessage } from '@/utils/apiError'

const POLL_INTERVAL = 3000
const POLL_TIMEOUT = 180000

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export function useDocumentUpload({
  fileInput,
  currentPage,
  loadDocuments,
  loadStats,
  processingFiles,
  showProgressModal,
  progressModalRef,
  updateProgress,
  closeProgressModal
}) {
  const triggerFileUpload = () => {
    fileInput.value?.click()
  }

  const pollDocumentResult = async (documentId, fileName) => {
    const deadline = Date.now() + POLL_TIMEOUT

    while (Date.now() < deadline) {
      const document = await PDFService.getDocument(documentId)
      if (document?.processed) {
        return { success: true, file: fileName }
      }

      if (document?.processing_error) {
        return {
          success: false,
          file: fileName,
          message: document.processing_error,
          errorCode: document.processing_error_code || 'PDF_PROCESS_FAILED'
        }
      }

      await sleep(POLL_INTERVAL)
    }

    return {
      success: false,
      file: fileName,
      message: 'PDF 处理超时，请稍后刷新列表查看结果',
      errorCode: 'PDF_PROCESS_TIMEOUT'
    }
  }

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files || [])
    if (files.length === 0) {
      return
    }

    processingFiles.value = files.map((file) => ({ name: file.name, size: file.size }))
    showProgressModal.value = true
    progressModalRef.value?.reset()
    updateProgress({
      processed: 0,
      total: files.length,
      current_file: '准备上传文件...',
      progress: 0
    })

    const pendingDocuments = []

    try {
      for (const file of files) {
        try {
          const result = await PDFService.uploadPDF(file, (progress) => {
            updateProgress({
              total: files.length,
              current_file: `正在上传：${file.name}`,
              progress
            })
          })

          if (result?.existing) {
            progressModalRef.value?.handleProcessingComplete({ total: files.length })
            ElMessage.warning(result.message || `${file.name} 已存在，已跳过重复上传`)
            continue
          }

          if (result?.document_id) {
            pendingDocuments.push({
              documentId: result.document_id,
              fileName: file.name
            })
          } else {
            progressModalRef.value?.handleProcessingError({
              file: file.name,
              message: '上传成功，但未返回文档编号，无法继续跟踪处理结果'
            })
          }
        } catch (error) {
          progressModalRef.value?.handleProcessingError({
            file: file.name,
            message: getApiErrorMessage(error, '文件上传失败')
          })
        }
      }

      for (const item of pendingDocuments) {
        updateProgress({
          total: files.length,
          current_file: `正在处理：${item.fileName}`,
          progress: 0
        })

        try {
          const result = await pollDocumentResult(item.documentId, item.fileName)
          if (result.success) {
            progressModalRef.value?.handleProcessingComplete({ total: files.length })
          } else {
            progressModalRef.value?.handleProcessingError({
              file: item.fileName,
              message: result.message
            })
          }
        } catch (error) {
          progressModalRef.value?.handleProcessingError({
            file: item.fileName,
            message: getApiErrorMessage(error, '获取 PDF 处理结果失败')
          })
        }
      }

      await loadDocuments(currentPage.value)
      await loadStats(true)
    } catch (error) {
      ElMessage.error(getApiErrorMessage(error, '上传流程执行失败'))
      closeProgressModal()
    } finally {
      event.target.value = ''
    }
  }

  return {
    triggerFileUpload,
    handleFileUpload
  }
}
