<template>
  <div class="multi-select-wrapper" ref="wrapperRef" :class="[theme, { 'dark-mode': theme === 'dark' }]">
    <div class="multi-select-trigger" @click="toggleDropdown" :class="{ active: isOpen }">
      <div class="selected-display">
        <span v-if="selectedValues.length === 0" class="placeholder-text">{{ placeholder }}</span>
        <div v-else class="selected-items-display">
          <span v-for="value in selectedValues" :key="value" class="selected-item-tag">
            {{ getOptionLabel(value) }}
            <button type="button" @click.stop="removeItem(value)" class="remove-item-btn">×</button>
          </span>
        </div>
      </div>
      <div class="dropdown-indicator" :class="{ rotated: isOpen }">
        ▼
      </div>
    </div>
    
    <div v-if="isOpen" class="dropdown-options">
      <div 
        v-for="option in options" 
        :key="option.value"
        class="dropdown-option"
        :class="{ selected: selectedValues.includes(option.value) }"
        @click="toggleItem(option.value)"
      >
        <div class="custom-checkbox" :class="{ checked: selectedValues.includes(option.value) }">
          <!-- 使用简单的背景色变化来表示选中状态 -->
        </div>
        <span class="option-text">{{ option.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  options: {
    type: Array,
    required: true
  },
  placeholder: {
    type: String,
    default: 'Select options...'
  },
  theme: {
    type: String,
    default: 'light' // 'light' or 'dark'
  }
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const wrapperRef = ref(null)

const selectedValues = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const getOptionLabel = (value) => {
  const option = props.options.find(opt => opt.value === value)
  return option ? option.label : value
}

const toggleDropdown = () => {
  isOpen.value = !isOpen.value
}

const toggleItem = (value) => {
  const currentValues = [...selectedValues.value]
  const index = currentValues.indexOf(value)
  
  if (index > -1) {
    currentValues.splice(index, 1)
  } else {
    currentValues.push(value)
  }
  
  selectedValues.value = currentValues
}

const removeItem = (value) => {
  const currentValues = selectedValues.value.filter(v => v !== value)
  selectedValues.value = currentValues
}

const handleClickOutside = (event) => {
  // 修复事件处理逻辑 - 使用正确的元素引用
  if (wrapperRef.value && !wrapperRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.multi-select-wrapper {
  position: relative;
  width: 100%;
}

.multi-select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.3s ease;
  min-height: 50px;
  box-sizing: border-box;
}

.multi-select-trigger:hover {
  border-color: #3fbbc0;
}

.multi-select-trigger.active {
  border-color: #3fbbc0;
  box-shadow: 0 0 0 3px rgba(63, 187, 192, 0.2);
}

.selected-display {
  flex: 1;
  display: flex;
  align-items: center;
  min-height: 20px;
}

.placeholder-text {
  color: #999;
  font-size: 1rem;
}

.selected-items-display {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  width: 100%;
  align-items: center;
}

.selected-item-tag {
  display: inline-flex;
  align-items: center;
  background: linear-gradient(45deg, #3fbbc0, #1071fb);
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
  gap: 6px;
  white-space: nowrap;
}

.remove-item-btn {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  padding: 0;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.remove-item-btn:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.dropdown-indicator {
  color: #666;
  transition: transform 0.3s ease;
  font-size: 12px;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dropdown-indicator.rotated {
  transform: rotate(180deg);
}

.dropdown-options {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  border: 1px solid #ddd;
  border-top: none;
  border-radius: 0 0 8px 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-height: 200px;
  overflow-y: auto;
}

.dropdown-option {
  display: flex;
  align-items: center;
  padding: 10px 15px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  gap: 10px;
}

.dropdown-option:hover {
  background-color: #f8f9fa;
}

.dropdown-option.selected {
  background-color: rgba(63, 187, 192, 0.1);
}

.dropdown-option input[type="checkbox"] {
   margin: 0;
   cursor: pointer;
 }

 .custom-checkbox {
    width: 16px;
    height: 16px;
    border: 2px solid #ddd;
    border-radius: 3px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    background: white;
    flex-shrink: 0;
    position: relative;
  }
  
  .custom-checkbox.checked {
    background-color: #3fbbc0;
    border-color: #3fbbc0;
    color: white;
  }
  
  .custom-checkbox.checked::after {
  content: '\f00c';
  font-family: 'Font Awesome 6 Free';
  font-weight: 900;
  color: white;
  font-size: 10px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

 .custom-checkbox svg {
    color: white;
  }
  
  .checkmark {
    color: white;
    font-size: 12px;
    font-weight: bold;
    line-height: 1;
  }
  
  .checkmark-icon {
    width: 8px;
    height: 4px;
    border-left: 2px solid white;
    border-bottom: 2px solid white;
    transform: rotate(-45deg);
    margin-top: 2px;
  }

.option-text {
  font-size: 0.95rem;
  color: #2c3e50;
}

/* 滚动条样式 */
.dropdown-options::-webkit-scrollbar {
  width: 6px;
}

.dropdown-options::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.dropdown-options::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.dropdown-options::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Dark Mode Styles */
.multi-select-wrapper.dark-mode .multi-select-trigger {
  background: rgba(15, 23, 42, 0.9);
  border-color: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.multi-select-wrapper.dark-mode .multi-select-trigger:hover {
  border-color: #38bdf8;
}

.multi-select-wrapper.dark-mode .multi-select-trigger.active {
  border-color: #38bdf8;
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
}

.multi-select-wrapper.dark-mode .placeholder-text {
  color: #94a3b8;
}

.multi-select-wrapper.dark-mode .dropdown-indicator {
  color: #94a3b8;
}

.multi-select-wrapper.dark-mode .dropdown-options {
  background: rgba(30, 41, 59, 0.95);
  backdrop-filter: blur(10px);
  border-color: rgba(255, 255, 255, 0.2);
}

.multi-select-wrapper.dark-mode .dropdown-option {
  color: #f1f5f9;
}

.multi-select-wrapper.dark-mode .dropdown-option:hover {
  background-color: rgba(56, 189, 248, 0.1);
}

.multi-select-wrapper.dark-mode .dropdown-option.selected {
  background-color: rgba(56, 189, 248, 0.2);
}

.multi-select-wrapper.dark-mode .option-text {
  color: #f1f5f9;
}

.multi-select-wrapper.dark-mode .custom-checkbox {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.3);
}

.multi-select-wrapper.dark-mode .custom-checkbox.checked {
  background-color: #38bdf8;
  border-color: #38bdf8;
}

.multi-select-wrapper.dark-mode .selected-item-tag {
  background: rgba(56, 189, 248, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(56, 189, 248, 0.3);
}

.multi-select-wrapper.dark-mode .remove-item-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: #f87171;
}

.multi-select-wrapper.dark-mode .dropdown-options::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}

.multi-select-wrapper.dark-mode .dropdown-options::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
}

.multi-select-wrapper.dark-mode .dropdown-options::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>