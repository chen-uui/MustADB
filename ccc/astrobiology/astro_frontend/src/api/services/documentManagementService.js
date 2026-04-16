/**
 * 文档管理API服务
 * 完全重构版本 - 直接调用后端API，不依赖旧组件
 */

import { api } from '../client.js'
import { API_ENDPOINTS, FILE_SIZE_LIMITS, MIME_TYPES } from '../interfaces.js'

class DocumentManagementService {
  /**
   * 获取文档列表
   * @param {Object} params - 查询参数
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   * @param {string} params.status - 文档状态
   * @param {string} params.search - 搜索关键词
   * @returns {Promise<Object>} 文档列表
   */
  async getDocuments(params = {}) {
    return await api.get(API_ENDPOINTS.DOCUMENT.LIST, params, {
      cache: true,
      cacheTTL: 2 * 60 * 1000 // 2分钟缓存
    })
  }

  /**
   * 上传文档
   * @param {File} file - 文档文件
   * @param {Function} onProgress - 进度回调
   * @param {Object} options - 上传选项
   * @returns {Promise<Object>} 上传结果
   */
  async uploadDocument(file, onProgress = null, options = {}) {
    // 验证文件
    this.validateFile(file)

    const uploadOptions = {
      timeout: 300000, // 5分钟超时
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress(percentCompleted)
        }
      },
      ...options
    }

    return await api.upload(API_ENDPOINTS.DOCUMENT.UPLOAD, file, onProgress, uploadOptions)
  }

  /**
   * 批量上传文档
   * @param {Array<File>} files - 文档文件数组
   * @param {Function} onProgress - 进度回调
   * @param {Object} options - 上传选项
   * @returns {Promise<Array>} 上传结果数组
   */
  async uploadDocuments(files, onProgress = null, options = {}) {
    const uploadPromises = files.map(async (file, index) => {
      const fileProgress = (progress) => {
        if (onProgress) {
          onProgress({
            fileIndex: index,
            fileName: file.name,
            progress: progress,
            totalFiles: files.length
          })
        }
      }

      try {
        const result = await this.uploadDocument(file, fileProgress, options)
        return { success: true, file: file.name, result }
      } catch (error) {
        return { success: false, file: file.name, error: error.message }
      }
    })

    return await Promise.all(uploadPromises)
  }

  /**
   * 获取文档详情
   * @param {number} id - 文档ID
   * @returns {Promise<Object>} 文档详情
   */
  async getDocumentDetail(id) {
    const url = API_ENDPOINTS.DOCUMENT.DETAIL.replace('{id}', id)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 删除文档
   * @param {number} id - 文档ID
   * @returns {Promise<Object>} 删除结果
   */
  async deleteDocument(id) {
    const url = API_ENDPOINTS.DOCUMENT.DELETE.replace('{id}', id)
    return await api.delete(url, {
      cache: false
    })
  }

  /**
   * 批量删除文档
   * @param {Array<number>} ids - 文档ID数组
   * @returns {Promise<Array>} 删除结果数组
   */
  async deleteDocuments(ids) {
    const deletePromises = ids.map(async (id) => {
      try {
        const result = await this.deleteDocument(id)
        return { success: true, id, result }
      } catch (error) {
        return { success: false, id, error: error.message }
      }
    })

    return await Promise.all(deletePromises)
  }

  /**
   * 处理文档
   * @param {number} id - 文档ID
   * @param {Object} options - 处理选项
   * @returns {Promise<Object>} 处理结果
   */
  async processDocument(id, options = {}) {
    const url = API_ENDPOINTS.DOCUMENT.PROCESS.replace('{id}', id)
    return await api.post(url, options, {
      cache: false
    })
  }

  /**
   * 获取文档处理状态
   * @param {number} id - 文档ID
   * @returns {Promise<Object>} 处理状态
   */
  async getDocumentStatus(id) {
    const url = API_ENDPOINTS.DOCUMENT.STATUS.replace('{id}', id)
    return await api.get(url, {}, {
      cache: true,
      cacheTTL: 30 * 1000 // 30秒缓存
    })
  }

  /**
   * 获取文档块
   * @param {Object} params - 查询参数
   * @param {number} params.document_id - 文档ID
   * @param {number} params.page - 页码
   * @param {number} params.page_size - 每页数量
   * @returns {Promise<Object>} 文档块列表
   */
  async getDocumentChunks(params) {
    return await api.get(API_ENDPOINTS.DOCUMENT.CHUNKS, params, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 搜索文档
   * @param {Object} searchParams - 搜索参数
   * @param {string} searchParams.query - 搜索关键词
   * @param {string} searchParams.status - 文档状态
   * @param {string} searchParams.date_from - 开始日期
   * @param {string} searchParams.date_to - 结束日期
   * @returns {Promise<Object>} 搜索结果
   */
  async searchDocuments(searchParams) {
    return await api.get(`${API_ENDPOINTS.DOCUMENT.LIST}search/`, searchParams, {
      cache: true,
      cacheTTL: 2 * 60 * 1000
    })
  }

  /**
   * 获取文档统计
   * @returns {Promise<Object>} 文档统计
   */
  async getDocumentStatistics() {
    return await api.get(`${API_ENDPOINTS.DOCUMENT.LIST}statistics/`, {}, {
      cache: true,
      cacheTTL: 5 * 60 * 1000
    })
  }

  /**
   * 预览文档
   * @param {number} id - 文档ID
   * @returns {Promise<Blob>} 文档预览
   */
  async previewDocument(id) {
    const url = `${API_ENDPOINTS.DOCUMENT.DETAIL.replace('{id}', id)}preview/`
    return await api.download(url, null, {
      responseType: 'blob'
    })
  }

  /**
   * 下载文档
   * @param {number} id - 文档ID
   * @param {string} filename - 文件名
   * @returns {Promise<Blob>} 文档文件
   */
  async downloadDocument(id, filename = null) {
    const url = `${API_ENDPOINTS.DOCUMENT.DETAIL.replace('{id}', id)}download/`
    return await api.download(url, filename)
  }

  /**
   * 验证文件
   * @param {File} file - 文件对象
   * @throws {Error} 文件验证失败
   */
  validateFile(file) {
    if (!file) {
      throw new Error('请选择文件')
    }

    // 检查文件类型
    const allowedTypes = Object.values(MIME_TYPES)
    if (!allowedTypes.includes(file.type)) {
      throw new Error('不支持的文件类型，请上传PDF、DOC、DOCX、TXT或RTF文件')
    }

    // 检查文件大小
    const maxSize = FILE_SIZE_LIMITS.PDF // 默认使用PDF限制
    if (file.size > maxSize) {
      throw new Error(`文件大小超过限制，最大允许${Math.round(maxSize / 1024 / 1024)}MB`)
    }

    // 检查文件名
    if (!file.name || file.name.trim() === '') {
      throw new Error('文件名不能为空')
    }
  }

  /**
   * 获取支持的文件类型
   * @returns {Array} 支持的文件类型
   */
  getSupportedFileTypes() {
    return [
      { type: 'pdf', mime: MIME_TYPES.PDF, extension: '.pdf', maxSize: FILE_SIZE_LIMITS.PDF },
      { type: 'doc', mime: MIME_TYPES.DOC, extension: '.doc', maxSize: FILE_SIZE_LIMITS.DOC },
      { type: 'docx', mime: MIME_TYPES.DOCX, extension: '.docx', maxSize: FILE_SIZE_LIMITS.DOCX },
      { type: 'txt', mime: MIME_TYPES.TXT, extension: '.txt', maxSize: FILE_SIZE_LIMITS.TXT },
      { type: 'rtf', mime: MIME_TYPES.RTF, extension: '.rtf', maxSize: FILE_SIZE_LIMITS.RTF }
    ]
  }

  /**
   * 获取上传进度
   * @param {string} uploadId - 上传ID
   * @returns {Promise<Object>} 上传进度
   */
  async getUploadProgress(uploadId) {
    return await api.get(`${API_ENDPOINTS.DOCUMENT.UPLOAD}progress/${uploadId}/`, {}, {
      cache: false
    })
  }

  /**
   * 取消上传
   * @param {string} uploadId - 上传ID
   * @returns {Promise<Object>} 取消结果
   */
  async cancelUpload(uploadId) {
    return await api.post(`${API_ENDPOINTS.DOCUMENT.UPLOAD}cancel/${uploadId}/`, {}, {
      cache: false
    })
  }
}

// 创建单例实例
const documentManagementService = new DocumentManagementService()

export default documentManagementService
export { DocumentManagementService }