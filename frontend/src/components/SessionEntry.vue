<script setup lang="ts">
import type { JobResponse } from '@/types'

defineProps<{ job: JobResponse; active: boolean }>()

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <router-link
    :to="`/jobs/${job.id}`"
    class="session-entry"
    :class="{ 'session-entry--active': active, 'session-entry--applied': job.applied }"
    :aria-current="active ? 'page' : undefined"
  >
    <div class="session-top">
      <span class="company-name">{{ job.company_name }}</span>
    </div>
    <div class="session-bottom">
      <span class="created-date">{{ formatDate(job.updated_at) }}</span>
      <div class="status-indicators">
        <!-- CV status -->
        <span v-if="job.status === 'complete'" class="indicator indicator--done" aria-label="CV ready" title="CV ready">CV</span>
        <span v-else-if="job.status === 'pending' || job.status === 'running'" class="indicator indicator--pending" aria-label="CV generating" title="CV generating">CV</span>
        <span v-else-if="job.status === 'failed'" class="indicator indicator--failed" aria-label="CV failed" title="CV failed">CV</span>

        <!-- Cover letter status -->
        <span v-if="job.cover_letter_text && job.cover_letter_text.length > 0" class="indicator indicator--done" aria-label="Cover letter ready" title="Cover letter ready">L</span>
        <span v-else-if="job.cover_letter_text === ''" class="indicator indicator--pending" aria-label="Cover letter generating" title="Cover letter generating">L</span>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.session-entry {
  display: block;
  padding: 11px 22px;
  border-left: 3px solid transparent;
  border-bottom: 1px solid var(--color-border);
  min-height: 48px;
  text-decoration: none;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background-color 100ms ease, border-color 100ms ease;
}
.session-entry:hover {
  background: var(--color-surface-2);
}
.session-entry--active {
  background: var(--color-surface-2);
  border-left-color: var(--color-accent-primary);
}
.session-entry--applied {
  background-color: var(--color-success-secondary);
  border-left-color: var(--color-success-primary);
}
.session-entry--applied:hover {
  /* A slightly lighter shade for hover on applied entries */
  background-color: color-mix(in srgb, var(--color-success-secondary) 80%, var(--color-surface-1) 20%);
}
.session-entry--active.session-entry--applied {
  border-left-color: var(--color-accent-primary);
}
.session-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 3px;
}
.company-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.created-date {
  font-size: 11px;
  color: var(--color-text-tertiary);
}
.status-indicators {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
}
.indicator {
  font-size: 9px;
  font-weight: 700;
  border-radius: 3px;
  padding: 1px 4px;
  letter-spacing: 0.02em;
  text-align: center;
  min-width: 18px;
}
.indicator--done { color: var(--color-success-primary); background: var(--color-success-secondary); }
.indicator--pending { color: var(--color-warning-text); background: var(--color-warning-bg); }
.indicator--failed { color: var(--color-error-text); background: var(--color-error-bg); }
</style>
