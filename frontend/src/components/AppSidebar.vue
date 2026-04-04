<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useJobStore } from '@/stores/jobStore'
import SessionEntry from './SessionEntry.vue'

const store = useJobStore()
const { jobs } = storeToRefs(store)
const route = useRoute()
const router = useRouter()

let pollInterval: ReturnType<typeof setInterval> | null = null

const sortedJobs = computed(() =>
  [...jobs.value].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  ),
)

onMounted(async () => {
  await store.fetchJobs().catch(() => {})
  pollInterval = setInterval(() => store.fetchJobs().catch(() => {}), 30_000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <button class="new-job-btn" @click="router.push('/')">New Job</button>
    </div>
    <nav aria-label="Job sessions">
      <template v-if="sortedJobs.length > 0">
        <SessionEntry
          v-for="job in sortedJobs"
          :key="job.id"
          :job="job"
          :active="route.params.id === job.id"
        />
      </template>
      <div v-else class="empty-state">
        <p class="empty-heading">No sessions yet</p>
        <p class="empty-body">Submit a job listing to get started.</p>
      </div>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar {
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  height: 100vh;
  position: sticky;
  top: 0;
  overflow-y: auto;
}
.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
}
.new-job-btn {
  display: block;
  width: 100%;
  height: 44px;
  background: #2563eb;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 150ms ease;
}
.new-job-btn:hover {
  background: #1d4ed8;
}
.empty-state {
  padding: 16px;
}
.empty-heading {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 4px;
}
.empty-body {
  font-size: 12px;
  color: #6b7280;
}
</style>
