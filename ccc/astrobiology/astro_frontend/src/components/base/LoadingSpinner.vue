<template>
  <div class="loading-spinner" v-show="loading">
    <el-icon class="is-loading">
      <Loading />
    </el-icon>
    <span class="loading-text">{{ text }}</span>
  </div>
</template>

<script setup>
import { Loading } from '@element-plus/icons-vue'

defineProps({
  loading: {
    type: Boolean,
    default: false
  },
  text: {
    type: String,
    default: '加载中...'
  },
  size: {
    type: String,
    default: 'default'
  }
})
</script>

<style scoped>
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #409eff;
}

.loading-spinner .el-icon {
  margin-right: 8px;
  font-size: 20px;
}

.loading-text {
  font-size: 14px;
}
</style>
