<script setup lang="ts">
withDefaults(defineProps<{ title: string; lines?: number }>(), { lines: 3 })
</script>

<template>
  <div class="skeleton-section">
    <h3 class="skeleton-title">{{ title }}</h3>
    <p class="skeleton-label">Generating...</p>
    <div aria-hidden="true" class="skeleton-lines">
      <div
        v-for="n in lines"
        :key="n"
        class="skeleton-line"
        :style="{ width: n === lines ? '60%' : '100%' }"
      ></div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-section {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 24px;
  margin-bottom: 48px;
}

.skeleton-title {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 4px;
}

.skeleton-label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 16px;
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 16px;
  background: #e2e8f0;
  border-radius: 4px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}
</style>
