<template>
  <header class="workspace-header">
    <div class="header-container">
      <div class="header-left">
        <div class="logo">
          <div class="logo-icon-wrapper">
            <i class="bi bi-shield-check"></i>
          </div>
          <div class="logo-text-wrapper">
            <span class="logo-text">管理后台</span>
            <span class="logo-subtitle">Admin Workspace</span>
          </div>
        </div>
      </div>
      
      <div class="header-center">
        <nav class="tab-navigation">
          <button 
            v-for="tab in tabs"
            :key="tab.id"
            :class="['tab-button', { active: activeTab === tab.id }]"
            @click="handleTabClick(tab.id)"
            :title="tab.description"
          >
            <i :class="tab.icon"></i>
            <span class="tab-label">{{ tab.label }}</span>
          </button>
        </nav>
      </div>
      
      <div class="header-right">
        <span class="user-info">管理员</span>
        <button class="logout-btn" @click="handleLogout" title="登出">
          <i class="bi bi-box-arrow-right"></i>
          <span>登出</span>
        </button>
        <button class="home-button" @click="$emit('navigate', '/')">
          <i class="bi bi-house"></i>
          <span>返回前台</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'documents'
  }
})

const emit = defineEmits(['tab-change', 'navigate'])

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

// 处理标签点击
const handleTabClick = (tabId) => {
  // 所有标签都通过导航事件处理，统一导航到对应页面
  emit('navigate', `/admin/${tabId}`)
}

// 后台标签页配置
const tabs = [
  {
    id: 'documents',
    label: '文档管理',
    icon: 'bi bi-file-earmark-text',
    description: '上传和管理PDF文档'
  },
  {
    id: 'extraction',
    label: '数据提取',
    icon: 'bi bi-gear',
    description: '智能提取陨石数据'
  },
  {
    id: 'direct-processing',
    label: '直接处理',
    icon: 'bi bi-lightning',
    description: 'AI直接分析文档'
  },
  {
    id: 'meteorite-management',
    label: '陨石数据管理',
    icon: 'bi bi-database',
    description: '管理已审核通过的陨石数据'
  },
  {
    id: 'unified-review',
    label: '审核中心',
    icon: 'bi bi-clipboard-check',
    description: '审核PDF和陨石数据'
  },
  {
    id: 'system-health',
    label: '系统健康',
    icon: 'bi bi-activity',
    description: '系统监控和健康检查'
  }
]
</script>

<style scoped>
.workspace-header {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding: 0;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12), inset 0 -1px 0 rgba(255, 255, 255, 0.05);
  position: relative;
  z-index: 100;
}

/* 顶部装饰线 */
.workspace-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
}

.header-container {
  max-width: 1920px;
  margin: 0 auto;
  padding: 1.25rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}

.header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 1rem;
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.logo:hover {
  transform: scale(1.02);
}

.logo-icon-wrapper {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 14px;
  box-shadow: 0 8px 24px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  color: white;
  font-size: 1.625rem;
}

.logo:hover .logo-icon-wrapper {
  box-shadow: 0 12px 32px rgba(59, 130, 246, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.3);
  transform: rotate(5deg) scale(1.05);
}

.logo-text-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.logo-text {
  font-size: 1.375rem;
  font-weight: 700;
  color: white;
  line-height: 1.2;
  text-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.logo-subtitle {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.tab-navigation {
  display: flex;
  gap: 0.625rem;
  background: rgba(255, 255, 255, 0.05);
  padding: 0.5rem;
  border-radius: 16px;
  backdrop-filter: blur(10px);
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 1.5rem;
  border: none;
  background: transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
  font-size: 0.9375rem;
  position: relative;
  overflow: hidden;
}

/* 标签按钮背景高光 */
.tab-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
  opacity: 0;
  transition: opacity 0.3s ease;
  border-radius: 12px;
}

.tab-button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.tab-button:hover::before {
  opacity: 1;
}

.tab-button.active {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.tab-button.active::before {
  opacity: 0;
}

.tab-button i {
  font-size: 1.125rem;
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.tab-button:hover i,
.tab-button.active i {
  transform: scale(1.1);
}

.tab-label {
  font-size: 0.9375rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  flex-shrink: 0;
}

.user-info {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.875rem;
  padding: 0.625rem 1.125rem;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  font-weight: 500;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.logout-btn:hover {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.logout-btn:active {
  transform: translateY(0);
}

.logout-btn i {
  font-size: 1rem;
}

.home-button {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: white;
  font-weight: 500;
  font-size: 0.9375rem;
  backdrop-filter: blur(10px);
}

.home-button:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.home-button:active {
  transform: translateY(0);
}

/* 响应式设计 */
@media (max-width: 1199px) {
  .tab-navigation {
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  
  .tab-button {
    padding: 0.625rem 1.125rem;
    font-size: 0.875rem;
  }
}

@media (max-width: 767px) {
  .workspace-header {
    padding-bottom: 1rem;
  }
  
  .header-container {
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 1.5rem;
  }
  
  .header-center {
    width: 100%;
    order: 1;
  }
  
  .header-left,
  .header-right {
    order: 2;
  }
  
  .tab-navigation {
    width: 100%;
    flex-direction: column;
  }
  
  .tab-button {
    justify-content: center;
    width: 100%;
  }
}
</style>
