<template>
  <transition name="fade">
    <div v-if="show" :class="['notification-bar', type]">
      <span class="icon">
        <template v-if="type === 'success'">✅</template>
        <template v-else-if="type === 'error'">❌</template>
        <template v-else-if="type === 'warning'">⚠️</template>
        <template v-else>ℹ️</template>
      </span>
      <div class="content">
        <strong v-if="title">{{ title }}</strong>
        <span>{{ message }}</span>
      </div>
      <button class="close-btn" @click="emit('close')">×</button>
    </div>
  </transition>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'
const props = defineProps({
  show: Boolean,
  type: {
    type: String,
    default: 'info' // 'success', 'error', 'warning', 'info'
  },
  message: String,
  title: String
})
const emit = defineEmits(['close'])
</script>

<style scoped>
.notification-bar {
  position: fixed;
  top: 30px;
  left: 50%;
  transform: translateX(-50%);
  min-width: 350px;
  max-width: 90vw;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 6px 32px rgba(0,0,0,0.13);
  padding: 16px 24px 16px 48px;
  display: flex;
  align-items: center;
  z-index: 1400;
  font-size: 1rem;
  gap: 20px;
  border-left: 6px solid #4154f1;
}
.notification-bar.success { border-left-color: #28a745; }
.notification-bar.error { border-left-color: #dc3545; }
.notification-bar.warning { border-left-color: #ffc107; }
.notification-bar.info { border-left-color: #4154f1; }
.icon { font-size: 1.5rem; margin-right: 10px; }
.content { flex: 1; }
.close-btn {
  background: none;
  border: none;
  font-size: 1.2rem;
  color: #888;
  cursor: pointer;
  margin-left: 20px;
}
.fade-enter-active, .fade-leave-active { transition: opacity .25s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
