<template>
  <div v-if="show" class="advanced-settings-panel">
    <h4>高级提取参数</h4>
    <div class="form-item">
      <label>关键词模板：</label>
      <input v-model="settings.keywords" type="text" placeholder="如：有机物, 基础信息" style="width: 80%" />
    </div>
    <div class="form-item">
      <label>提取字段：</label>
      <input v-model="settings.fields" type="text" placeholder="如：分类, 污染" style="width: 80%" />
    </div>
    <div class="form-item">
      <label>相关性阈值：</label>
      <input v-model="settings.threshold" type="number" min="0" max="1" step="0.01" style="width: 100px;" />
    </div>
    <slot></slot> <!-- 允许插入额外设置 -->
    <div style="margin-top: 1rem; text-align:right;">
      <button class="btn-secondary" @click="$emit('close')">收起高级</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue'

const props = defineProps({
  modelValue: Object,
  show: Boolean
})
const emit = defineEmits(['update:modelValue', 'close'])

const settings = ref({
  keywords: '',
  fields: '',
  threshold: 0.4
})

watch(() => props.modelValue, v => {
  if (v) Object.assign(settings.value, v)
})

watch(settings, v => {
  emit('update:modelValue', { ...settings.value })
}, { deep: true })
</script>

<style scoped>
.advanced-settings-panel {
  border:1px solid #eee;
  border-radius:8px;
  padding:1.5rem 1rem;
  background:#fcfcff;
  margin-bottom:2rem;
}
.form-item { margin-bottom: 1rem; }
label { width: 90px; display:inline-block; }
</style>
