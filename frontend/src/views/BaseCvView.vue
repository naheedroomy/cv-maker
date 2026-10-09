<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useCvStore } from '@/stores/cvStore'
import PdfDropZone from '@/components/PdfDropZone.vue'
import CvFormEditor from '@/components/CvFormEditor.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const store = useCvStore()
const {
  baseCvs,
  activeCvId,
  activeCv,
  activeCvName,
  activeCvIsDefault,
  loading,
  saving,
  uploading,
  uploadProgress,
  error,
} = storeToRefs(store)

const downloading = ref(false)

// Rename modal state
const showRenameModal = ref(false)
const renameName = ref('')
const renaming = ref(false)
const renameInputRef = ref<HTMLInputElement | null>(null)

// Create modal state
const showCreateModal = ref(false)
const createMode = ref<'duplicate' | 'upload' | 'scratch'>('duplicate')
const newCvName = ref('')

onMounted(() => {
  store.fetchBaseCvs()
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (showRenameModal.value) {
      showRenameModal.value = false
    } else if (showCreateModal.value && !uploading.value) {
      showCreateModal.value = false
    }
  }
}

// ── Active CV Action Handlers ───────────────────────────────────────────────

async function handleSetDefault() {
  if (!activeCvId.value) return
  await store.setDefaultBaseCv(activeCvId.value)
}

function openRenameModal() {
  if (!activeCvId.value) return
  renameName.value = activeCvName.value
  showRenameModal.value = true
  nextTick(() => {
    renameInputRef.value?.focus()
    renameInputRef.value?.select()
  })
}

async function handleRenameSubmit() {
  if (!activeCvId.value || !renameName.value.trim()) return
  renaming.value = true
  try {
    await store.renameBaseCv(activeCvId.value, renameName.value.trim())
    if (!store.error) {
      showRenameModal.value = false
    }
  } finally {
    renaming.value = false
  }
}

async function handleDuplicateActive() {
  if (!activeCvId.value) return
  const name = `${activeCvName.value || 'Base CV'} Copy`
  await store.createBaseCv(name, { sourceId: activeCvId.value })
}

async function handleDelete() {
  if (!activeCvId.value || baseCvs.value.length <= 1) return
  if (confirm('Delete this Base CV? This cannot be undone.')) {
    await store.deleteBaseCv(activeCvId.value)
  }
}

async function handleDownload() {
  downloading.value = true
  try {
    await store.downloadBaseCvPdf()
  } finally {
    downloading.value = false
  }
}

async function handleSave() {
  await store.saveActiveCv()
}

// ── Create Modal Handlers ──────────────────────────────────────────────────

function openCreateModal(initialMode?: 'duplicate' | 'upload' | 'scratch') {
  let mode = initialMode
  if (!mode) {
    mode = activeCvId.value ? 'duplicate' : 'upload'
  } else if (mode === 'duplicate' && !activeCvId.value) {
    mode = 'upload'
  }
  setCreateMode(mode)
  showCreateModal.value = true
}

function setCreateMode(mode: 'duplicate' | 'upload' | 'scratch') {
  createMode.value = mode
  if (mode === 'duplicate') {
    newCvName.value = `${activeCvName.value || 'Base CV'} Copy`
  } else if (mode === 'upload') {
    newCvName.value = 'Uploaded Base CV'
  } else {
    newCvName.value = 'New Base CV'
  }
}

async function handleDuplicateSubmit() {
  if (!activeCvId.value) return
  const name = newCvName.value.trim() || `${activeCvName.value || 'Base CV'} Copy`
  await store.createBaseCv(name, { sourceId: activeCvId.value })
  if (!store.error) {
    showCreateModal.value = false
  }
}

async function handleUploadModal(file: File, options?: { provider: string; model: string }) {
  const name = newCvName.value.trim() || 'Uploaded Base CV'
  await store.createBaseCv(name, {
    file,
    provider: options?.provider,
    model: options?.model,
  })
  if (!store.error) {
    showCreateModal.value = false
  }
}

async function handleScratchSubmit() {
  const name = newCvName.value.trim() || 'New Base CV'
  await store.createBaseCv(name)
  if (!store.error) {
    showCreateModal.value = false
  }
}
</script>

