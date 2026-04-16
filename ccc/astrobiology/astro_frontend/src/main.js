import { createApp } from 'vue'
import { createStore } from 'vuex'
import App from './App.vue'
// Commented out old theme CSS - using new Astrobiology theme
// import './assets/css/style.css'
// import './assets/css/animations.css'
import './styles/workspace.css'
import './assets/css/astro-theme.css' // New Astrobiology theme
import store from './store'

// Import Bootstrap CSS
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'

// Import Bootstrap JS
import 'bootstrap/dist/js/bootstrap.bundle.min.js'

// Import Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// Create Vue app
const app = createApp(App)

// 使用Vuex
app.use(store)

// 使用Element Plus
app.use(ElementPlus)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 注册滚动动画指令
app.directive('scroll-animate', {
  mounted(el, binding) {
    const animationClass = binding.value || 'animate-fadeIn'

    // 创建IntersectionObserver来检测元素是否进入视口
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          // 添加动画类
          entry.target.classList.add('animate-on-scroll', animationClass)
          entry.target.classList.add('visible')

          // 停止观察
          observer.unobserve(entry.target)
        }
      })
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    })

    // 开始观察元素
    observer.observe(el)

    // 保存observer引用以便清理
    el._observer = observer
  },
  unmounted(el) {
    // 清理observer
    if (el._observer) {
      el._observer.disconnect()
      delete el._observer
    }
  }
})

// Mount the app
app.mount('#app')

// Print admin panel URL in console (for development/debugging)
if (import.meta.env.DEV) {
  const adminUrl = `${window.location.origin}/admin`
  const backendUrl = import.meta.env.VITE_BACKEND_URL || `http://${import.meta.env.VITE_BACKEND_HOST || 'localhost'}:${import.meta.env.VITE_BACKEND_PORT || '8000'}`

  console.log('%c🔐 Admin Panel', 'color: #3b82f6; font-size: 16px; font-weight: bold;')
  console.log(`%cAccess the admin panel at: ${adminUrl}`, 'color: #64748b; font-size: 12px;')
  console.log(`%cBackend API at: ${backendUrl}`, 'color: #64748b; font-size: 12px;')
  console.log('%cNote: Admin access is restricted to authorized personnel only.', 'color: #ef4444; font-size: 11px; font-style: italic;')
}