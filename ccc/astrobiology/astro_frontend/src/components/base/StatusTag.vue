<template>
  <el-tag :type="tagType" :size="size" :effect="effect">
    {{ statusText }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'unknown'
  },
  size: {
    type: String,
    default: 'small'
  },
  effect: {
    type: String,
    default: 'light'
  }
})

const tagType = computed(() => {
  const typeMap = {
    active: 'success',
    inactive: 'info',
    pending: 'warning',
    error: 'danger',
    completed: 'success',
    processing: 'warning',
    failed: 'danger',
    unknown: 'info'
  }
  return typeMap[props.status] || 'info'
})

const statusText = computed(() => {
  const textMap = {
    active: '活跃',
    inactive: '非活跃',
    pending: '待处理',
    error: '错误',
    completed: '已完成',
    processing: '处理中',
    failed: '失败',
    unknown: '未知'
  }
  return textMap[props.status] || props.status
})
</script>

<style scoped>
.el-tag {
  font-weight: 500;
}
</style>
