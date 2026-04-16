const HTML_RE = /<[^>]+>/i
const TRACEBACK_RE = /(Traceback \(most recent call last\)|^\s*File ".*", line \d+)/im
const LATIN1_MOJIBAKE_RE = /[ÃÂÆÐØÐæçéåø]/

const isBlob = (value) => typeof Blob !== 'undefined' && value instanceof Blob

const isPlainObject = (value) => Object.prototype.toString.call(value) === '[object Object]'

const repairMojibake = (value) => {
  if (typeof value !== 'string' || !value || !LATIN1_MOJIBAKE_RE.test(value)) {
    return value
  }

  try {
    const bytes = Uint8Array.from(Array.from(value).map((char) => char.charCodeAt(0) & 0xff))
    return new TextDecoder('utf-8', { fatal: false }).decode(bytes) || value
  } catch {
    return value
  }
}

const normalizeText = (value) => {
  if (value == null) {
    return ''
  }
  if (typeof value === 'string') {
    return repairMojibake(value).replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  }
  if (Array.isArray(value)) {
    return value.map((item) => normalizeText(item)).filter(Boolean).join('；')
  }
  if (isBlob(value)) {
    return ''
  }
  if (isPlainObject(value)) {
    return Object.entries(value)
      .map(([key, item]) => {
        const normalized = normalizeText(item)
        return normalized ? `${key}: ${normalized}` : ''
      })
      .filter(Boolean)
      .join('；')
  }
  return String(value).trim()
}

const sanitizeUserMessage = (value, fallbackMessage) => {
  const message = normalizeText(value)
  if (!message) {
    return fallbackMessage
  }
  if (HTML_RE.test(message)) {
    return '服务器返回了异常页面，请稍后重试'
  }
  if (TRACEBACK_RE.test(message)) {
    return fallbackMessage
  }
  return message
}

const unwrapResponsePayload = (responseData) => {
  if (!responseData || isBlob(responseData)) {
    return {}
  }
  if (typeof responseData === 'string') {
    const trimmed = responseData.trim()
    if (!trimmed) {
      return {}
    }
    try {
      const parsed = JSON.parse(trimmed)
      return isPlainObject(parsed) ? parsed : { message: trimmed }
    } catch {
      return { message: trimmed }
    }
  }
  if (isPlainObject(responseData)) {
    return responseData
  }
  return { message: normalizeText(responseData) }
}

export const extractApiError = (error, fallbackMessage = '请求失败') => {
  const payload = unwrapResponsePayload(error?.response?.data)
  const errorCode = normalizeText(payload.error_code || payload.code) || 'REQUEST_FAILED'

  let fallback = fallbackMessage
  if (!fallback || fallback === 'Request failed with status code 500') {
    fallback = '请求失败'
  }
  if (error?.message === 'Network Error') {
    fallback = '网络连接失败，请检查后端服务是否可用'
  }

  const message = sanitizeUserMessage(
    payload.message || payload.error || payload.msg || payload.detail || error?.message,
    fallback
  )
  const detail = sanitizeUserMessage(payload.detail || payload.error || error?.message, message)

  return {
    status: error?.response?.status || 0,
    errorCode,
    message,
    detail
  }
}

export const getApiErrorMessage = (error, fallbackMessage = '请求失败') => {
  return extractApiError(error, fallbackMessage).message
}
