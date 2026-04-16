import { apiMethods } from '@/utils/apiClient'
import { API_CONFIG } from '@/config/api'

class ReviewService {
  async reviewDocument(documentId, reviewData) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.REVIEW_DASHBOARD, reviewData)
    return response.data
  }

  async getMeteoriteData(filters = {}) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.METEORITE_DATA, filters)
    return response.data
  }

  async getReviewDashboard() {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.REVIEW_DASHBOARD)
    return response.data
  }

  async getApprovedMeteorites(params = {}, config = {}) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.APPROVED_METEORITES, {
      ...config,
      params
    })
    return response.data
  }

  async getPendingMeteorites(params = {}) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.PENDING_METEORITES, { params })
    return response.data
  }

  async getRejectedMeteorites(params = {}) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.REJECTED_METEORITES, { params })
    return response.data
  }

  async getMeteoriteOptions() {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.METEORITE_OPTIONS)
    return response.data
  }

  async approveMeteorite(id, data = {}) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.APPROVE_METEORITE(id), data)
    return response.data
  }

  async rejectMeteorite(id, data = {}) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.REJECT_METEORITE(id), data)
    return response.data
  }

  async batchApproveMeteorite(meteoriteIds, notes = 'Batch approve review') {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.BATCH_APPROVE_METEORITE(), {
      meteorite_ids: meteoriteIds,
      notes
    })
    return response.data
  }

  async batchRejectMeteorite(
    meteoriteIds,
    reason = 'Batch reject review',
    category = 'data_quality',
    notes = 'Batch reject review'
  ) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.BATCH_REJECT_METEORITE(), {
      meteorite_ids: meteoriteIds,
      reason,
      category,
      notes
    })
    return response.data
  }

  async approveAllMeteorite(notes = 'Approve all review items') {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.APPROVE_ALL_METEORITE(), {
      notes
    })
    return response.data
  }

  async rejectAllMeteorite(
    reason = 'Reject all review items',
    category = 'data_quality',
    notes = 'Reject all review items'
  ) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.REJECT_ALL_METEORITE(), {
      reason,
      category,
      notes
    })
    return response.data
  }

  async restoreMeteorite(id, data = {}) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.RESTORE_METEORITE(id), data)
    return response.data
  }

  async permanentDeleteMeteorite(id, data = {}) {
    const response = await apiMethods.delete(API_CONFIG.ENDPOINTS.PERMANENT_DELETE_METEORITE(id), { data })
    return response.data
  }

  async getApprovedMeteoriteDetail(id) {
    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.METEORITE_DETAIL(id))
    return response.data
  }

  async deleteApprovedMeteorite(id) {
    const response = await apiMethods.delete(API_CONFIG.ENDPOINTS.METEORITE_DETAIL(id))
    return response.data
  }

  async updateMeteorite(id, data = {}) {
    const response = await apiMethods.put(API_CONFIG.ENDPOINTS.METEORITE_DETAIL(id), data)
    return response.data
  }

  async createMeteorite(data = {}) {
    const response = await apiMethods.post(API_CONFIG.ENDPOINTS.APPROVED_METEORITES, data)
    return response.data
  }

  async updateApprovedMeteorite(id, data = {}) {
    return this.updateMeteorite(id, data)
  }

  async searchMeteorites(params = {}) {
    const newParams = {}

    if (params.name) {
      newParams.search = params.name
    }
    if (params.classification) {
      newParams.classification = params.classification
    }
    if (params.origin) {
      newParams.origin = params.origin
    }
    if (params.discovery_location && !params.name) {
      newParams.search = params.discovery_location
    }
    if (params.page) {
      newParams.page = params.page
    }
    if (params.page_size) {
      newParams.page_size = params.page_size
    }
    if (params.organic_compound_name) {
      console.warn('organic_compound_name is not supported by the current meteorite search API')
    }

    const response = await apiMethods.get(API_CONFIG.ENDPOINTS.METEORITE_SEARCH, {
      params: newParams
    })
    const data = response.data || {}

    return {
      success: true,
      data: {
        results: data.results || [],
        count: data.count || 0,
        next: data.next || null,
        previous: data.previous || null
      }
    }
  }
}

const reviewService = new ReviewService()

export { reviewService as ReviewService }
export default reviewService
