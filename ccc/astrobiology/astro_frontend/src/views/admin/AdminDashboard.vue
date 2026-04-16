<template>
  <div class="admin-dashboard">
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" style="background: #3b82f6;">
          <i class="bi bi-file-earmark-text"></i>
        </div>
        <div class="stat-content">
          <h3>{{ stats.documents || 0 }}</h3>
          <p>文档总数</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #10b981;">
          <i class="bi bi-database"></i>
        </div>
        <div class="stat-content">
          <h3>{{ stats.meteorites || 0 }}</h3>
          <p>陨石数据</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #f59e0b;">
          <i class="bi bi-gear"></i>
        </div>
        <div class="stat-content">
          <h3>{{ stats.extractions || 0 }}</h3>
          <p>提取任务</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: #ef4444;">
          <i class="bi bi-activity"></i>
        </div>
        <div class="stat-content">
          <h3>{{ stats.systemHealth || '正常' }}</h3>
          <p>系统状态</p>
        </div>
      </div>
    </div>
    
    <div class="quick-actions">
      <h3>快速操作</h3>
      <div class="actions-grid">
        <button class="action-btn" @click="$emit('navigate', '/admin/documents')">
          <i class="bi bi-file-earmark-plus"></i>
          <span>上传文档</span>
        </button>
        <button class="action-btn" @click="$emit('navigate', '/admin/extraction')">
          <i class="bi bi-gear"></i>
          <span>数据提取</span>
        </button>
        <button class="action-btn" @click="$emit('navigate', '/admin/meteorite-management')">
          <i class="bi bi-database"></i>
          <span>数据管理</span>
        </button>
        <button class="action-btn" @click="$emit('navigate', '/admin/system-health')">
          <i class="bi bi-activity"></i>
          <span>系统监控</span>
        </button>
        <button class="action-btn" @click="$emit('navigate', '/admin/unified-review')">
          <i class="bi bi-clipboard-check"></i>
          <span>审核中心</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const emit = defineEmits(['navigate'])

const stats = ref({
  documents: 0,
  meteorites: 0,
  extractions: 0,
  systemHealth: '正常'
})

onMounted(async () => {
  // TODO: 加载统计数据
  // 这里可以调用API获取实际数据
})
</script>

<style scoped>
.admin-dashboard {
  max-width: 1400px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.5rem;
}

.stat-content h3 {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: #1e293b;
}

.stat-content p {
  margin: 0.25rem 0 0 0;
  color: #64748b;
  font-size: 0.875rem;
}

.quick-actions {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.quick-actions h3 {
  margin: 0 0 1.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  color: #475569;
}

.action-btn:hover {
  border-color: #3b82f6;
  background: #f8fafc;
  color: #3b82f6;
  transform: translateY(-2px);
}

.action-btn i {
  font-size: 2rem;
}

.action-btn span {
  font-weight: 500;
  font-size: 0.9375rem;
}
</style>

