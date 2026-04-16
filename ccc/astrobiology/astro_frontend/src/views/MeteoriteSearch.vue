<template>
  <div class="page">
    <FrontendWorkspaceHeader :active-tab="'meteorite-search'" @tab-change="onTabChange" @navigate="onNavigate" />
    <section class="page-hero">
      <div class="hero-content">
        <h2>Meteorite Search</h2>
        <p>Filter and explore meteorite data with flexible criteria and fast results.</p>
      </div>
    </section>
    <div class="body">
      <MeteoriteSearchTab />
    </div>
  </div>
</template>

<script setup>
import { defineAsyncComponent } from 'vue'
import FrontendWorkspaceHeader from '@/components/workspace/FrontendWorkspaceHeader.vue'
const MeteoriteSearchTab = defineAsyncComponent(() => import('@/components/workspace/tabs/MeteoriteSearchTab.vue'))
const emit = defineEmits(['navigate'])
const onNavigate = (route) => emit('navigate', route)
const onTabChange = (tab) => {
  if (tab === 'qa') emit('navigate', '/intelligent-qa')
}
</script>

<style scoped>
.page { display: flex; flex-direction: column; background: linear-gradient(135deg, #f8fbff 0%, #eef2ff 100%); position: relative; }
.page::before { content:""; position:absolute; top:-120px; left:-120px; width:360px; height:360px; background: radial-gradient(closest-side, rgba(63,187,192,.18), transparent); filter: blur(8px); }
.page::after { content:""; position:absolute; bottom:-140px; right:-140px; width:420px; height:420px; background: radial-gradient(closest-side, rgba(16,113,251,.16), transparent); filter: blur(10px); }
.page-hero { background: linear-gradient(135deg, #eef2ff, #f8fafc); border-bottom: 1px solid #e2e8f0; }
.hero-content { max-width: 1100px; margin: 0 auto; padding: 1.25rem 2rem; }
.hero-content h2 { margin: 0; font-size: 1.6rem; font-weight: 700; color: #012970; }
.hero-content p { margin: .35rem 0 0; color: #64748b; }
.body { padding: 2rem; }
</style>
