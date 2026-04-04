<script setup lang="ts">
defineProps<{ message: string }>()
defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="error-banner" role="alert">
    <p class="error-text">
      <strong>Something went wrong.</strong> {{ message }}
    </p>
    <button class="retry-btn" @click="$emit('retry')">Try again</button>
  </div>
</template>

<style scoped>
.error-banner {
  background: #fee2e2;
  border-left: 4px solid #dc2626;
  padding: 16px;
  border-radius: 0 6px 6px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.error-text {
  color: #7f1d1d;
  font-size: 14px;
  margin: 0;
}
.retry-btn {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  padding: 0;
}
.retry-btn:hover {
  text-decoration: underline;
}
</style>
