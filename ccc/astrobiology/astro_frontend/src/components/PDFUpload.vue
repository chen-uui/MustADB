<template>
  <section id="pdf-upload" class="py-20 relative">
    <div class="container mx-auto px-6 relative z-10">
      <div class="text-center mb-16 animate-fade-in-up">
        <h2 class="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
          Upload Research Papers
        </h2>
        <p class="text-lg text-white/60 max-w-2xl mx-auto font-light">
          Share your research papers with our community. Uploaded papers will be reviewed before being added to the database.
        </p>
      </div>

      <div class="max-w-3xl mx-auto">
        <AstroCard class="!p-0 overflow-hidden">
          <!-- Upload Area -->
          <div 
            class="relative p-12 text-center transition-all duration-300 border-2 border-dashed border-white/10 hover:border-starlight-blue/50 hover:bg-white/5 group cursor-pointer"
            :class="{ 'bg-starlight-blue/5 border-starlight-blue': isDragging, 'opacity-50 pointer-events-none': isUploading }"
            @drop="handleDrop"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @click="triggerFileInput"
          >
            <input 
              ref="fileInput"
              type="file" 
              accept=".pdf"
              multiple
              @change="handleFileSelect"
              class="hidden"
            />
            
            <div v-if="!isUploading" class="space-y-4">
              <div class="w-20 h-20 mx-auto rounded-full bg-white/5 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                <i class="bi bi-cloud-upload text-4xl text-starlight-blue"></i>
              </div>
              <h3 class="text-xl font-semibold text-white">Drag & Drop PDF Files</h3>
              <p class="text-white/50">or click to browse</p>
              <p class="text-xs text-white/30 uppercase tracking-wider">Max file size: 50MB</p>
            </div>
            
            <!-- Progress Bar -->
            <div v-else class="space-y-4">
              <div class="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                <div 
                  class="h-full bg-gradient-to-r from-nebula-purple to-starlight-blue transition-all duration-300"
                  :style="{ width: uploadProgress + '%' }"
                ></div>
              </div>
              <p class="text-starlight-blue font-mono">Uploading... {{ uploadProgress }}%</p>
            </div>
          </div>

          <!-- File List -->
          <div v-if="selectedFiles.length > 0 && !isUploading" class="border-t border-white/10 bg-black/20 p-6">
            <div class="flex justify-between items-center mb-4">
              <h4 class="text-white font-medium">Selected Files ({{ selectedFiles.length }})</h4>
              <button @click.stop="clearFiles" class="text-xs text-red-400 hover:text-red-300 transition-colors">
                Clear All
              </button>
            </div>
            
            <div class="space-y-2 max-h-60 overflow-y-auto custom-scrollbar mb-6">
              <div 
                v-for="(file, index) in selectedFiles" 
                :key="index" 
                class="flex items-center justify-between p-3 rounded bg-white/5 border border-white/5 hover:border-white/20 transition-colors"
              >
                <div class="flex items-center gap-3 overflow-hidden">
                  <i class="bi bi-file-pdf text-red-400 text-xl"></i>
                  <div class="flex flex-col min-w-0">
                    <span class="text-sm text-white truncate">{{ file.name }}</span>
                    <span class="text-xs text-white/40 font-mono">{{ formatFileSize(file.size) }}</span>
                  </div>
                </div>
                <button @click.stop="removeFile(index)" class="text-white/30 hover:text-white transition-colors p-1">
                  <i class="bi bi-x-lg"></i>
                </button>
              </div>
            </div>
            
            <AstroButton variant="primary" block @click.stop="uploadFiles" :disabled="isUploading">
              <i class="bi bi-upload mr-2"></i>
              Upload {{ selectedFiles.length }} File(s)
            </AstroButton>
          </div>

          <!-- Results -->
          <div v-if="uploadResults.length > 0" class="border-t border-white/10 bg-black/20 p-6">
            <h4 class="text-white font-medium mb-4">Upload Results</h4>
            <div class="space-y-2 mb-6">
              <div 
                v-for="(result, index) in uploadResults" 
                :key="index" 
                class="flex items-center gap-3 p-3 rounded text-sm"
                :class="result.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'"
              >
                <i :class="result.success ? 'bi bi-check-circle' : 'bi bi-x-circle'"></i>
                <div class="flex flex-col">
                  <span class="font-medium">{{ result.filename }}</span>
                  <span class="opacity-80 text-xs">{{ result.message }}</span>
                </div>
              </div>
            </div>
            <AstroButton variant="secondary" block @click="clearResults">Close</AstroButton>
          </div>
        </AstroCard>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import { apiMethods } from '@/utils/apiClient.js'
import { getApiErrorMessage } from '@/utils/apiError'
import AstroCard from './ui/AstroCard.vue'
import AstroButton from './ui/AstroButton.vue'

const fileInput = ref(null)
const isDragging = ref(false)
const isUploading = ref(false)
const uploadProgress = ref(0)
const selectedFiles = ref([])
const uploadResults = ref([])

const triggerFileInput = () => {
  if (!isUploading.value) {
    fileInput.value?.click()
  }
}

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files)
  addFiles(files)
}

const handleDrop = (event) => {
  event.preventDefault()
  isDragging.value = false
  
  const files = Array.from(event.dataTransfer.files).filter(file => 
    file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')
  )
  
  addFiles(files)
}

const addFiles = (files) => {
  const maxSize = 50 * 1024 * 1024 // 50MB
  const validFiles = files.filter(file => {
    if (file.size > maxSize) {
      ElMessage.error(`文件 ${file.name} 超过 50MB 限制`)
      return false
    }
    return true
  })
  
  const existingNames = new Set(selectedFiles.value.map(f => f.name))
  const newFiles = validFiles.filter(file => !existingNames.has(file.name))
  
  selectedFiles.value.push(...newFiles)
}

const removeFile = (index) => {
  selectedFiles.value.splice(index, 1)
}

const clearFiles = () => {
  selectedFiles.value = []
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const uploadFiles = async () => {
  if (selectedFiles.value.length === 0) return
  
  isUploading.value = true
  uploadProgress.value = 0
  uploadResults.value = []
  
  const formData = new FormData()
  selectedFiles.value.forEach(file => {
    formData.append('files', file)
  })
  
  try {
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          uploadProgress.value = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
        }
      }
    }
    
    const response = await apiMethods.post(
      `/api/pdf/documents/user-upload/`,
      formData,
      config
    )
    
    if (response.data) {
      const results = response.data.results || []
      uploadResults.value = results.map(result => ({
        filename: result.filename || 'Unknown',
        success: result.success || false,
        message: result.success 
          ? 'Uploaded successfully. Awaiting review.'
          : result.message || result.error || 'Upload failed'
      }))
      
      if (results.every(r => r.success)) {
        setTimeout(() => {
          clearFiles()
        }, 3000)
      }
    }
  } catch (error) {
    console.error('Upload error:', error)
    uploadResults.value = selectedFiles.value.map(file => ({
      filename: file.name,
      success: false,
      message: getApiErrorMessage(error, 'Upload failed')
    }))
  } finally {
    isUploading.value = false
    uploadProgress.value = 0
  }
}

const clearResults = () => {
  uploadResults.value = []
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
