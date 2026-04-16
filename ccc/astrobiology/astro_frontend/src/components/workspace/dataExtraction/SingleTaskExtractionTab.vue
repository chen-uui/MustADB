<template>
  <div class="single-task-wrapper">
    <SingleTaskExtractionView />
  </div>
</template>

<script setup>
import SingleTaskExtractionView from '@/components/workspace/dataExtraction/singleTask/SingleTaskExtractionView.vue'
</script>

<style scoped>
.single-task-wrapper {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #f6f8ff 0%, #eef1ff 100%);
}
</style>

