import { computed, ref } from 'vue'

export function useReviewSelection({ items, getItemId }) {
  const selectedItems = ref([])

  const isAllSelected = computed(() => {
    return (
      items.value.length > 0 &&
      items.value.every((item) => selectedItems.value.includes(getItemId(item)))
    )
  })

  const toggleSelectAll = (checked = !isAllSelected.value) => {
    if (checked) {
      selectedItems.value = items.value.map((item) => getItemId(item))
      return
    }

    selectedItems.value = []
  }

  const clearSelection = () => {
    selectedItems.value = []
  }

  return {
    selectedItems,
    isAllSelected,
    toggleSelectAll,
    clearSelection
  }
}
