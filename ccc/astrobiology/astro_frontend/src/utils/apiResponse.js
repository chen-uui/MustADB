import { extractApiError } from '@/utils/apiError'

const FAILED_STATUSES = new Set(['error', 'failed', 'failure'])

const isResponseWrapper = (value) => {
  return Boolean(
    value &&
      typeof value === 'object' &&
      Object.prototype.hasOwnProperty.call(value, 'data') &&
      Object.prototype.hasOwnProperty.call(value, 'status')
  )
}

export const unwrapApiPayload = (response) => {
  if (isResponseWrapper(response)) {
    return response.data
  }
  return response
}

export const createBusinessError = (payload, fallbackMessage = '操作失败') => {
  const error = new Error(fallbackMessage)
  error.response = {
    status: 200,
    data: payload
  }
  error.normalized = extractApiError(error, fallbackMessage)
  error.message = error.normalized.message
  return error
}

export const isApiFailure = (response) => {
  const payload = unwrapApiPayload(response)
  if (!payload || typeof payload !== 'object') {
    return false
  }

  if (payload.success === false || payload.ok === false) {
    return true
  }

  if (typeof payload.status === 'string' && FAILED_STATUSES.has(payload.status.toLowerCase())) {
    return true
  }

  return false
}

export const ensureApiSuccess = (response, fallbackMessage = '操作失败') => {
  const payload = unwrapApiPayload(response)

  if (isApiFailure(payload)) {
    throw createBusinessError(payload, fallbackMessage)
  }

  return payload
}

export const getApiMessage = (response, fallbackMessage = '') => {
  const payload = unwrapApiPayload(response)
  if (payload && typeof payload === 'object') {
    return payload.message || payload.detail || payload.error || fallbackMessage
  }
  return fallbackMessage
}
