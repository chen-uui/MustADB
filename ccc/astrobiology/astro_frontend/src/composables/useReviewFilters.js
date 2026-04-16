import { computed, ref } from 'vue'

export const createDefaultReviewFilters = () => ({
  classification: '',
  origin: '',
  confidence_min: '',
  confidence_max: ''
})

export function useReviewFilters({
  initialPageSize = 20,
  initialSortField = '',
  initialSortOrder = 'asc',
  initialFilters = createDefaultReviewFilters()
} = {}) {
  const searchQuery = ref('')
  const showFilters = ref(false)
  const currentPage = ref(1)
  const pageSize = ref(initialPageSize)
  const totalCount = ref(0)
  const sortField = ref(initialSortField)
  const sortOrder = ref(initialSortOrder)
  const filters = ref({ ...initialFilters })

  const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

  const visiblePages = computed(() => {
    const pages = []
    const start = Math.max(1, currentPage.value - 2)
    const end = Math.min(totalPages.value, currentPage.value + 2)

    for (let page = start; page <= end; page += 1) {
      pages.push(page)
    }

    return pages
  })

  const resetPage = () => {
    currentPage.value = 1
  }

  const handleSearch = (onChange) => {
    resetPage()
    onChange?.()
  }

  const sortBy = (field, onChange) => {
    if (sortField.value === field) {
      sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
    } else {
      sortField.value = field
      sortOrder.value = 'asc'
    }

    onChange?.()
  }

  const getSortIcon = (field) => {
    if (sortField.value !== field) {
      return 'icon-sort'
    }

    return sortOrder.value === 'asc' ? 'icon-sort-up' : 'icon-sort-down'
  }

  const applyFilters = (onChange) => {
    resetPage()
    onChange?.()
  }

  const clearFilters = (onChange) => {
    filters.value = { ...initialFilters }
    resetPage()
    onChange?.()
  }

  const goToPage = (page, onChange) => {
    if (page >= 1 && page <= totalPages.value) {
      currentPage.value = page
      onChange?.()
    }
  }

  return {
    searchQuery,
    showFilters,
    currentPage,
    pageSize,
    totalCount,
    totalPages,
    sortField,
    sortOrder,
    filters,
    visiblePages,
    handleSearch,
    sortBy,
    getSortIcon,
    applyFilters,
    clearFilters,
    goToPage,
    resetPage
  }
}
