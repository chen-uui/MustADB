import { apiMethods } from '@/utils/apiClient'
import { API_CONFIG } from '@/config/api'
import { extractApiError } from '@/utils/apiError'

const STREAM_FALLBACK_TOKEN = 'c7808553361817594a38e375f8aec670230fc253'

class QAService {
  async askQuestion(params, endpoint = 'QA_ASK', signal = null) {
    let data
    if (typeof params === 'string') {
      data = { question: params }
      if (endpoint && typeof endpoint === 'string' && !API_CONFIG.ENDPOINTS[endpoint]) {
        data.document_id = endpoint
        endpoint = 'QA_ASK'
      }
    } else {
      data = { ...params }
    }

    const endpointUrl =
      typeof endpoint === 'string' && API_CONFIG.ENDPOINTS[endpoint]
        ? API_CONFIG.ENDPOINTS[endpoint]
        : API_CONFIG.ENDPOINTS.QA_ASK

    if (data.stream) {
      return this.askQuestionStream(data, endpointUrl, signal)
    }

    const response = await apiMethods.post(endpointUrl, data, { signal })
    return response.data
  }

  async askQuestionStream(data, endpointUrl, signal = null) {
    try {
      const token =
        (typeof window !== 'undefined' && window.localStorage.getItem('token')) || STREAM_FALLBACK_TOKEN

      const response = await fetch(`${API_CONFIG.BASE_URL}${endpointUrl}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(data),
        signal
      })

      if (!response.ok) {
        const contentType = response.headers.get('content-type') || ''
        let payload = {}

        if (contentType.includes('application/json')) {
          payload = await response.json()
        } else {
          payload = await response.text()
        }

        const streamError = new Error('流式问答失败')
        streamError.response = {
          status: response.status,
          data: payload
        }
        throw streamError
      }

      return {
        success: true,
        stream: response.body,
        status: response.status
      }
    } catch (error) {
      console.error('Stream request failed:', error)
      const normalized = extractApiError(error, '问答失败')
      return {
        success: false,
        error: normalized.message,
        detail: normalized.detail,
        status: normalized.status || 'Unknown error'
      }
    }
  }

  async getSystemHealth() {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.SYSTEM_HEALTH)
    return response.data
  }
}

const qaService = new QAService()

export { qaService as QAService }
export default qaService
