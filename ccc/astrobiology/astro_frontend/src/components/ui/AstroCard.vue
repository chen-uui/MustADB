<template>
  <div
    :class="[
      'astro-card',
      'relative overflow-hidden',
      'bg-white/5 backdrop-blur-md',
      'border border-white/10',
      'rounded-2xl',
      'transition-all duration-500',
      'hover:bg-white/10 hover:border-nebula-purple/30',
      'hover:shadow-[0_8px_32px_rgba(108,92,231,0.3)]',
      'hover:-translate-y-1',
      'group',
      className
    ]"
  >
    <!-- Shimmer overlay -->
    <div class="absolute inset-0 shimmer-overlay opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
    
    <!-- Inner glow -->
    <div class="absolute inset-[1px] rounded-2xl bg-gradient-to-br from-white/5 via-transparent to-transparent pointer-events-none"></div>
    
    <!-- Content -->
    <div :class="['relative z-10', padding ? `p-${padding}` : 'p-6']">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
defineProps({
  className: {
    type: String,
    default: ''
  },
  padding: {
    type: String,
    default: '6'
  }
})
</script>

<style scoped>
.astro-card {
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.shimmer-overlay {
  background: linear-gradient(
    120deg,
    transparent 30%,
    rgba(108, 92, 231, 0.1) 50%,
    transparent 70%
  );
  background-size: 200% 100%;
  animation: shimmer-slide 3s infinite;
}

@keyframes shimmer-slide {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}
</style>
