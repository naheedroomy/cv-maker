<script setup lang="ts">
import type { JobStatus } from '@/types'
defineProps<{ status: JobStatus }>()
</script>

<template>
  <span :class="['badge', `badge--${status}`]" :aria-label="`Status: ${status}`">
    {{ status }}
  </span>
</template>

<style scoped>
.badge {
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 600;
  display: inline-block;
  text-transform: capitalize;
}
.badge--pending,
.badge--running {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}
.badge--complete {
  background: var(--color-success-secondary);
  color: var(--color-success-primary);
}
.badge--failed {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}
.badge--cancelled {
  background: var(--color-surface-2);
  color: var(--color-text-secondary);
}
</style>