<template>
  <div class="cv-view">
    <header class="page-heading">
      <span class="page-kicker">YOUR SOURCE MATERIAL / 02</span>
      <h1>One good CV. <em>Many possibilities.</em></h1>
      <p>Keep your experience accurate and up to date. Choose a base CV for every new application.</p>
    </header>
    <!-- Global Error banner -->
    <div v-if="error" class="error-banner">{{ error }}</div>

    <!-- Initial loading state -->
    <div v-if="loading && baseCvs.length === 0" class="loading-state">
      <LoadingSpinner />
      <span class="loading-text">Loading Base CVs...</span>
    </div>

    <!-- Empty state when no CVs exist -->
    <div v-else-if="baseCvs.length === 0" class="empty-state">
      <div class="empty-card">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </div>
        <h2 class="empty-title">Start with your experience.</h2>
        <p class="empty-description">
          Add a base CV to get started. Upload a PDF, import text, or fill in your details from scratch.
        </p>
        <div class="empty-actions">
          <button type="button" class="btn-primary" @click="openCreateModal('upload')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload PDF CV
          </button>
          <button type="button" class="btn-secondary" @click="openCreateModal('scratch')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Start from Scratch
          </button>
        </div>
      </div>
    </div>

    <!-- Base CV Manager View -->
    <div v-else class="cv-manager-layout">
      <!-- Top Tab Bar & Active CV Controls -->
      <div class="top-tab-bar">
        <div class="tabs-header-row">
          <div class="tabs-scroll-container" role="tablist" aria-label="Base CV Profiles">
            <button
              v-for="item in baseCvs"
              :key="item.id"
              role="tab"
              :aria-selected="item.id === activeCvId"
              class="tab-pill"
              :class="{ 'tab-pill--active': item.id === activeCvId }"
              @click="store.selectBaseCv(item.id)"
            >
              <span class="tab-title">{{ item.name }}</span>
              <span v-if="item.is_default" class="badge-default">★ Default</span>
            </button>
          </div>

          <button
            type="button"
            class="btn-new-cv"
            @click="openCreateModal()"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Base CV
          </button>
        </div>

        <!-- Active CV Action Buttons Bar -->
        <div v-if="activeCv" class="active-toolbar">
          <div class="active-info">
            <span class="active-tag">Active Profile:</span>
            <span class="active-cv-heading">{{ activeCvName }}</span>
            <span v-if="activeCvIsDefault" class="badge-default">★ Default</span>
          </div>

          <div class="active-actions">
            <button
              v-if="!activeCvIsDefault"
              type="button"
              class="btn-toolbar btn-toolbar--default"
              @click="handleSetDefault"
              title="Make this your default Base CV for new job applications"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              Set as Default
            </button>

            <button
              type="button"
              class="btn-toolbar"
              @click="openRenameModal"
              title="Rename active Base CV"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
              </svg>
              Rename
            </button>

            <button
              type="button"
              class="btn-toolbar"
              @click="handleDuplicateActive"
              title="Create a duplicate copy of this Base CV"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              Duplicate
            </button>

            <button
              type="button"
              class="btn-toolbar btn-toolbar--danger"
              :disabled="baseCvs.length <= 1"
              :title="baseCvs.length <= 1 ? 'Cannot delete your only Base CV' : 'Delete this Base CV'"
              @click="handleDelete"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              Delete
            </button>
          </div>
        </div>
      </div>

      <!-- Main Editor Body -->
      <div v-if="loading && !activeCv" class="loading-state">
        <LoadingSpinner />
        <span class="loading-text">Loading Base CV...</span>
      </div>

      <CvFormEditor
        v-else-if="activeCv"
        v-model="activeCv"
        :title="activeCvName"
        save-label="Save Base CV"
        :saving="saving"
        :show-download="true"
        :downloading="downloading"
        @save="handleSave"
        @download="handleDownload"
      />
    </div>

    <!-- Rename Modal -->
    <div
      v-if="showRenameModal"
      class="modal-backdrop"
      @click.self="showRenameModal = false"
    >
      <div class="modal-card modal-card--sm">
        <div class="modal-header">
          <h3 class="modal-title">Rename Base CV</h3>
          <button type="button" class="modal-close" aria-label="Close rename dialog" @click="showRenameModal = false">✕</button>
        </div>
        <form @submit.prevent="handleRenameSubmit" class="modal-body">
          <div class="form-group">
            <label class="modal-label" for="rename-input">Base CV Name</label>
            <input
              id="rename-input"
              ref="renameInputRef"
              v-model="renameName"
              type="text"
              class="modal-input"
              placeholder="e.g. Platform Engineer Base"
              required
            />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" @click="showRenameModal = false">
              Cancel
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="!renameName.trim() || renaming"
            >
              {{ renaming ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Create New Base CV Modal -->
    <div
      v-if="showCreateModal"
      class="modal-backdrop"
      @click.self="!uploading && (showCreateModal = false)"
    >
      <div class="modal-card">
        <div class="modal-header">
          <h3 class="modal-title">Create New Base CV</h3>
          <button
            type="button"
            class="modal-close"
            aria-label="Close new CV dialog"
            :disabled="uploading"
            @click="showCreateModal = false"
          >
            ✕
          </button>
        </div>

        <div class="modal-body">
          <!-- 3 Choices Mode Selector -->
          <div class="creation-tabs">
            <button
              type="button"
              class="creation-tab"
              :class="{ 'creation-tab--active': createMode === 'duplicate' }"
              :disabled="!activeCvId || uploading"
              @click="setCreateMode('duplicate')"
            >
              <div class="creation-tab-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              </div>
              <span class="creation-tab-title">Duplicate Active</span>
              <span class="creation-tab-desc">Clone current CV</span>
            </button>

            <button
              type="button"
              class="creation-tab"
              :class="{ 'creation-tab--active': createMode === 'upload' }"
              :disabled="uploading"
              @click="setCreateMode('upload')"
            >
              <div class="creation-tab-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="12" y1="18" x2="12" y2="12" />
                  <line x1="9" y1="15" x2="15" y2="15" />
                </svg>
              </div>
              <span class="creation-tab-title">Upload PDF</span>
              <span class="creation-tab-desc">Vision AI extraction</span>
            </button>

            <button
              type="button"
              class="creation-tab"
              :class="{ 'creation-tab--active': createMode === 'scratch' }"
              :disabled="uploading"
              @click="setCreateMode('scratch')"
            >
              <div class="creation-tab-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
              </div>
              <span class="creation-tab-title">Start from Scratch</span>
              <span class="creation-tab-desc">Blank CV template</span>
            </button>
          </div>

          <!-- Mode 1: Duplicate -->
          <form
            v-if="createMode === 'duplicate'"
            @submit.prevent="handleDuplicateSubmit"
            class="mode-content"
          >
            <div class="form-group">
              <label class="modal-label" for="dup-name-input">Base CV Name</label>
              <input
                id="dup-name-input"
                v-model="newCvName"
                type="text"
                class="modal-input"
                placeholder="e.g. Platform Engineer Base"
                required
              />
            </div>
            <p class="mode-help-text">
              Clones all contact info, experience, skills, and projects from
              <strong>{{ activeCvName }}</strong> into a new Base CV profile.
            </p>
            <div class="modal-footer">
              <button
                type="button"
                class="btn-secondary"
                :disabled="saving"
                @click="showCreateModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn-primary"
                :disabled="!newCvName.trim() || saving"
              >
                <LoadingSpinner v-if="saving" class="btn-spinner" />
                {{ saving ? 'Duplicating...' : 'Duplicate Base CV' }}
              </button>
            </div>
          </form>

          <!-- Mode 2: Upload PDF -->
          <div
            v-else-if="createMode === 'upload'"
            class="mode-content"
          >
            <div class="form-group">
              <label class="modal-label" for="upload-name-input">Base CV Name</label>
              <input
                id="upload-name-input"
                v-model="newCvName"
                type="text"
                class="modal-input"
                placeholder="e.g. Uploaded Base CV"
                :disabled="uploading"
                required
              />
            </div>

            <PdfDropZone
              :uploading="uploading"
              :upload-progress="uploadProgress"
              @upload="handleUploadModal"
            />

            <div class="modal-footer modal-footer--plain">
              <button
                type="button"
                class="btn-secondary"
                :disabled="uploading"
                @click="showCreateModal = false"
              >
                Cancel
              </button>
            </div>
          </div>

          <!-- Mode 3: Start from Scratch -->
          <form
            v-else-if="createMode === 'scratch'"
            @submit.prevent="handleScratchSubmit"
            class="mode-content"
          >
            <div class="form-group">
              <label class="modal-label" for="scratch-name-input">Base CV Name</label>
              <input
                id="scratch-name-input"
                v-model="newCvName"
                type="text"
                class="modal-input"
                placeholder="e.g. New Base CV"
                required
              />
            </div>
            <p class="mode-help-text">
              Creates a blank Base CV template ready for you to fill in your contact information, work experience, education, and skills.
            </p>
            <div class="modal-footer">
              <button
                type="button"
                class="btn-secondary"
                :disabled="saving"
                @click="showCreateModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="btn-primary"
                :disabled="!newCvName.trim() || saving"
              >
                <LoadingSpinner v-if="saving" class="btn-spinner" />
                {{ saving ? 'Creating...' : 'Create Blank CV' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cv-view {
  width: 100%;
  max-width: 1160px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-heading { margin: 0 0 22px; }
.page-kicker { color: var(--color-text-secondary); font-size: 10px; font-weight: 800; letter-spacing: .13em; }
.page-heading h1 { margin: 13px 0 7px; font-size: clamp(32px, 3.5vw, 52px); font-weight: 800; letter-spacing: -.055em; line-height: 1.12; }
.page-heading h1 em { font-style: normal; text-decoration: underline; text-decoration-color: var(--color-highlight); text-decoration-thickness: .13em; }
.page-heading p { max-width: 570px; color: var(--color-text-secondary); font-size: 14px; line-height: 1.6; }

.cv-manager-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Top Tab Bar & Active Controls */
.top-tab-bar {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tabs-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.tabs-scroll-container {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
  scrollbar-width: thin;
  flex: 1;
}

.tab-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 8px;
  background-color: var(--color-surface-1);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.tab-pill:hover:not(.tab-pill--active) {
  background-color: var(--color-surface-2);
  color: var(--color-text-primary);
  border-color: var(--color-surface-3);
}

.tab-pill--active {
  background-color: var(--color-accent-secondary);
  border-color: var(--color-accent-primary);
  color: var(--color-text-primary);
  font-weight: 600;
  box-shadow: 0 0 0 1px var(--color-accent-primary);
}

.tab-title {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge-default {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background-color: var(--color-accent-secondary);
  color: var(--color-accent-primary);
  border: 1px solid var(--color-border);
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  padding: 3px 6px;
  border-radius: 4px;
  letter-spacing: 0.02em;
}

.btn-new-cv {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background-color: var(--color-accent-primary);
  color: var(--color-text-inverted);
  border: none;
  border-radius: 8px;
  height: 36px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.15s ease;
}

.btn-new-cv:hover {
  background-color: var(--color-accent-primary-hover);
}

/* Active CV Toolbar */
.active-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 16px;
  background-color: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.active-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.active-tag {
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
}

.active-cv-heading {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.active-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-toolbar {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background-color: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-toolbar:hover:not(:disabled) {
  background-color: var(--color-surface-3);
  color: var(--color-text-primary);
}

.btn-toolbar:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-toolbar--default {
  color: var(--color-accent-primary);
  border-color: var(--color-accent-primary);
}

.btn-toolbar--default:hover:not(:disabled) {
  background-color: var(--color-accent-secondary);
  color: var(--color-accent-primary);
}

.btn-toolbar--danger {
  color: var(--color-error);
}

.btn-toolbar--danger:hover:not(:disabled) {
  background-color: var(--color-error-bg);
  border-color: var(--color-error-border);
  color: var(--color-error-text);
}

/* Error Banner */
.error-banner {
  background: var(--color-error-bg);
  border: 1px solid var(--color-error-border);
  color: var(--color-error);
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
}

/* Loading State */
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

/* Empty State */
.empty-state {
  display: flex;
  justify-content: center;
  padding: 32px 0;
}

.empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  background-color: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  padding: 48px 32px;
  max-width: 520px;
  width: 100%;
}

.empty-icon {
  color: var(--color-text-tertiary);
  margin-bottom: 16px;
}

.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 8px 0;
}

.empty-description {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0 0 24px 0;
}

.empty-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

/* Buttons */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background-color: var(--color-accent-primary);
  color: var(--color-text-inverted);
  border: none;
  border-radius: 6px;
  height: 38px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--color-accent-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background-color: var(--color-surface-2);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  height: 38px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--color-surface-3);
  color: var(--color-text-primary);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-spinner {
  width: 14px;
  height: 14px;
}

/* Modals */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background-color: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.modal-card {
  background-color: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  width: 100%;
  max-width: 580px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-card--sm {
  max-width: 440px;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.modal-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.modal-close {
  background: none;
  border: none;
  color: var(--color-text-tertiary);
  font-size: 18px;
  line-height: 1;
  padding: 4px;
  border-radius: 4px;
  cursor: pointer;
  transition: color 0.15s ease;
}

.modal-close:hover:not(:disabled) {
  color: var(--color-text-primary);
}

.modal-close:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.modal-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.modal-input {
  background-color: var(--color-surface-2);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.15s ease;
}

.modal-input:focus {
  border-color: var(--color-accent-primary);
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
}

.modal-footer--plain {
  padding-top: 0;
}

/* Creation Modal Tabs */
.creation-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.creation-tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 6px;
  padding: 14px 8px;
  background-color: var(--color-surface-2);
  border: 2px solid var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
  color: var(--color-text-secondary);
}

.creation-tab:hover:not(:disabled) {
  border-color: var(--color-accent-primary-hover);
  color: var(--color-text-primary);
}

.creation-tab:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.creation-tab--active {
  border-color: var(--color-accent-primary);
  background-color: var(--color-accent-secondary);
  color: var(--color-accent-primary);
}

.creation-tab-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.creation-tab-title {
  font-size: 12px;
  font-weight: 600;
  display: block;
}

.creation-tab-desc {
  font-size: 11px;
  color: var(--color-text-tertiary);
  display: block;
}

.creation-tab--active .creation-tab-desc {
  color: var(--color-text-secondary);
}

.mode-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mode-help-text {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
</style>
