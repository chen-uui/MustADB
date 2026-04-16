<template>
  <teleport to="body">
    <transition name="fade">
      <div v-if="visible" class="extraction-toast" :class="status">
        <span class="toast-icon" v-if="status==='success'">✅</span>
        <span class="toast-icon" v-if="status==='error'">❌</span>
        <span class="toast-icon" v-if="status==='progress'">⏳</span>
        <span>{{ message }}</span>
        <button v-if="closable" class="close-btn" @click="visible=false">×</button>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, watch, defineExpose } from 'vue'

const visible = ref(false)
const message = ref('')
const status = ref('info')  // 'success' | 'error' | 'progress'
const closable = ref(false)
let timer = null

defineExpose({ showToast })

function showToast(msg, type = 'info', options = {}) {
  message.value = msg
  status.value = type
  closable.value = !!options.closable
  visible.value = true
  if (timer) clearTimeout(timer)
  const duration = options.duration ?? (type === 'progress' ? 120000 : 3200)
  if (type !== 'progress') {
    timer = setTimeout(() => { visible.value = false }, duration)
  }
}
</script>

<style scoped>
.extraction-toast {
  position: fixed;
  top: 64px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  min-width: 280px;
  max-width: 90vw;
  padding: 16px 28px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgba(65, 84, 241, 0.18);
  font-weight: 600;
  color: #333;
  font-size: 1.02rem;
  display:flex;
  align-items: center;
  gap: 14px;
  border-left: 6px solid #4154f1;
  animation: pop-in 0.2s;
}
.toast-icon {
  font-size: 1.24em;
}
.extraction-toast.success { border-left-color: #38c172; }
.extraction-toast.error { border-left-color: #e3342f; }
.extraction-toast.progress { border-left-color: #ffb700; }
.close-btn {
  background: transparent;
  border:none;
  font-size:1.1em;
  margin-left:10px;
  cursor:pointer;
}
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.25s;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
@keyframes pop-in {
  from { transform: translateY(-40px) scale(0.93); opacity: 0.6; }
  to   { transform: translateY(0) scale(1); opacity: 1; }
}
</style>
