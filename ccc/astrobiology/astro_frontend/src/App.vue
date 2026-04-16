<template>
  <div id="app" class="relative min-h-screen">
    <!-- Layer 0: Star Field Background -->
    <StarFieldBackground />
    <!-- Layer 1: Gradient Overlay -->
    <div class="fixed inset-0 bg-gradient-to-br from-nebula-purple/10 via-transparent to-space-black pointer-events-none z-[1]"></div>
    
    <!-- Layer 10+: Main Content -->
    <div class="relative z-10">
        <!-- 后台管理页面 -->
        <template v-if="isAdminPage">
          <!-- 检查登录状态 -->
          <AdminLogin v-if="!isLoggedIn" @login-success="handleLoginSuccess" />
          <!-- 后台布局（已登录） -->
          <AdminLayout v-else :current-path="currentPath" @navigate="handleNavigate">
            <!-- 后台工作台（默认显示文档管理） -->
            <AdminWorkspace v-if="currentPage === 'admin' || currentPage === 'admin-workspace'" :active-tab="getActiveTabFromPath()" @navigate="handleNavigate" />
            <!-- 系统健康监控页面（后台） -->
            <SystemHealthView v-else-if="currentPage === 'system-health'" @navigate="handleNavigate" />
            <!-- 统一审核页面（后台） -->
            <UnifiedReview v-else-if="currentPage === 'unified-review'" @navigate="handleNavigate" />
          </AdminLayout>
        </template>
    
    <!-- 前台页面 -->
    <template v-else>
      <!-- 主页面（天体生物学数据库系统） -->
      <div v-if="currentPage === 'home'">
        <TopBar />
        <Header />
        <Hero />
        <WorkspaceEntrance />
        <PDFUpload />
        <About />
        <Contact />
        <Footer />
      </div>
      
      <!-- 陨石搜索页面（二级页面） -->
      <div v-else-if="currentPage === 'meteorite-search'">
        <TopBar />
        <Header />
        <MeteoriteSearch />
        <Footer />
      </div>

      <!-- PDF详情页面（三级页面） -->
      <PDFDetail v-else-if="currentPage === 'pdf-detail'" 
                  :document-id="currentDocumentId"
                  @navigate="handleNavigate" />


      <!-- 回收站管理页面 -->
      <RecycleBinManagement v-else-if="currentPage === 'recycle-bin'" @navigate="handleNavigate" />

      <!-- 前台工作台（只包含智能问答） -->
      <FrontendWorkspace v-else-if="currentPage === 'workspace'" @navigate="handleNavigate" />

      <!-- 返回顶部按钮 -->
      <a href="#" class="back-to-top d-flex align-items-center justify-content-center"
         @click="scrollToTop"
         v-show="isScrolled">
        <i class="bi bi-arrow-up-short"></i>
      </a>
    </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useStore } from 'vuex'
import StarFieldBackground from './components/ui/StarFieldBackground.vue'
import TopBar from './components/TopBar.vue'
import Header from './components/Header.vue'
import Hero from './components/Hero.vue'
import WorkspaceEntrance from './components/WorkspaceEntrance.vue'
import PDFUpload from './components/PDFUpload.vue'
import About from './components/About.vue'
import Contact from './components/Contact.vue'
import Footer from './components/Footer.vue'

import PDFDetail from './views/PDFDetail.vue'
import RecycleBinManagement from './views/RecycleBinManagement.vue'
import SystemHealthView from './views/SystemHealthView.vue'
import FrontendWorkspace from './views/FrontendWorkspace.vue'
import MeteoriteSearch from './views/MeteoriteSearch.vue'
import AdminLayout from './layouts/AdminLayout.vue'
import AdminDashboard from './views/admin/AdminDashboard.vue'
import AdminWorkspace from './views/admin/AdminWorkspace.vue'
import AdminLogin from './views/admin/AdminLogin.vue'
import UnifiedReview from './views/UnifiedReview.vue'

const store = useStore()
const isScrolled = ref(false)
const currentPage = ref('home')
const currentDocumentId = ref(null)
const currentPath = ref('/admin')

const normalizeDocumentId = (value) => {
  if (value === null || value === undefined) {
    return null
  }
  const text = String(value).trim()
  return text || null
}

