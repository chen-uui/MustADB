<template>
  <button
    :class="[
      'astro-button',
      `btn-${variant}`,
      `btn-${size}`,
      'relative overflow-hidden',
      'font-medium transition-all duration-300',
      'rounded-lg',
      'glow-hover',
      className
    ]"
    @click="handleClick"
  >
    <span class="relative z-10 flex items-center justify-center gap-2">
      <slot></slot>
    </span>
    <span v-if="ripples.length > 0" class="ripple-container">
      <span
        v-for="ripple in ripples"
        :key="ripple.id"
        class="ripple"
        :style="{
          left: ripple.x + 'px',
          top: ripple.y + 'px'
        }"
      ></span>
    </span>
  </button>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'ghost'].includes(value)
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },
  className: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['click'])

const ripples = ref([])
let rippleId = 0

const handleClick = (event) => {
  // Create ripple effect
  const button = event.currentTarget
  const rect = button.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  const newRipple = {
    id: rippleId++,
    x,
    y
  }

  ripples.value.push(newRipple)

  // Remove ripple after animation
  setTimeout(() => {
    ripples.value = ripples.value.filter(r => r.id !== newRipple.id)
  }, 600)

  emit('click', event)
}
</script>

<style scoped>
.astro-button {
  border: 1px solid transparent;
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}

.astro-button:active {
  transform: scale(0.98);
}

/* Sizes */
.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

.btn-md {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
}

.btn-lg {
  padding: 1rem 2rem;
  font-size: 1.125rem;
}

/* Variants */
.btn-primary {
  background: linear-gradient(135deg, #6C5CE7 0%, #00CEC9 100%);
  background-size: 200% 200%;
  color: white;
  box-shadow: 0 4px 15px rgba(108, 92, 231, 0.4);
}

.btn-primary:hover {
  background-position: 100% 0;
  box-shadow: 0 6px 20px rgba(108, 92, 231, 0.6), 0 0 30px rgba(0, 206, 201, 0.3);
  transform: translateY(-2px);
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-color: rgba(255, 255, 255, 0.1);
  color: white;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(108, 92, 231, 0.5);
  box-shadow: 0 4px 15px rgba(108, 92, 231, 0.3);
}

.btn-ghost {
  background: transparent;
  color: rgba(255, 255, 255, 0.8);
  border-color: transparent;
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.05);
  color: white;
}

/* Ripple Effect */
.ripple-container {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
}

.ripple {
  position: absolute;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
  transform: translate(-50%, -50%) scale(0);
  animation: ripple-animation 0.6s ease-out;
}

@keyframes ripple-animation {
  to {
    transform: translate(-50%, -50%) scale(20);
    opacity: 0;
  }
}
</style>
