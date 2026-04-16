<template>
  <div class="empty-state">
    <el-icon class="empty-icon">
      <component :is="iconComponent" />
    </el-icon>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-description">{{ description }}</p>
    <slot name="action">
      <el-button v-if="actionText" @click="$emit('action')" type="primary">
        {{ actionText }}
      </el-button>
    </slot>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { 
  Search, 
  Document, 
  ChatDotRound, 
  Setting, 
  Lightning, 
  TrendCharts,
  FolderOpened
} from '@element-plus/icons-vue'

const props = defineProps({
  title: {
    type: String,
    default: '暂无数据'
  },
  description: {
    type: String,
    default: '请尝试其他操作'
  },
  icon: {
    type: String,
    default: 'folder'
  },
  actionText: {
    type: String,
    default: ''
  }
})

defineEmits(['action'])

const iconComponent = computed(() => {
  const iconMap = {
    search: Search,
    document: Document,
    chat: ChatDotRound,
    setting: Setting,
    lightning: Lightning,
    chart: TrendCharts,
    folder: FolderOpened
  }
  return iconMap[props.icon] || FolderOpened
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: #909399;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  color: #c0c4cc;
}

.empty-title {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 500;
  color: #606266;
}

.empty-description {
  margin: 0 0 20px 0;
  font-size: 14px;
  color: #909399;
  line-height: 1.5;
}
</style>
