<template>
  <div v-if="show" class="task-progress-bar">
    <div class="tpb-header">
      <span class="tpb-title">{{ title }}</span>
      <span class="tpb-status">{{ statusText }}</span>
    </div>
    <div class="tpb-bar">
      <div class="tpb-fill" :style="{ width: (percentage || 0) + '%' }"></div>
    </div>
    <div class="tpb-stats">
      <span>进度: {{ (percentage || 0).toFixed(1) }}%</span>
      <span v-if="total !== undefined">处理: {{ processed || 0 }}/{{ total }}</span>
      <span>成功: {{ successful || 0 }}</span>
      <span>失败: {{ failed || 0 }}</span>
    </div>
    <div v-if="hasControls" class="tpb-actions">
      <button
        v-if="canPause"
        class="tpb-btn"
        :disabled="isPauseDisabled"
        @click="controls.onPause"
      >
        暂停
      </button>
      <button
        v-if="canResume"
        class="tpb-btn"
        :disabled="isResumeDisabled"
        @click="controls.onResume"
      >
        恢复
      </button>
      <button
        v-if="canStop"
        class="tpb-btn tpb-btn-danger"
        :disabled="isStopDisabled"
        @click="controls.onStop"
      >
        停止
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TaskProgressBar',
  props: {
    show: { type: Boolean, default: false },
    percentage: { type: Number, default: 0 },
    processed: { type: Number, default: 0 },
    total: { type: Number, default: undefined },
    successful: { type: Number, default: 0 },
    failed: { type: Number, default: 0 },
    statusText: { type: String, default: '处理中' },
    title: { type: String, default: '任务进度' },
    controls: {
      type: Object,
      default: null
    }
  },
  computed: {
    hasControls () {
      return !!(this.controls && (this.controls.onPause || this.controls.onResume || this.controls.onStop))
    },
    canPause () {
      return this.controls && this.controls.onPause && !this.controls.isPaused
    },
    canResume () {
      return this.controls && this.controls.onResume && this.controls.isPaused
    },
    canStop () {
      return this.controls && this.controls.onStop
    },
    isPauseDisabled () {
      return this.controls?.disablePause || this.controls?.loading === 'pause'
    },
    isResumeDisabled () {
      return this.controls?.disableResume || this.controls?.loading === 'resume'
    },
    isStopDisabled () {
      return this.controls?.disableStop || this.controls?.loading === 'stop'
    }
  }
}
</script>

<style scoped>
.task-progress-bar { padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }
.tpb-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.tpb-title { font-weight: 600; }
.tpb-status { font-size: 12px; color: #6b7280; }
.tpb-bar { position: relative; height: 8px; background: #f3f4f6; border-radius: 9999px; overflow: hidden; }
.tpb-fill { position: absolute; left: 0; top: 0; bottom: 0; background: #3b82f6; transition: width 0.3s ease; }
.tpb-stats { display: grid; grid-template-columns: repeat(4, auto); gap: 12px; margin-top: 8px; font-size: 12px; color: #374151; }
.tpb-actions { display: flex; gap: 8px; margin-top: 12px; }
.tpb-btn { padding: 6px 14px; font-size: 13px; border-radius: 20px; border: 1px solid #3b82f6; background: #fff; color: #3b82f6; cursor: pointer; transition: all 0.2s ease; }
.tpb-btn:hover:not(:disabled) { background: #3b82f6; color: #fff; }
.tpb-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.tpb-btn-danger { border-color: #ef4444; color: #ef4444; }
.tpb-btn-danger:hover:not(:disabled) { background: #ef4444; color: #fff; }
@media (max-width: 640px) { .tpb-stats { grid-template-columns: repeat(2, auto); } }
</style>
