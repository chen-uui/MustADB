<template>
  <div class="system-health-view">
    <AdminWorkspaceHeader 
      :active-tab="'system-health'"
      @navigate="handleNavigate"
    />
    <div class="system-health-content">
      <!-- 页面标题 -->
      <div class="page-header">
        <h1 class="page-title">
          <i class="bi bi-activity"></i>
          系统健康监控
        </h1>
        <p class="page-subtitle">
          实时监控RAG系统各组件的运行状态和性能指标
        </p>
      </div>

      <!-- 主要内容区域 -->
      <div class="main-content">
        <SystemHealth />
      </div>
    </div>
  </div>
</template>

<script setup>
import SystemHealth from '@/components/SystemHealth.vue'
import AdminWorkspaceHeader from '@/components/workspace/AdminWorkspaceHeader.vue'

const emit = defineEmits(['navigate'])

const handleNavigate = (path) => {
  emit('navigate', path)
}
</script>

<style scoped>
.system-health-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f5f7fa;
}

.system-health-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0 0 0.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.page-title i {
  color: #3b82f6;
  font-size: 1.5rem;
}

.page-subtitle {
  color: #64748b;
  font-size: 0.9375rem;
  margin: 0;
}

.main-content {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

@media (max-width: 768px) {
  .page-title {
    font-size: 1.5rem;
  }
  
  .page-subtitle {
    font-size: 1rem;
  }
  
  .main-content {
    padding: 1rem 0;
  }
}
</style>