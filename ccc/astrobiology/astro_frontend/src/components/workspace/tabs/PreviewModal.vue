<template>
  <teleport to="body">
    <transition name="fade">
      <div v-if="visible" class="preview-modal-overlay">
        <div class="preview-modal-content">
          <div class="modal-header">
            <h3>{{ title }}</h3>
            <button class="close-btn" @click="close">×</button>
          </div>
          <div class="modal-body">
            <div class="select-controls">
              <button @click="selectAll" class="btn-secondary">全选</button>
              <button @click="deselectAll" class="btn-secondary">全不选</button>
              <button @click="exportSelected" class="btn-primary" :disabled="selected.length === 0">导出选中项</button>
              <span style="margin-left:22px;">选中：{{ selected.length }} / {{ data.length }}</span>
            </div>
            <div class="preview-list">
              <div class="preview-item" v-for="(item, idx) in data" :key="idx" :class="{ selected: selected.includes(idx) }" @click="toggle(idx)">
                <input type="checkbox" :checked="selected.includes(idx)" @change.stop="toggle(idx)" />
                <span>{{ item.meteorite_data?.name || '未命名陨石' }}</span>
                <span v-if="item.confidence_score">置信度: {{ (item.confidence_score*100).toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="close">取消</button>
            <button class="btn-primary" :disabled="selected.length===0||loading" @click="confirm">{{ loading ? '保存中...' : '确认保存 (' + selected.length + ')' }}</button>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue'
const props = defineProps({
  visible: Boolean,
  data: Array,
  title: String,
  loading: Boolean,
  selected: Array
})
const emit = defineEmits(['update:visible','update:selected','confirm','export'])

function toggle(idx) {
  const isSel = props.selected.includes(idx)
  let arr = props.selected.slice()
  if(isSel) arr = arr.filter(i => i!==idx)
  else arr.push(idx)
  emit('update:selected', arr)
}
function selectAll(){ emit('update:selected', props.data.map((_,ix)=>ix)) }
function deselectAll(){ emit('update:selected', []) }
function close(){ emit('update:visible', false) }
function confirm(){ emit('confirm') }
function exportSelected(){ emit('export', props.selected.slice()) }
</script>

<style scoped>
.preview-modal-overlay {
  position:fixed; inset:0; background:rgba(0,0,0,0.54); z-index:1000;
  display: flex; align-items: center; justify-content: center;
}
.preview-modal-content {
  background:white; border-radius:12px; min-width:366px; max-width:96vw; max-height:90vh; overflow:auto; box-shadow:0 6px 30px rgba(101,101,191,0.18);
  display:flex; flex-direction: column;
}
.modal-header { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #eee; padding:18px;}
.modal-header h3 { margin:0; }
.close-btn {background:none;border:none;font-size:18px;cursor:pointer;}
.modal-body{padding:18px;}
.select-controls{margin-bottom:10px;display:flex;gap:12px;align-items:center;}
.preview-list{max-height:50vh;overflow:auto;}
.preview-item { padding:10px;background: #fafbfc;margin-bottom:4px;border-radius:6px;cursor:pointer;display:flex;align-items:center;gap:10px;transition:.18s; }
.preview-item.selected { background: #e3f2fd; }
.preview-item input[type="checkbox"] {margin-right:5px;}
.modal-footer{display:flex;justify-content:flex-end;gap:14px;border-top:1px solid #eee;padding:16px;}
</style>
