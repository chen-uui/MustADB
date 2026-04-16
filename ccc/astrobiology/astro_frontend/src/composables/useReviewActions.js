import { ensureApiSuccess } from '@/utils/apiResponse'

export function useReviewActions({ selectedItems }) {
  const clearSelection = () => {
    selectedItems.value = []
  }

  const runBatchAction = async ({ items = selectedItems.value, execute, afterSuccess }) => {
    const snapshot = [...items]

    if (snapshot.length === 0) {
      return false
    }

    await Promise.all(
      snapshot.map(async (item) => {
        const result = await execute(item)
        return ensureApiSuccess(result, '批量操作失败')
      })
    )
    clearSelection()
    await afterSuccess?.(snapshot)

    return true
  }

  return {
    clearSelection,
    runBatchAction
  }
}
