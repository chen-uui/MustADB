<template>
  <div v-if="visible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>{{ item?.type === 'pdf' ? 'PDF Details' : 'Meteorite Details' }}</h3>
        <button class="btn-close" @click="$emit('close')">x</button>
      </div>
      <div class="modal-body">
        <div v-if="item?.type === 'pdf'" class="detail-content">
          <div class="detail-section">
            <h4>Document Information</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <label>Title</label>
                <span>{{ item.title }}</span>
              </div>
              <div class="detail-item">
                <label>Filename</label>
                <span>{{ item.filename }}</span>
              </div>
              <div class="detail-item">
                <label>Authors</label>
                <span>{{ item.authors || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>Year</label>
                <span>{{ item.year || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>Journal</label>
                <span>{{ item.journal || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>File Size</label>
                <span>{{ formatFileSize(item.file_size) }}</span>
              </div>
              <div class="detail-item">
                <label>Pages</label>
                <span>{{ item.page_count || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>Uploaded By</label>
                <span>{{ item.uploaded_by || 'Anonymous' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="item" class="detail-content">
          <div class="detail-section">
            <h4>Meteorite Information</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <label>Name</label>
                <span>{{ item.name }}</span>
              </div>
              <div class="detail-item">
                <label>Classification</label>
                <span>{{ item.classification || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>Discovery Location</label>
                <span>{{ item.discovery_location || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>Origin</label>
                <span>{{ item.origin || '-' }}</span>
              </div>
              <div class="detail-item">
                <label>Confidence Score</label>
                <span>{{ formatConfidence(item.confidence_score) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-success" @click="$emit('approve')">
          <i class="bi bi-check"></i>
          Approve
        </button>
        <button class="btn btn-danger" @click="$emit('reject')">
          <i class="bi bi-x"></i>
          Reject
        </button>
        <button class="btn btn-outline" @click="$emit('close')">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  item: {
    type: Object,
    default: null
  }
})

defineEmits(['close', 'approve', 'reject'])

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const index = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, index)) * 100) / 100 + ' ' + sizes[index]
}

const formatConfidence = (score) => {
  if (score === null || score === undefined) {
    return '-'
  }

  return `${(score * 100).toFixed(1)}%`
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.modal-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #e9ecef;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.detail-content {
  max-height: 60vh;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  color: #495057;
  border-bottom: 1px solid #e9ecef;
  padding-bottom: 8px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-item label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
  text-transform: uppercase;
}

.detail-item span {
  font-size: 14px;
  color: #495057;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-danger {
  background: #dc3545;
  color: white;
}

.btn-outline {
  background: white;
  color: #495057;
  border: 1px solid #ced4da;
}

.btn-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close:hover {
  color: #000;
}

@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
