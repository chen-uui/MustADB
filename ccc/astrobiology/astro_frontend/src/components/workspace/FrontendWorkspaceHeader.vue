<template>
  <header class="workspace-header">
    <div class="header-container">
      <div class="header-left">
        <div class="logo">
          <div class="logo-icon-wrapper">
            <svg class="logo-icon" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7v10c0 5.55 3.84 10 9 9 5.16-1 9-5.45 9-9V7l-10-5z"/>
              <path d="M12 8v8M8 12h8"/>
            </svg>
          </div>
          <div class="logo-text-wrapper">
            <span class="logo-text">MUSTADB Workspace</span>
            <span class="logo-subtitle">Intelligent Research Platform</span>
          </div>
        </div>
      </div>
      
      <div class="header-center">
        <nav class="tab-navigation">
          <button 
            v-for="tab in tabs"
            :key="tab.id"
            :class="['tab-button', { active: activeTab === tab.id }]"
            @click="$emit('tab-change', tab.id)"
            :title="tab.description"
          >
            <i :class="tab.icon"></i>
            <span class="tab-label">{{ tab.label }}</span>
          </button>
        </nav>
      </div>
      
      <div class="header-right">
        <button class="home-button" @click="$emit('navigate', '/')">
          <i class="bi bi-house"></i>
          <span>Home</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
const props = defineProps({
  activeTab: {
    type: String,
    default: 'meteorite-search'
  }
})

const emit = defineEmits(['tab-change', 'navigate'])

// Frontend tabs - only search and Q&A
const tabs = [
  {
    id: 'meteorite-search',
    label: 'Meteorite Search',
    icon: 'bi bi-search',
    description: 'Search meteorite data'
  },
  {
    id: 'qa',
    label: 'AI Q&A',
    icon: 'bi bi-chat-dots',
    description: 'AI-powered question and answer system'
  }
]
</script>

<style scoped>
.workspace-header {
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding: 0;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 100;
}

.workspace-header::after {
  display: none;
}

.header-container {
  max-width: 1920px;
  margin: 0 auto;
  padding: 1rem 2rem;
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
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: scale(1.02);
}

.logo-icon-wrapper {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
}

.logo:hover .logo-icon-wrapper {
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
  transform: rotate(5deg);
}

.logo-icon {
  color: white;
  width: 24px;
  height: 24px;
}

.logo-text-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.logo-text {
  font-size: 1.25rem;
  font-weight: 700;
  color: white;
  line-height: 1.2;
}

.logo-subtitle {
  font-size: 0.75rem;
  color: #94a3b8;
  font-weight: 500;
  letter-spacing: 0.05em;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.tab-navigation {
  display: flex;
  gap: 0.5rem;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  background: transparent;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
}

.tab-button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.tab-button.active {
  background: rgba(56, 189, 248, 0.2);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.tab-button i {
  font-size: 1.125rem;
}

.tab-label {
  font-size: 0.9375rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-shrink: 0;
}

.home-button {
  display: flex;
  align-items: center;
  gap: .5rem;
  padding: .6rem 1rem;
  border: none;
  border-radius: 9999px;
  background: linear-gradient(135deg, #3fbbc0 0%, #1071fb 100%);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(16,113,251,.18);
  transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
}

.home-button:hover { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(16,113,251,.25); filter: brightness(1.05); }
.home-button i { font-size: 1rem; }
.home-button span { font-weight: 600; }

.admin-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  color: #64748b;
  font-weight: 500;
  font-size: 0.9375rem;
}

.admin-button:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%);
  border-color: #3b82f6;
  color: #3b82f6;
  transform: translateY(-2px);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* 响应式设计 */
@media (max-width: 1199px) {
  .tab-navigation {
    flex-wrap: wrap;
  }
  
  .tab-button {
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
  }
}

@media (max-width: 767px) {
  .workspace-header {
    flex-direction: column;
    gap: 1rem;
  }
  
  .header-center {
    order: 1;
  }
  
  .header-left,
  .header-right {
    order: 2;
  }
  
  .tab-navigation {
    flex-direction: column;
    width: 100%;
  }
  
  .tab-button {
    justify-content: center;
  }
}
</style>

