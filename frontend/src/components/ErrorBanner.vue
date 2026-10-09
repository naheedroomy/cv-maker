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
  background: var(--color-error-bg);
  border-left: 4px solid var(--color-error-border);
  padding: 16px;
  border-radius: 0 6px 6px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.error-text {
  color: var(--color-error-text);
  font-size: 14px;
  margin: 0;
}
.retry-btn {
  background: none;
  border: none;
  color: var(--color-accent-primary);
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  min-height: 40px;
  padding: 8px 4px;
}
.retry-btn:hover {
  text-decoration: underline;
}
</style>
