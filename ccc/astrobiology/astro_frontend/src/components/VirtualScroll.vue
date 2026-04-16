<template>
  <div class="virtual-scroll-container" :style="{ height: containerHeight + 'px' }" @scroll="handleScroll">
    <div class="virtual-scroll-spacer" :style="{ height: totalHeight + 'px' }">
      <div class="virtual-scroll-content" :style="{ transform: `translateY(${offsetY}px)` }">
        <slot :items="visibleItems" :startIndex="startIndex"></slot>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

export default {
  name: 'VirtualScroll',
  props: {
    items: {
      type: Array,
      required: true
    },
    itemHeight: {
      type: Number,
      default: 200
    },
    containerHeight: {
      type: Number,
      default: 600
    },
    overscan: {
      type: Number,
      default: 5
    }
  },
  setup(props) {
    const scrollTop = ref(0)
    
    const totalHeight = computed(() => props.items.length * props.itemHeight)
    
    const startIndex = computed(() => {
      return Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - props.overscan)
    })
    
    const endIndex = computed(() => {
      const visibleCount = Math.ceil(props.containerHeight / props.itemHeight)
      return Math.min(
        props.items.length - 1,
        startIndex.value + visibleCount + props.overscan * 2
      )
    })
    
    const visibleItems = computed(() => {
      return props.items.slice(startIndex.value, endIndex.value + 1)
    })
    
    const offsetY = computed(() => startIndex.value * props.itemHeight)
    
    const handleScroll = (event) => {
      scrollTop.value = event.target.scrollTop
    }
    
    return {
      scrollTop,
      totalHeight,
      startIndex,
      endIndex,
      visibleItems,
      offsetY,
      handleScroll
    }
  }
}
</script>

<style scoped>
.virtual-scroll-container {
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

.virtual-scroll-spacer {
  position: relative;
}

.virtual-scroll-content {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
}
</style>
