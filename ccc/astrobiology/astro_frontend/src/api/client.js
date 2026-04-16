import apiClient, { apiMethods } from '@/utils/apiClient'

const sanitizeOptions = (options = {}) => {
  const { cache, cacheTTL, ...rest } = options || {}
  return rest
}

export const api = {
  get(url, params = {}, options = {}) {
    const config = sanitizeOptions(options)
    config.params = params
    return apiMethods.get(url, config)
  },
  post(url, data = {}, options = {}) {
    return apiMethods.post(url, data, sanitizeOptions(options))
  },
  put(url, data = {}, options = {}) {
    return apiMethods.put(url, data, sanitizeOptions(options))
  },
  patch(url, data = {}, options = {}) {
    return apiMethods.patch(url, data, sanitizeOptions(options))
  },
  delete(url, options = {}) {
    return apiMethods.delete(url, sanitizeOptions(options))
  },
  download(url, params = null, options = {}) {
    const config = sanitizeOptions(options)
    if (params) config.params = params
    return apiMethods.download(url, config)
  }
}

export default api