// 登录状态（使用ref而不是computed，以便手动触发更新）
const isLoggedIn = ref(false)

// 检查登录状态的函数
const checkLoginStatus = () => {
  const token = typeof window !== 'undefined' ? window.localStorage.getItem('token') : null
  const adminLoggedIn = typeof window !== 'undefined' ? window.localStorage.getItem('admin_logged_in') : null
  isLoggedIn.value = !!(token && adminLoggedIn === 'true')
}

// 初始化时检查登录状态
onMounted(() => {
  checkLoginStatus()
  // 监听storage变化（用于跨标签页同步）
  window.addEventListener('storage', checkLoginStatus)
})

onUnmounted(() => {
  window.removeEventListener('storage', checkLoginStatus)
})

// 处理登录成功
const handleLoginSuccess = async () => {
  // 强制更新登录状态
  checkLoginStatus()
  // 优化：移除生产环境的console.log
  if (import.meta.env.DEV) {
    console.log('登录成功，已切换到后台')
  }
  
  // 等待Vue更新DOM
  await nextTick()
  
  // 确保显示后台页面
  if (currentPage.value !== 'admin' && currentPage.value !== 'admin-workspace') {
    currentPage.value = 'admin-workspace'
    currentPath.value = '/admin/documents'
    store.dispatch('workspace/switchTab', 'documents')
  }
}

  // 判断是否为后台页面
  const isAdminPage = computed(() => {
    return currentPage.value === 'admin' ||
           currentPage.value === 'admin-workspace' ||
           currentPage.value === 'system-health' ||
           currentPage.value === 'unified-review' ||
           (
             window.location.pathname.startsWith('/admin') &&
             !window.location.pathname.startsWith('/admin/pdf-detail/')
           )
  })

  // 从路径获取活动标签（用于导航栏高亮）
  const getActiveTabFromPath = () => {
    const path = currentPath.value
    if (path === '/admin/unified-review') return 'unified-review'
    if (path === '/admin/system-health') return 'system-health'
    if (path.startsWith('/admin/documents')) return 'documents'
    if (path.startsWith('/admin/extraction')) return 'extraction'
    if (path.startsWith('/admin/direct-processing')) return 'direct-processing'
    if (path.startsWith('/admin/meteorite-management')) return 'meteorite-management'
    return store.getters['workspace/activeTab'] || 'documents'
  }

// 处理页面导航
const handleNavigate = (route, data = {}) => {
  // 处理路由字符串（如 '/admin', '/admin/documents'）
  if (typeof route === 'string' && route.startsWith('/')) {
    if (route === '/') {
      currentPage.value = 'home'
      currentPath.value = '/'
        } else if (route === '/admin' || route === '/admin/') {
          // 默认跳转到文档管理
          currentPage.value = 'admin-workspace'
          currentPath.value = '/admin/documents'
          store.dispatch('workspace/switchTab', 'documents')
    } else if (route.startsWith('/admin/pdf-detail/')) {
      currentPage.value = 'pdf-detail'
      currentDocumentId.value = normalizeDocumentId(route.split('/').pop())
      currentPath.value = route
    } else if (route.startsWith('/admin/')) {
      const path = route.replace('/admin/', '')
      if (path === 'documents' || path === 'extraction' || path === 'direct-processing' || path === 'meteorite-management') {
        currentPage.value = 'admin-workspace'
        currentPath.value = route
        // 触发tab切换
        store.dispatch('workspace/switchTab', path)
      } else if (path === 'unified-review') {
        currentPage.value = 'unified-review'
        currentPath.value = route
      } else if (path === 'system-health') {
        currentPage.value = 'system-health'
        currentPath.value = route
      } else {
        currentPage.value = 'admin'
        currentPath.value = '/admin'
      }
    } else if (route === '/workspace') {
      currentPage.value = 'workspace'
      currentPath.value = '/workspace'
    } else if (route === '/meteorite-search') {
      currentPage.value = 'meteorite-search'
      currentPath.value = '/meteorite-search'
    } else {
      // 兼容旧的页面导航方式
      currentPage.value = route
    }
  } else {
    // 兼容旧的页面导航方式
    currentPage.value = route
    if (data.documentId) {
      currentDocumentId.value = normalizeDocumentId(data.documentId)
    }
  }
  updateURL(currentPage.value, data)
  window.scrollTo(0, 0)
}

