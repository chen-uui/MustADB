<template>
  <el-alert
    v-if="error"
    :title="error"
    type="error"
    :closable="true"
    @close="$emit('close')"
    class="error-alert"
  />
</template>

<script setup>
defineProps({
  error: {
    type: String,
    default: ''
  }
})

defineEmits(['close'])
</script>

<style scoped>
.error-alert {
  margin: 10px 0;
}
</style>
