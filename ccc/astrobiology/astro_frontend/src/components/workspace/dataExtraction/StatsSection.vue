<template>
  <div class="stats-section">
    <div class="stats-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-icon">{{ stat.icon }}</div>
        <div class="stat-content">
          <h3>{{ stat.value }}</h3>
          <p>{{ stat.label }}</p>
          <p v-if="stat.description" class="stat-description">{{ stat.description }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  statistics: {
    type: Object,
    default: () => ({})
  }
})

const stats = computed(() => {
  // 如果有提取任务相关的统计数据，使用它们
  if (props.statistics?.total_tasks !== undefined) {
    return [
      {
        label: '总提取任务',
        value: props.statistics.total_tasks || 0,
        icon: '📊'
      },
      {
        label: '成功提取',
        value: props.statistics.successful_extractions || 0,
        icon: '✅'
      },
      {
        label: '进行中',
        value: props.statistics.running_tasks || 0,
        icon: '⏳'
      },
      {
        label: '成功率',
        value: props.statistics.success_rate 
          ? `${(props.statistics.success_rate * 100).toFixed(1)}%`
          : props.statistics.total_tasks > 0
            ? `${((props.statistics.successful_extractions || 0) / props.statistics.total_tasks * 100).toFixed(1)}%`
            : '0.0%',
        icon: '📈'
      }
    ]
  }
  
  // 如果没有提取任务数据，显示提示信息
  return [
    {
      label: '当前会话状态',
      value: props.statistics?.current_session_status || '未开始',
      icon: '🔍',
      description: '开始搜索以创建提取任务'
    },
    {
      label: '已处理片段',
      value: props.statistics?.processed_segments || 0,
      icon: '📄'
    },
    {
      label: '已提取数据',
      value: props.statistics?.extracted_entities || 0,
      icon: '💎'
    },
    {
      label: '聚合结果',
      value: props.statistics?.aggregated_results || 0,
      icon: '📦'
    }
  ]
})
</script>

<style scoped>
.stats-section {
  margin-bottom: 40px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.stat-card {
  background: white;
  border-radius: 15px;
  padding: 25px;
  display: flex;
  align-items: center;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-icon {
  font-size: 3rem;
  margin-right: 20px;
}

.stat-content h3 {
  font-size: 2.5rem;
  font-weight: 700;
  color: #333;
  margin: 0;
}

.stat-content p {
  color: #666;
  margin: 5px 0 0 0;
  font-size: 1rem;
}

.stat-description {
  color: #999;
  font-size: 0.875rem;
  margin-top: 4px;
  font-style: italic;
}
</style>

