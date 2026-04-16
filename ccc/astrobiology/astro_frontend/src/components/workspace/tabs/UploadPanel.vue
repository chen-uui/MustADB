<template>
  <div class="simple-upload-section">
    <div class="upload-area" @click="triggerFileUpload" @dragover.prevent @drop.prevent="handleFileDrop">
      <div class="upload-icon">📄</div>
      <h4>上传要提取的文档</h4>
      <p style="color: #666">支持PDF、DOC、DOCX</p>
      <input ref="fileInput" type="file" multiple accept=".pdf,.doc,.docx" @change="onFileSelect" style="display:none;" />
    </div>
    <div v-if="localFiles.length > 0" class="selected-files">
      <h4>已选择文件（{{ localFiles.length }}）</h4>
      <div class="file-list">
        <div v-for="(file, index) in localFiles" :key="index" class="file-item">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatFileSize(file.size) }}</span>
          <button @click="removeFile(index)" class="remove-btn">×</button>
        </div>
      </div>
    </div>
    <div class="form-actions">
      <button @click="emitFiles" class="btn-primary" :disabled="localFiles.length === 0 || isExtracting">
        <span v-if="isExtracting">正在提取…</span>
        <span v-else>一键智能提取</span>
      </button>
      <button v-if="localFiles.length > 0" @click="clearFiles" class="btn-secondary">清空文件</button>
    </div>
    <div v-if="isExtracting" style="text-align:center;margin-top:14px;color:#4154f1">数据提取中…</div>
  </div>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue'

const props = defineProps({
  modelValue: Array,
  isExtracting: Boolean
})
const emit = defineEmits(['update:modelValue', 'triggerExtract'])
const localFiles = ref([])

watch(() => props.modelValue, v => {
  if (v && v.length !== localFiles.value.length) {
    localFiles.value = [...v]
  }
})

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024;
  if (bytes < k) return bytes + ' B';
  const sizes = ['KB','MB','GB'];
  let i = Math.floor(Math.log(bytes)/Math.log(k));
  return (bytes/Math.pow(k,i)).toFixed(2)+' '+sizes[i-1];
}

function triggerFileUpload() {
  document.querySelector('input[type="file"]').click()
}
function onFileSelect(event) {
  const files = Array.from(event.target.files)
  localFiles.value = [...localFiles.value, ...files]
  emit('update:modelValue', localFiles.value)
}
function handleFileDrop(event) {
  const files = Array.from(event.dataTransfer.files)
  localFiles.value = [...localFiles.value, ...files]
  emit('update:modelValue', localFiles.value)
}
function removeFile(index) {
  localFiles.value.splice(index, 1)
  emit('update:modelValue', localFiles.value)
}
function clearFiles() {
  localFiles.value = []
  emit('update:modelValue', localFiles.value)
}
function emitFiles() {
  emit('update:modelValue', localFiles.value)
  emit('triggerExtract')
}
</script>

<style scoped>
.simple-upload-section {
  margin-bottom: 2rem;
}
</style>