// 滚动到顶部
const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleScroll = () => {
  isScrolled.value = window.scrollY > 100
}

// 监听URL变化以支持浏览器前进后退
const handlePopState = () => {
  const path = window.location.pathname
  currentPath.value = path
  
      if (path.startsWith('/admin/pdf-detail/')) {
        const id = path.split('/').pop()
        currentDocumentId.value = normalizeDocumentId(id)
        currentPage.value = 'pdf-detail'
      } else if (path.startsWith('/admin')) {
        if (path === '/admin' || path === '/admin/') {
          // 默认跳转到文档管理
          currentPage.value = 'admin-workspace'
          currentPath.value = '/admin/documents'
          store.dispatch('workspace/switchTab', 'documents')
        } else if (path.startsWith('/admin/documents') || 
                   path.startsWith('/admin/extraction') || 
                   path.startsWith('/admin/direct-processing') || 
                   path.startsWith('/admin/meteorite-management')) {
          currentPage.value = 'admin-workspace'
          const tab = path.split('/').pop()
          store.dispatch('workspace/switchTab', tab)
        } else if (path === '/admin/system-health') {
          currentPage.value = 'system-health'
        } else if (path === '/admin/unified-review') {
          currentPage.value = 'unified-review'
        } else {
          // 默认跳转到文档管理
          currentPage.value = 'admin-workspace'
          currentPath.value = '/admin/documents'
          store.dispatch('workspace/switchTab', 'documents')
        }
  } else if (path.startsWith('/pdf-detail/')) {
    const id = path.split('/').pop()
    currentDocumentId.value = normalizeDocumentId(id)
    currentPage.value = 'pdf-detail'
  } else if (path === '/recycle-bin') {
    currentPage.value = 'recycle-bin'
  } else if (path === '/system-health') {
    currentPage.value = 'system-health'
  } else if (path === '/workspace') {
    currentPage.value = 'workspace'
  } else if (path === '/meteorite-search') {
    currentPage.value = 'meteorite-search'
  } else {
    currentPage.value = 'home'
  }
}

// 更新URL
const updateURL = (page, data = {}) => {
  if (page === 'home') {
    history.pushState({}, '', '/')
  } else if (page === 'admin' || page === 'admin-workspace') {
    const activeTab = store.getters['workspace/activeTab'] || 'documents'
    history.pushState({}, '', `/admin/${activeTab}`)
  } else if (page === 'pdf-detail') {
    history.pushState({}, '', `/pdf-detail/${normalizeDocumentId(data.documentId)}`)
  } else if (page === 'recycle-bin') {
    history.pushState({}, '', '/recycle-bin')
  } else if (page === 'system-health') {
    history.pushState({}, '', '/admin/system-health')
  } else if (page === 'unified-review') {
    history.pushState({}, '', '/admin/unified-review')
  } else if (page === 'workspace') {
    history.pushState({}, '', '/workspace')
  } else if (page === 'meteorite-search') {
    history.pushState({}, '', '/meteorite-search')
  }
}

onMounted(() => {
  // 监听自定义导航事件
  window.addEventListener('navigate-to-pdf', (event) => {
    const page = event.detail.page
    // 如果是路径字符串，直接使用handleNavigate
    if (typeof page === 'string' && page.startsWith('/')) {
      handleNavigate(page)
    } else {
      handleNavigate(page)
    }
  })
  
  // 添加popstate事件监听器以支持浏览器前进后退
  window.addEventListener('popstate', handlePopState)
  
  // 添加滚动监听
  window.addEventListener('scroll', handleScroll)
  
  // 初始化时处理当前URL
  handlePopState()
})

onUnmounted(() => {
  window.removeEventListener('popstate', handlePopState)
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style>
/* Global styles will be imported from assets */
.back-to-top {
  position: fixed;
  right: 15px;
  bottom: 15px;
  z-index: 99999;
  background: #4154f1;
  width: 40px;
  height: 40px;
  border-radius: 4px;
  transition: all 0.4s;
}

.back-to-top i {
  font-size: 24px;
  color: #fff;
  line-height: 0;
}

.back-to-top:hover {
  background: #6776f4;
  color: #fff;
}
</style>
