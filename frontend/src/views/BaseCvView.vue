<script setup lang="ts">
import { ref, onMounted } from 'vue'
import CvPreview from '@/components/CvPreview.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const loading = ref(true)
const cvData = ref<any>(null)
const loaded = ref(false)

onMounted(async () => {
  try {
    const res = await fetch('/api/cv/info')
    if (res.ok) {
      const data = await res.json()
      loaded.value = data.loaded === true
      if (data.cv) cvData.value = data.cv
    }
  } catch { /* ignore */ }
  loading.value = false
})
</script>

<template>
  <div class="base-cv-view">
    <h2 class="page-title">Imported CV</h2>

    <div v-if="loading" class="loading-state">
      <LoadingSpinner />
      <p class="status-text">Loading...</p>
    </div>

    <div v-else-if="!loaded" class="empty-state">
      <p class="empty-heading">No CV imported yet</p>
      <p class="empty-body">Go to <RouterLink to="/convert" class="link">Import CV</RouterLink> to upload your base CV.</p>
    </div>

    <template v-else-if="cvData">
      <p class="cv-meta">
        {{ cvData.contact?.name }}
        <span v-if="cvData.contact?.location"> &middot; {{ cvData.contact.location }}</span>
      </p>
      <CvPreview :cv="cvData" />
    </template>
  </div>
</template>

<style scoped>
.base-cv-view {
  max-width: 800px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 8px;
}
.cv-meta {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 24px;
}
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 0;
}
.status-text {
  font-size: 14px;
  color: #6b7280;
}
.empty-state {
  padding: 48px 0;
  text-align: center;
}
.empty-heading {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 8px;
}
.empty-body {
  font-size: 14px;
  color: #6b7280;
}
.link {
  color: #2563eb;
  text-decoration: none;
}
.link:hover {
  text-decoration: underline;
}
</style>
