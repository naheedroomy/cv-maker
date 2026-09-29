<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCvStore } from '@/stores/cvStore'
import PdfDropZone from '@/components/PdfDropZone.vue'
import CvFormEditor from '@/components/CvFormEditor.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { apiFetch } from '@/utils/apiFetch'

const store = useCvStore()
const { cv, loading, saving, uploading, uploadProgress, error } = storeToRefs(store)

const downloading = ref(false)

onMounted(() => {
  store.fetchCv()
})

// ── Upload / Save / Delete ─────────────────────────────────────────────────

function handleUpload(file: File) {
  store.uploadPdf(file)
}

async function handleSave() {
  await store.saveCv()
}

function handleDelete() {
  if (confirm('Remove your CV? This cannot be undone.')) {
    store.deleteCv()
  }
}

async function handleDownload() {
  if (!cv.value) return
  downloading.value = true
  try {
    const res = await apiFetch('/api/cv/me/pdf', {
      method: 'POST',
      body: JSON.stringify(cv.value),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error((body as { detail?: string }).detail ?? `PDF generation failed: ${res.status}`)
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'Base-CV.pdf'
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Download failed'
  } finally {
    downloading.value = false
  }
}

function handleCreateEmpty() {
  store.createEmptyCv()
}
</script>

<template>
  <div class="cv-view">
    <div v-if="error" class="error-banner">{{ error }}</div>

    <div v-if="loading" class="loading-state">
      <LoadingSpinner />
      <span class="loading-text">Loading...</span>
    </div>

    <!-- No CV yet — upload zone + create from scratch -->
    <div v-else-if="!cv" class="empty-state">
      <div class="editor-header">
        <h2 class="editor-title">My Base CV</h2>
      </div>
      <PdfDropZone
        :uploading="uploading"
        :upload-progress="uploadProgress"
        @upload="handleUpload"
      />
      <p class="or-divider"><span>or</span></p>
      <div class="create-empty-row">
        <button type="button" class="btn-secondary" @click="handleCreateEmpty">
          Create CV from scratch
        </button>
      </div>
    </div>

    <!-- CV loaded — editor and actions -->
    <div v-else class="cv-loaded-container">
      <!-- Re-upload dropzone (optional compact accordion/bar) -->
      <div class="top-reupload">
        <PdfDropZone
          :uploading="uploading"
          :upload-progress="uploadProgress"
          @upload="handleUpload"
        />
      </div>

      <CvFormEditor
        v-model="cv"
        title="My Base CV"
        save-label="Save CV"
        :saving="saving"
        :show-download="true"
        :downloading="downloading"
        @save="handleSave"
        @download="handleDownload"
      />

      <div class="footer-danger-actions">
        <button
          type="button"
          class="btn-danger"
          @click="handleDelete"
        >
          Remove CV
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cv-view {
  width: 100%;
  max-width: 1040px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cv-loaded-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.top-reupload {
  margin-bottom: 4px;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.editor-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

/* Error */
.error-banner {
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  color: var(--color-error);
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
}

/* Loading */
.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 48px 0;
  justify-content: center;
}

.loading-text {
  font-size: 14px;
  color: var(--color-text-secondary);
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.or-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  color: var(--color-text-tertiary);
  font-size: 13px;
}

.or-divider::before,
.or-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.create-empty-row {
  text-align: center;
}

.btn-secondary {
  background: var(--color-surface-1);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  height: 38px;
  padding: 0 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-secondary:hover {
  background: var(--color-surface-2);
}

.footer-danger-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.btn-danger {
  background: none;
  color: var(--color-error);
  border: 1px solid var(--color-error-border);
  border-radius: 6px;
  height: 36px;
  padding: 0 16px;
  font-size: 13px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-danger:hover {
  background: var(--color-error-bg);
}
</style>
