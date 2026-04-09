<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RouterLink } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useJobStore } from '@/stores/jobStore'
import { useAuthStore } from '@/stores/authStore'
import { apiFetch } from '@/utils/apiFetch'
import SessionEntry from './SessionEntry.vue'

const store = useJobStore()
const { jobs } = storeToRefs(store)
const route = useRoute()
const router = useRouter()

const authStore = useAuthStore()
const { user, isAuthenticated } = storeToRefs(authStore)

let pollInterval: ReturnType<typeof setInterval> | null = null

interface CvInfo {
  loaded: boolean
  name?: string
  email?: string
  location?: string
  roles?: number
  skills?: number
  certifications?: number
}

const cvInfo = ref<CvInfo | null>(null)
const searchQuery = ref('')

const sortedJobs = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  const filtered = q
    ? jobs.value.filter(j => j.company_name.toLowerCase().includes(q))
    : jobs.value
  return [...filtered].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
})

async function fetchCvInfo() {
  try {
    const res = await apiFetch('/api/cv/me')
    if (res.ok) {
      const data = await res.json()
      if (data.has_cv && data.cv) {
        cvInfo.value = {
          loaded: true,
          name: data.cv.contact?.name,
          roles: data.cv.experience?.length || 0,
          skills: data.cv.skills?.length || 0,
          certifications: data.cv.certifications?.length || 0,
        }
      } else {
        cvInfo.value = { loaded: false }
      }
    }
  } catch { /* ignore */ }
}

function handleSignOut() {
  authStore.logout()
  router.push('/signin')
}

onMounted(async () => {
  await Promise.all([
    store.fetchJobs().catch(() => {}),
    fetchCvInfo(),
  ])
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
      <div class="header-links">
        <RouterLink to="/convert" class="header-link">Import CV</RouterLink>
        <RouterLink to="/settings" class="header-link">Settings</RouterLink>
      </div>
    </div>
    <div v-if="jobs.length > 0" class="search-box">
      <input
        v-model="searchQuery"
        type="text"
        class="search-input"
        placeholder="Search jobs..."
      />
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
    <div v-if="cvInfo" class="cv-info">
      <RouterLink v-if="cvInfo.loaded" to="/base-cv" class="cv-info-loaded">
        <p class="cv-info-name">{{ cvInfo.name }}</p>
        <p class="cv-info-detail">{{ cvInfo.roles }} roles, {{ cvInfo.skills }} skills, {{ cvInfo.certifications }} certs</p>
      </RouterLink>
      <div v-else class="cv-info-empty">
        <p class="cv-info-detail">No CV uploaded</p>
        <RouterLink to="/base-cv" class="cv-info-link">Upload CV</RouterLink>
      </div>
    </div>
    <div v-if="isAuthenticated && user" class="user-profile">
      <img
        v-if="user.picture"
        :src="user.picture"
        :alt="user.name"
        class="user-avatar"
        referrerpolicy="no-referrer"
      />
      <div v-else class="user-avatar-placeholder">
        {{ user.name?.charAt(0)?.toUpperCase() }}
      </div>
      <div class="user-info">
        <p class="user-name">{{ user.name }}</p>
        <button class="sign-out-btn" @click="handleSignOut">Sign out</button>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.search-box {
  padding: 8px 16px;
  border-bottom: 1px solid #e2e8f0;
}
.search-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
  color: #111827;
  box-sizing: border-box;
}
.search-input:focus {
  outline: none;
  border-color: #2563eb;
}
.search-input::placeholder {
  color: #9ca3af;
}

.sidebar {
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  height: 100vh;
  position: sticky;
  top: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
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
.header-links {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 8px;
}
.header-link {
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  text-decoration: none;
  transition: color 150ms ease;
}
.header-link:hover {
  color: #111827;
}
nav {
  flex: 1;
  overflow-y: auto;
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
.cv-info {
  padding: 12px 16px;
  border-top: 1px solid #e2e8f0;
  margin-top: auto;
}
.cv-info-loaded {
  display: block;
  text-decoration: none;
  transition: background-color 150ms ease;
  border-radius: 4px;
  padding: 4px;
  margin: -4px;
}
.cv-info-loaded:hover {
  background: #f3f4f6;
}
.cv-info-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}
.cv-info-detail {
  font-size: 11px;
  color: #6b7280;
  margin: 2px 0 0;
}
.cv-info-empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cv-info-link {
  font-size: 11px;
  color: #2563eb;
  text-decoration: none;
}
.cv-info-link:hover {
  text-decoration: underline;
}
.user-profile {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid #e2e8f0;
  margin-top: auto;
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
}
.user-avatar-placeholder {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #2563eb;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
.user-info {
  flex: 1;
  min-width: 0;
}
.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sign-out-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 11px;
  color: #6b7280;
  cursor: pointer;
  transition: color 150ms ease;
}
.sign-out-btn:hover {
  color: #dc2626;
}
</style>
