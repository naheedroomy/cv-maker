<script setup lang="ts">
import type { JobResponse } from '@/types'
import StatusBadge from './StatusBadge.vue'

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
    :class="{ 'session-entry--active': active }"
    :aria-current="active ? 'page' : undefined"
  >
    <div class="session-top">
      <span class="company-name">{{ job.company_name }}</span>
      <div class="session-badges">
        <span v-if="job.applied" class="applied-badge">Applied</span>
        <StatusBadge :status="job.status" />
      </div>
    </div>
    <span class="created-date">{{ formatDate(job.created_at) }}</span>
  </router-link>
</template>

<style scoped>
.session-entry {
  display: block;
  padding: 8px 16px;
  min-height: 48px;
  text-decoration: none;
  color: #374151;
  border-bottom: 1px solid #e2e8f0;
  cursor: pointer;
  transition: background-color 100ms ease;
}
.session-entry:hover {
  background: #f1f5f9;
  color: #111827;
}
.session-entry--active {
  background: #eff6ff;
  color: #1e40af;
}
.session-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.company-name {
  font-size: 14px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session-badges {
  display: flex;
  align-items: center;
  gap: 4px;
}
.applied-badge {
  font-size: 10px;
  font-weight: 600;
  color: #16a34a;
  background: #dcfce7;
  border-radius: 3px;
  padding: 1px 5px;
}
.created-date {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
  display: block;
}
</style>
