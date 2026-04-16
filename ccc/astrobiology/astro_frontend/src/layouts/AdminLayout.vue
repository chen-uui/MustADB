<template>
  <div class="admin-layout">
    <div class="admin-sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <i class="bi bi-shield-check"></i>
          <span>管理后台</span>
        </div>
      </div>
      <nav class="sidebar-nav">
        <a 
          v-for="item in menuItems" 
          :key="item.path"
          :class="['nav-item', { active: currentPath === item.path }]"
          @click="navigateTo(item.path)"
        >
          <i :class="item.icon"></i>
          <span>{{ item.label }}</span>
        </a>
      </nav>
      <div class="sidebar-footer">
        <a class="nav-item" @click="navigateToHome">
          <i class="bi bi-house"></i>
          <span>返回前台</span>
        </a>
      </div>
    </div>
    <div class="admin-content">
      <div class="admin-body">
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessageBox } from 'element-plus'

const props = defineProps({
  currentPath: {
    type: String,
    default: '/admin'
  }
})

const emit = defineEmits(['navigate'])

const menuItems = [
  {
    path: '/admin/documents',
    label: '文档管理',
    icon: 'bi bi-file-earmark-text'
  },
  {
    path: '/admin/extraction',
    label: '数据提取',
    icon: 'bi bi-gear'
  },
  {
    path: '/admin/direct-processing',
    label: '直接处理',
    icon: 'bi bi-lightning'
  },
  {
    path: '/admin/meteorite-management',
    label: '陨石数据管理',
    icon: 'bi bi-database'
  },
  {
    path: '/admin/unified-review',
    label: '审核中心',
    icon: 'bi bi-clipboard-check'
  },
  {
    path: '/admin/system-health',
    label: '系统健康',
    icon: 'bi bi-activity'
  }
]

const currentPageTitle = computed(() => {
  const item = menuItems.find(m => m.path === props.currentPath)
  return item ? item.label : '管理后台'
})

const navigateTo = (path) => {
  emit('navigate', path)
}

const navigateToHome = () => {
  emit('navigate', '/')
}

const handleLogout = async () => {
  try {
    await ElMessageBox.confirm('确定要登出吗？', '退出登录', {
      type: 'warning'
    })
    try {
      // 调用后端登出API（可选，主要用于删除服务器端token）
      const { apiMethods } = await import('@/utils/apiClient.js')
      try {
        await apiMethods.post('/api/pdf/auth/logout/')
      } catch (error) {
        console.warn('登出API调用失败，但继续清除本地token:', error)
      }
    } catch (error) {
      console.warn('无法导入apiMethods，直接清除本地token')
    }

    localStorage.removeItem('token')
    localStorage.removeItem('admin_logged_in')
    window.location.reload()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.warn('登出确认失败:', error)
    }
  }
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e5e9f0 100%);
}

.admin-sidebar {
  width: 280px;
  background: linear-gradient(180deg, #0f172a 0%, #1e293b 50%, #334155 100%);
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(255, 255, 255, 0.05);
  position: relative;
  z-index: 10;
}

/* 添加侧边栏顶部装饰线 */
.admin-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
}

.sidebar-header {
  padding: 2rem 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(10px);
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 1.375rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.logo:hover {
  transform: scale(1.02) translateX(4px);
}

.logo i {
  font-size: 1.75rem;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 2px 8px rgba(59, 130, 246, 0.3));
}

.sidebar-nav {
  flex: 1;
  padding: 1.5rem 0;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 自定义滚动条 */
.sidebar-nav::-webkit-scrollbar {
  width: 6px;
}

.sidebar-nav::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 3px;
}

.sidebar-nav::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

.sidebar-nav::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  margin: 0.25rem 1rem;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 12px;
  border-left: 3px solid transparent;
  position: relative;
  font-weight: 500;
  font-size: 0.9375rem;
}

/* 导航项背景高光效果 */
.nav-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
  border-radius: 12px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.nav-item:hover::before {
  opacity: 1;
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.15));
  color: white;
  border-left-color: #3b82f6;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  transform: translateX(4px);
}

.nav-item.active::before {
  opacity: 1;
}

.nav-item i {
  font-size: 1.25rem;
  width: 24px;
  text-align: center;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.nav-item:hover i,
.nav-item.active i {
  transform: scale(1.1) rotate(5deg);
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(10px);
}

.admin-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
}

.admin-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 内容区滚动条优化 */
.admin-body::-webkit-scrollbar {
  width: 8px;
}

.admin-body::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
}

.admin-body::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
}

.admin-body::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

/* 响应式优化 */
@media (max-width: 1024px) {
  .admin-sidebar {
    width: 240px;
  }
}
</style>
