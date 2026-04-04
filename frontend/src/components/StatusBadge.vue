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
  background: #fef3c7;
  color: #92400e;
}
.badge--complete {
  background: #dcfce7;
  color: #14532d;
}
.badge--failed {
  background: #fee2e2;
  color: #991b1b;
}
.badge--cancelled {
  background: #f3f4f6;
  color: #374151;
}
</style>
