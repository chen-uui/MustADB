import axios from 'axios'

import { API_CONFIG, REQUEST_CONFIG } from '@/config/api'
import { extractApiError } from '@/utils/apiError'
import requestCache from './requestCache'

const pendingRequests = new Map()

const apiClient = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: REQUEST_CONFIG.TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

const DEV_TOKEN = 'c7808553361817594a38e375f8aec670230fc253'

const getAuthToken = () => {
  const stored = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null
  if (stored && stored.trim() !== '') {
    return stored
  }
  return DEV_TOKEN
}

apiClient.interceptors.request.use(
  (config) => {
    const isAuthEndpoint =
      config.url &&
      (config.url.includes('/auth/login/') || config.url.includes('/auth/register/'))

    if (!isAuthEndpoint) {
      const token = getAuthToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }

    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const normalized = extractApiError(error, '请求失败')
    error.normalized = normalized

    console.error('API request failed', {
      url: error?.config?.url,
      method: error?.config?.method,
      status: normalized.status,
      error_code: normalized.errorCode,
      message: normalized.message,
      detail: normalized.detail
    })

    return Promise.reject(error)
  }
)

const retryRequest = async (request, retries = REQUEST_CONFIG.RETRY_COUNT) => {
  try {
    return await request()
  } catch (error) {
    if (retries > 0 && error.response?.status >= 500) {
      await new Promise((resolve) => setTimeout(resolve, REQUEST_CONFIG.RETRY_DELAY))
      return retryRequest(request, retries - 1)
    }
    throw error
  }
}

export const apiMethods = {
  get: async (url, config = {}) => {
    const params = config.params || {}
    const useCache = config.cache !== false

    if (useCache) {
      const cached = requestCache.get(url, params)
      if (cached) {
        return { data: cached, status: 200, fromCache: true }
      }
    }

    const requestKey = `${url}?${JSON.stringify(params)}`
    if (pendingRequests.has(requestKey)) {
      return pendingRequests.get(requestKey)
    }

    const requestPromise = retryRequest(() => apiClient.get(url, config))
      .then((response) => {
        if (useCache && response.data) {
          requestCache.set(url, params, response.data)
        }
        pendingRequests.delete(requestKey)
        return response
      })
      .catch((error) => {
        pendingRequests.delete(requestKey)
        throw error
      })

    pendingRequests.set(requestKey, requestPromise)
    return requestPromise
  },

  post: (url, data = {}, config = {}) => retryRequest(() => apiClient.post(url, data, config)),
  patch: (url, data = {}, config = {}) => retryRequest(() => apiClient.patch(url, data, config)),
  put: (url, data = {}, config = {}) => retryRequest(() => apiClient.put(url, data, config)),
  delete: (url, config = {}) => retryRequest(() => apiClient.delete(url, config)),

  upload: (url, formData, config = {}) => {
    const uploadConfig = {
      ...config,
      headers: {
        ...config.headers,
        'Content-Type': 'multipart/form-data'
      }
    }
    return retryRequest(() => apiClient.post(url, formData, uploadConfig))
  },

  download: (url, config = {}) => {
    const downloadConfig = {
      ...config,
      responseType: 'blob'
    }
    return retryRequest(() => apiClient.get(url, downloadConfig))
  }
}

export default apiClient
