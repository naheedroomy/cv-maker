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
      <span v-if="job.applied" class="applied-badge">Applied</span>
    </div>
    <div class="session-bottom">
      <span class="created-date">{{ formatDate(job.updated_at) }}</span>
      <div class="status-indicators">
        <!-- CV status -->
        <span v-if="job.status === 'complete'" class="indicator indicator--done" title="CV ready">CV</span>
        <span v-else-if="job.status === 'pending' || job.status === 'running'" class="indicator indicator--pending" title="CV generating">CV</span>
        <span v-else-if="job.status === 'failed'" class="indicator indicator--failed" title="CV failed">CV</span>

        <!-- Cover letter status -->
        <span v-if="job.cover_letter_text && job.cover_letter_text.length > 0" class="indicator indicator--done" title="Cover letter ready">L</span>
        <span v-else-if="job.cover_letter_text === ''" class="indicator indicator--pending" title="Cover letter generating">L</span>
      </div>
    </div>
  </router-link>
</template>

<style scoped>
.session-entry {
  display: block;
  padding: 10px 16px;
  min-height: 48px;
  text-decoration: none;
  color: #111827;
  cursor: pointer;
  transition: background-color 100ms ease;
}
.session-entry:hover {
  background: #f9fafb;
}
.session-entry--active {
  background: #f3f4f6;
  border-left: 3px solid #2563eb;
}
.session-entry--applied {
  background: #f0fdf4;
  border-left: 3px solid #22c55e;
}
.session-entry--applied:hover {
  background: #dcfce7;
}
.session-entry--active.session-entry--applied {
  background: #dcfce7;
  border-left: 3px solid #2563eb;
}
.session-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.company-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.applied-badge {
  font-size: 9px;
  font-weight: 600;
  color: #15803d;
  background: #bbf7d0;
  border-radius: 3px;
  padding: 1px 5px;
  flex-shrink: 0;
}
.session-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 3px;
}
.created-date {
  font-size: 11px;
  color: #9ca3af;
}
.status-indicators {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.indicator {
  font-size: 9px;
  font-weight: 700;
  border-radius: 3px;
  padding: 1px 4px;
  letter-spacing: 0.02em;
}
.indicator--done {
  color: #16a34a;
  background: #dcfce7;
}
.indicator--pending {
  color: #d97706;
  background: #fef3c7;
}
.indicator--failed {
  color: #dc2626;
  background: #fee2e2;
}
</style>
