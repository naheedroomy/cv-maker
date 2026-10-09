<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
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
  roles?: number
  skills?: number
  certifications?: number
}
const cvInfo = ref<CvInfo | null>(null)
const searchQuery = ref('')
const sortedJobs = computed(() => {
  const q = searchQuery.value.toLowerCase().trim()
  const filtered = q ? jobs.value.filter(j => j.company_name.toLowerCase().includes(q)) : jobs.value
  return [...filtered].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
})

async function fetchCvInfo() {
  try {
    const res = await apiFetch('/api/cv/me')
    if (res.ok) {
      const data = await res.json()
      cvInfo.value = data.has_cv && data.cv
        ? { loaded: true, name: data.cv.contact?.name, roles: data.cv.experience?.length || 0,
            skills: data.cv.skills?.length || 0, certifications: data.cv.certifications?.length || 0 }
        : { loaded: false }
    }
  } catch { /* The CV page has its own error state; keep navigation usable. */ }
}

function handleSignOut() {
  authStore.logout()
  router.push('/signin')
}
onMounted(async () => {
  await Promise.all([store.fetchJobs().catch(() => {}), fetchCvInfo()])
  pollInterval = setInterval(() => store.fetchJobs().catch(() => {}), 30_000)
})
onUnmounted(() => { if (pollInterval) clearInterval(pollInterval) })
</script>

