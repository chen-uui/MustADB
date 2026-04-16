import { API_CONFIG } from '@/config/api'
import { apiMethods } from '@/utils/apiClient'

class DocumentService {
  async uploadPDF(file, onProgress = null) {
    const formData = new FormData()
    formData.append('file', file)

    const config = {}
    if (onProgress) {
      config.onUploadProgress = (progressEvent) => {
        if (!progressEvent?.total) {
          return
        }
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(percentCompleted)
      }
    }

    const response = await apiMethods.upload(API_CONFIG.ENDPOINTS.UPLOAD, formData, config)
    return response.data
  }

  async listPDFs() {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.DOCUMENTS)
    return response.data
  }

  async searchPDFs(query, limit = 10) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.SEARCH, { query, limit })
    return response.data
  }

  async downloadPDF(documentId) {
    return apiMethods.download(API_CONFIG.ENDPOINTS.DOWNLOAD(documentId))
  }

  async deletePDF(documentId) {
    const response = await apiMethods.delete(API_CONFIG.ENDPOINTS.DELETE(documentId))
    return response.data
  }

  async processPDF(documentId) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.PROCESS_SINGLE(documentId))
    return response.data
  }

  async getDocument(documentId) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.DOCUMENT_DETAIL(documentId), { cache: false })
    return response.data
  }

  async getDocumentChunks(documentId) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.CHUNKS, {
      params: {
        document_id: documentId,
        limit: 1000,
        offset: 0
      }
    })
    return response.data
  }

  async getDocuments(params = {}) {
    return apiMethods.get(API_CONFIG.ENDPOINTS.DOCUMENTS, { params })
  }

  async getStats() {
    return apiMethods.get(API_CONFIG.ENDPOINTS.STATS)
  }

  async getDownloadUrl(documentId) {
    return new URL(API_CONFIG.ENDPOINTS.DOWNLOAD(documentId), API_CONFIG.BASE_URL).toString()
  }

  async syncFiles() {
    return apiMethods.post(API_CONFIG.ENDPOINTS.SYNC_FILES)
  }

  async uploadDocument(formData) {
    return apiMethods.upload(API_CONFIG.ENDPOINTS.UPLOAD, formData)
  }

  async processPending() {
    return apiMethods.post(API_CONFIG.ENDPOINTS.PROCESS_PENDING)
  }

  async processStale() {
    return apiMethods.post(API_CONFIG.ENDPOINTS.PROCESS_STALE)
  }

  async getProcessingStatus() {
    return apiMethods.get(API_CONFIG.ENDPOINTS.PROCESSING_STATUS, { cache: false })
  }

  async reprocessAll(payload = { confirm: true }) {
    return apiMethods.post(API_CONFIG.ENDPOINTS.REPROCESS_ALL, payload)
  }

  async cancelProcessing() {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.CANCEL_PROCESSING)
    return response.data
  }
}

const documentService = new DocumentService()

export { documentService as DocumentService }
export default documentService
