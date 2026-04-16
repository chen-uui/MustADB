<template>
  <div v-if="loading" class="loading-overlay">
    <div class="loading-content">
      <div class="loading-spinner">
        <div class="spinner"></div>
      </div>
      <div class="loading-text">
        <h3>{{ title }}</h3>
        <p>{{ message }}</p>
        <div v-if="progress !== null" class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <div v-if="details" class="loading-details">
          <p>{{ details }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '处理中...'
  },
  message: {
    type: String,
    default: '请稍候，正在处理您的请求'
  },
  progress: {
    type: Number,
    default: null
  },
  details: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.loading-content {
  background: white;
  border-radius: 1rem;
  padding: 2rem;
  text-align: center;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  max-width: 400px;
  width: 90%;
}

.loading-spinner {
  margin-bottom: 1.5rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text h3 {
  margin: 0 0 0.5rem 0;
  color: #2c3e50;
  font-size: 1.25rem;
}

.loading-text p {
  margin: 0 0 1rem 0;
  color: #6c757d;
  font-size: 1rem;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin: 1rem 0;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007bff, #0056b3);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.loading-details {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 0.5rem;
  font-size: 0.9rem;
  color: #495057;
}

.loading-details p {
  margin: 0;
}
</style>