<template>
  <aside id="app-sidebar" class="sidebar" aria-label="Application navigation">
    <div class="sidebar-brand">
      <RouterLink to="/" class="brand-link" aria-label="CV Maker home">
        <span class="brand-mark" aria-hidden="true"><span>cv</span><i /></span>
        <span class="brand-wordmark">CV MAKER<span class="brand-period">.</span></span>
      </RouterLink>
      <p class="brand-caption">YOUR APPLICATION WORKSPACE</p>
    </div>

    <div class="sidebar-primary">
      <p class="rail-label">WORKSPACE <span>01 / 03</span></p>
      <RouterLink to="/" class="new-job-btn" :class="{ 'new-job-btn--current': route.path === '/' }">
        <span aria-hidden="true">＋</span> New application <span class="link-arrow" aria-hidden="true">↗</span>
      </RouterLink>
      <RouterLink to="/base-cv" class="rail-link" :aria-current="route.path === '/base-cv' ? 'page' : undefined">
        <span class="rail-index">01</span> Base CV <span class="link-arrow" aria-hidden="true">↗</span>
      </RouterLink>
      <RouterLink to="/convert" class="rail-link" :aria-current="route.path === '/convert' ? 'page' : undefined">
        <span class="rail-index">02</span> Import text <span class="link-arrow" aria-hidden="true">↗</span>
      </RouterLink>
      <RouterLink to="/settings" class="rail-link" :aria-current="route.path === '/settings' ? 'page' : undefined">
        <span class="rail-index">03</span> Settings <span class="link-arrow" aria-hidden="true">↗</span>
      </RouterLink>
    </div>

    <div class="sessions-header">
      <p class="rail-label">APPLICATIONS <span>{{ jobs.length.toString().padStart(2, '0') }}</span></p>
      <input v-if="jobs.length" v-model="searchQuery" type="search" class="search-input" placeholder="Find an application" aria-label="Search applications by company" />
    </div>
    <nav class="sessions-list" aria-label="Past applications">
      <template v-if="sortedJobs.length">
        <SessionEntry v-for="job in sortedJobs" :key="job.id" :job="job" :active="route.params.id === job.id" />
      </template>
      <div v-else class="empty-state">
        <span class="empty-rule" aria-hidden="true">—</span>
        <p class="empty-heading">{{ searchQuery ? 'No matching applications' : 'A fresh file.' }}</p>
        <p class="empty-body">{{ searchQuery ? 'Try another company name.' : 'Your applications will live here after you create one.' }}</p>
      </div>
    </nav>

    <div v-if="cvInfo" class="cv-info">
      <span class="rail-label">SOURCE FILE</span>
      <RouterLink v-if="cvInfo.loaded" to="/base-cv" class="cv-info-loaded">
        <span class="cv-info-name">{{ cvInfo.name || 'Your base CV' }}</span>
        <span class="cv-info-detail">{{ cvInfo.roles }} roles · {{ cvInfo.skills }} skills · {{ cvInfo.certifications }} certs</span>
      </RouterLink>
      <div v-else class="cv-info-empty">
        <p class="cv-info-detail">No CV uploaded yet.</p>
        <RouterLink to="/base-cv" class="cv-info-link">Add a base CV →</RouterLink>
      </div>
    </div>
    <div v-if="isAuthenticated && user" class="user-profile">
      <img v-if="user.picture" :src="user.picture" :alt="user.name" class="user-avatar" referrerpolicy="no-referrer" />
      <div v-else class="user-avatar-placeholder" aria-hidden="true">{{ user.name?.charAt(0)?.toUpperCase() }}</div>
      <div class="user-info"><p class="user-name">{{ user.name }}</p><button class="sign-out-btn" @click="handleSignOut">Sign out ↗</button></div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  --color-surface-1: #183535; --color-surface-2: #254742; --color-surface-3: #34544c;
  --color-border: #416059; --color-text-primary: #f7f8ee;
  --color-text-secondary: #d4e2d5; --color-text-tertiary: #b3c8b9;
  --color-accent-primary: #d8f050; --color-accent-primary-hover: #efffa2;
  --color-text-inverted: #183535;
  background: var(--color-surface-1); color: var(--color-text-primary);
  border-right: 1px solid var(--color-border); height: 100dvh; position: sticky; top: 0;
  overflow-y: auto; display: flex; flex-direction: column;
}
.sidebar-brand { padding: 30px 22px 24px; border-bottom: 1px solid var(--color-border); }
.brand-link { display: flex; align-items: center; gap: 11px; color: var(--color-text-primary); text-decoration: none; }
.brand-mark { width: 37px; height: 37px; display: grid; place-items: center; background: var(--color-highlight); color: #183535; font-size: 18px; font-weight: 800; letter-spacing: -2px; position: relative; }
.brand-mark i { position: absolute; width: 6px; height: 6px; right: 4px; bottom: 4px; background: #183535; }
.brand-wordmark { font-weight: 800; font-size: 15px; letter-spacing: -.045em; }
.brand-period { color: var(--color-highlight); }
.brand-caption { margin: 15px 0 0; color: var(--color-text-tertiary); font-size: 9px; font-weight: 700; letter-spacing: .16em; }
.sidebar-primary { padding: 27px 13px 26px; border-bottom: 1px solid var(--color-border); }
.rail-label { display: flex; align-items: center; justify-content: space-between; color: var(--color-text-tertiary); font-size: 10px; font-weight: 700; letter-spacing: .12em; }
.sidebar-primary > .rail-label { padding: 0 10px 13px; }
.rail-label span { opacity: .8; letter-spacing: .03em; }
.new-job-btn { display: flex; align-items: center; gap: 9px; padding: 12px 13px; margin-bottom: 16px; background: var(--color-highlight); color: #183535; font-size: 13px; font-weight: 800; text-decoration: none; border-radius: 4px; min-height: 45px; }
.new-job-btn:hover { background: var(--color-highlight-hover); }
.new-job-btn > span:first-child { font-size: 19px; line-height: 0; font-weight: 400; }
.link-arrow { margin-left: auto; }
.rail-link { display: flex; align-items: center; gap: 12px; min-height: 42px; padding: 6px 10px; color: var(--color-text-secondary); text-decoration: none; font-weight: 600; font-size: 13px; border-radius: 4px; }
.rail-link:hover, .rail-link[aria-current='page'] { background: var(--color-surface-2); color: var(--color-text-primary); }
.rail-index { font-size: 10px; color: var(--color-text-tertiary); letter-spacing: .03em; }
.sessions-header { padding: 24px 22px 11px; }
.search-input { width: 100%; margin-top: 14px; padding: 9px 10px; background: var(--color-surface-2); border: 1px solid var(--color-border); color: var(--color-text-primary); font-size: 12px; border-radius: 4px; }
.search-input::placeholder { color: var(--color-text-tertiary); }
.sessions-list { flex: 1; overflow-y: auto; }
.empty-state { padding: 8px 22px 28px; }
.empty-rule { color: var(--color-highlight); font-size: 22px; line-height: 1; }
.empty-heading { margin: 10px 0 5px; font-size: 14px; font-weight: 700; }
.empty-body { font-size: 12px; line-height: 1.5; color: var(--color-text-tertiary); }
.cv-info { padding: 19px 22px; border-top: 1px solid var(--color-border); }
.cv-info .rail-label { margin-bottom: 10px; }
.cv-info-loaded { display: flex; flex-direction: column; gap: 3px; text-decoration: none; color: var(--color-text-primary); }
.cv-info-loaded:hover .cv-info-name, .cv-info-link:hover { text-decoration: underline; }
.cv-info-name { font-size: 13px; font-weight: 700; }
.cv-info-detail { color: var(--color-text-tertiary); font-size: 11px; line-height: 1.5; }
.cv-info-link { display: inline-block; margin-top: 6px; color: var(--color-highlight); font-size: 12px; font-weight: 700; text-decoration: none; }
.user-profile { display: flex; align-items: center; gap: 10px; padding: 16px 22px; border-top: 1px solid var(--color-border); }
.user-avatar, .user-avatar-placeholder { width: 32px; height: 32px; flex-shrink: 0; object-fit: cover; border-radius: 4px; }
.user-avatar-placeholder { display: grid; place-items: center; background: var(--color-highlight); color: #183535; font-weight: 800; }
.user-info { min-width: 0; }
.user-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 700; }
.sign-out-btn { padding: 2px 0; border: 0; background: none; color: var(--color-text-tertiary); font-size: 11px; }
.sign-out-btn:hover { color: var(--color-highlight); }
@media (max-width: 900px) {
  .sidebar { position: fixed; left: 0; z-index: 100; width: min(85vw, 300px); transform: translateX(-100%); visibility: hidden; transition: transform .2s ease, visibility .2s ease; }
  .sidebar.sidebar--open { transform: translateX(0); visibility: visible; }
  .sidebar-brand { padding-left: 72px; }
}
</style>
