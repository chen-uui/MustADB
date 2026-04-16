<template>
  <div v-if="visible" class="modal-overlay" @click="$emit('close')">
    <div class="modal-content reject-dialog" @click.stop>
      <div class="modal-header">
        <h3>
          <i class="bi bi-exclamation-triangle"></i>
          Confirm Rejection
        </h3>
        <button class="btn-close" @click="$emit('close')">x</button>
      </div>
      <div class="modal-body">
        <div class="reject-warning">
          <p v-if="isBatch">
            You are about to reject <strong>{{ item?.count || 0 }}</strong> selected items.
          </p>
          <template v-else>
            <p>You are about to reject the following item:</p>
            <div class="reject-item-info">
              <strong>{{ displayTitle }}</strong>
              <span class="item-type">{{ item?.type?.toUpperCase() }}</span>
            </div>
          </template>
        </div>
        <div class="reject-reason-section">
          <label for="reject-reason">
            <i class="bi bi-pencil"></i>
            Rejection Reason <span class="required">*</span>
          </label>
          <textarea
            id="reject-reason"
            :value="reason"
            placeholder="Enter the rejection reason"
            rows="4"
            class="reject-reason-input"
            maxlength="500"
            @input="$emit('update:reason', $event.target.value)"
          ></textarea>
          <div class="char-count">{{ reason.length }}/500</div>
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-outline" @click="$emit('close')">Cancel</button>
        <button class="btn btn-danger" :disabled="!reason.trim()" @click="$emit('confirm')">
          <i class="bi bi-x-circle"></i>
          Confirm Reject
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  item: {
    type: Object,
    default: null
  },
  reason: {
    type: String,
    default: ''
  }
})

defineEmits(['close', 'confirm', 'update:reason'])

const isBatch = computed(() => props.item?.type === 'batch')
const displayTitle = computed(() => {
  if (!props.item) {
    return '-'
  }

  return props.item.type === 'pdf' ? props.item.title : props.item.name
})
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
  max-width: 500px;
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
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  color: #1a1a1a;
}

.modal-header h3 i {
  color: #ffc107;
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

.reject-warning {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 20px;
}

.reject-warning p {
  margin: 0 0 12px 0;
  color: #856404;
  font-weight: 500;
}

.reject-item-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.reject-item-info strong {
  color: #1a1a1a;
  font-size: 15px;
  flex: 1;
}

.item-type {
  background: #ffc107;
  color: #856404;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.reject-reason-section {
  margin-top: 20px;
}

.reject-reason-section label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #495057;
  margin-bottom: 8px;
  font-size: 14px;
}

.required {
  color: #dc3545;
}

.reject-reason-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ced4da;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.reject-reason-input:focus {
  outline: none;
  border-color: #3fbbc0;
  box-shadow: 0 0 0 3px rgba(63, 187, 192, 0.1);
}

.char-count {
  text-align: right;
  font-size: 12px;
  color: #6c757d;
  margin-top: 4px;
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

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  color: #6c757d;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #f0f0f0;
  color: #495057;
}
</style>
