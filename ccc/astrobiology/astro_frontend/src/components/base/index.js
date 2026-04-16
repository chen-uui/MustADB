/**
 * 统一RAG工作台基础UI组件
 * 完全重构版本 - 提供统一的基础UI组件
 */

// 导入所有基础组件
import LoadingSpinner from './LoadingSpinner.vue'
import ErrorAlert from './ErrorAlert.vue'
import EmptyState from './EmptyState.vue'
import StatusTag from './StatusTag.vue'
import Pagination from './Pagination.vue'

// 导入工具函数
import { useNotification, useConfirm } from './useNotification.js'

// 导出所有组件
export {
  LoadingSpinner,
  ErrorAlert,
  EmptyState,
  StatusTag,
  Pagination,
  useNotification,
  useConfirm
}

// 默认导出
export default {
  LoadingSpinner,
  ErrorAlert,
  EmptyState,
  StatusTag,
  Pagination,
  useNotification,
  useConfirm
}