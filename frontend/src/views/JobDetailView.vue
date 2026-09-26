<script setup lang="ts">
import { ref, watch, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useJobStore, type JobResponse } from '@/stores/jobStore'
import { apiFetch } from '@/utils/apiFetch'
import StatusBadge from '@/components/StatusBadge.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import SkeletonSection from '@/components/SkeletonSection.vue'
import CvPreview from '@/components/CvPreview.vue'
import GapDiffTable from '@/components/GapDiffTable.vue'
import TailoringNotes from '@/components/TailoringNotes.vue'
import RegeneratePanel from '@/components/RegeneratePanel.vue'
import CoverLetterSection from '@/components/CoverLetterSection.vue'

const route = useRoute()
const router = useRouter()
const store = useJobStore()
const { currentJob, error } = storeToRefs(store)
const jobId = computed(() => route.params.id as string)

const cancelling = ref(false)
const downloading = ref(false)
const deleting = ref(false)
const regenerating = ref(false)
const savingListing = ref(false)
const activeTab = ref<'cv' | 'cover-letter' | 'analysis' | 'job-listing'>('cv')

const statusText: Record<string, string> = {
  pending: 'Analyzing job...',
  running: 'Generating tailored CV...',
  complete: 'CV ready',
  failed: 'Generation failed',
  cancelled: 'Cancelled',
}

async function loadJob(id: string) {
  store.closeSSE()
  currentJob.value = null
  activeTab.value = 'cv'
  await store.fetchJob(id)
  // Re-read from store — fetchJob sets currentJob.value internally.
  // Cast needed because vue-tsc narrows to 'never' after the null assignment above.
  const loaded = store.currentJob as JobResponse | null
  if (loaded && !['complete', 'failed', 'cancelled'].includes(loaded.status)) {
    store.openSSE(id)
  }
}

watch(jobId, (id) => { loadJob(id) }, { immediate: true })

onUnmounted(() => {
  store.closeSSE()
})

async function handleCancel() {
  cancelling.value = true
  try {
    await store.cancelJob(jobId.value)
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Cancel failed'
  } finally {
    cancelling.value = false
  }
}

async function handleDownload() {
  if (!currentJob.value) return
  downloading.value = true
  try {
    await store.downloadPdf(jobId.value, currentJob.value.company_name)
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Download failed'
  } finally {
    downloading.value = false
  }
}

async function handleDelete() {
  if (!currentJob.value) return
  deleting.value = true
  try {
    await store.deleteJob(jobId.value)
    router.push('/')
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Delete failed'
  } finally {
    deleting.value = false
  }
}

function handleDownloadJobText() {
  if (!currentJob.value?.job_text) return
  const blob = new Blob([currentJob.value.job_text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const safeName = (currentJob.value.company_name || 'job').replace(/[^a-z0-9]+/gi, '-').toLowerCase()
  a.href = url
  a.download = `${safeName}-job-description.txt`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

async function handleSaveListing() {
  if (!currentJob.value) return
  savingListing.value = true
  try {
    const res = await apiFetch(`/api/jobs/${jobId.value}/listing`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_link: currentJob.value.job_link,
        job_text: currentJob.value.job_text,
      }),
    })
    if (!res.ok) {
      store.error = `Save failed: ${res.status}`
    }
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Save failed'
  } finally {
    savingListing.value = false
  }
}

async function handleRegenerate(
  model?: string,
  creativityLevel?: number,
  userNotes?: string,
  modelId?: string,
  reasoningEffort?: string,
) {
  if (!currentJob.value) return
  regenerating.value = true
  try {
    await store.regenerateJob(
      currentJob.value,
      model,
      creativityLevel,
      userNotes,
      modelId,
      reasoningEffort,
    )
    // Job is now pending — open SSE to track progress
    store.openSSE(jobId.value)
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Regenerate failed'
  } finally {
    regenerating.value = false
  }
}
</script>

<template>
  <!-- Loading state: job not yet fetched -->
  <div v-if="!currentJob" class="loading-state">
    <LoadingSpinner />
    <p class="status-text">Loading...</p>
  </div>

  <!-- Job detail: currentJob exists -->
  <div v-else class="job-detail-view">

    <!-- Zone 1: HEADER (always visible) -->
    <div class="job-header">
      <h2 class="company-heading">{{ currentJob.company_name }}</h2>
      <StatusBadge :status="currentJob.status" />
      <span class="model-badge">{{ { 'claude-haiku': 'Claude CLI', 'claude-api': 'Claude API', 'gemini-flash': 'Gemini', 'openai': 'OpenAI' }[currentJob.model] || currentJob.model }}</span>
      <span class="model-badge">Level {{ currentJob.creativity_level ?? 2 }}</span>
      <span class="model-badge">{{ new Date(currentJob.updated_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
      <button
        class="applied-toggle"
        :class="{ 'applied-toggle--active': currentJob.applied }"
        @click="store.toggleApplied(jobId)"
      >{{ currentJob.applied ? 'Applied' : 'Not Applied' }}</button>
      <span v-if="currentJob.applied && currentJob.applied_at" class="applied-date">{{ new Date(currentJob.applied_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}</span>
    </div>
    <a
      v-if="currentJob.job_link"
      :href="currentJob.job_link"
      target="_blank"
      rel="noopener noreferrer"
      class="job-link"
    >{{ currentJob.job_link }}</a>

    <!-- Error banner (store-level errors) -->
    <ErrorBanner
      v-if="error"
      :message="error"
      @retry="handleRegenerate"
    />

    <!-- Zone 3: TAB BAR (always visible once job exists) -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'cv' }"
        @click="activeTab = 'cv'"
      >CV</button>
      <button
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'cover-letter' }"
        @click="activeTab = 'cover-letter'"
      >Cover Letter</button>
      <button
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'analysis' }"
        @click="activeTab = 'analysis'"
      >Analysis</button>
      <button
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === 'job-listing' }"
        @click="activeTab = 'job-listing'"
      >Job Listing</button>
    </div>

    <!-- Zone 4: TAB PANELS -->

    <!-- CV Tab -->
    <div v-show="activeTab === 'cv'" class="tab-panel">
      <!-- Version history (show on top so it's visible during regeneration) -->
      <div v-if="currentJob.cv_history && currentJob.cv_history.length > 0" class="cv-history cv-history--top">
        <h4 class="history-heading">Previous Versions</h4>
        <div class="history-list">
          <button
            v-for="entry in currentJob.cv_history"
            :key="entry.version"
            class="history-btn"
            @click="store.downloadPdf(jobId, currentJob.company_name, entry.version)"
          >
            Download V{{ entry.version }}
            <span class="history-meta">
              {{ { 'claude-haiku': 'CLI', 'claude-api': 'Claude', 'gemini-flash': 'Gemini', 'openai': 'OpenAI' }[entry.model] || entry.model }}
              · L{{ entry.creativity_level }}
              · {{ new Date(entry.created_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }}
            </span>
          </button>
        </div>
      </div>

      <!-- Generating state (pending/running) -->
      <template v-if="currentJob.status === 'pending' || currentJob.status === 'running'">
        <div class="spinner-container">
          <LoadingSpinner />
          <p class="status-text">{{ statusText[currentJob.status] }}</p>
        </div>
        <template v-if="currentJob.status === 'running'">
          <SkeletonSection title="Summary" :lines="3" />
          <SkeletonSection title="Experience" :lines="5" />
          <SkeletonSection title="Skills" :lines="2" />
          <SkeletonSection title="Education" :lines="3" />
        </template>
        <div class="running-actions">
          <button class="btn-secondary" :disabled="cancelling" @click="handleCancel">
            {{ cancelling ? 'Cancelling...' : 'Cancel Job' }}
          </button>
        </div>
      </template>

      <!-- Complete/failed/cancelled state -->
      <template v-else>
        <!-- Action buttons -->
        <div class="action-buttons">
          <button
            v-if="currentJob.status === 'complete'"
            class="btn-primary"
            :disabled="downloading"
            @click="handleDownload"
          >
            <LoadingSpinner v-if="downloading" class="btn-spinner" />
            {{ downloading ? 'Downloading...' : 'Download PDF' }}
          </button>

          <RegeneratePanel
            :current-model="currentJob.model"
            :current-creativity-level="currentJob.creativity_level"
            :current-notes="currentJob.user_notes"
            :current-model-id="currentJob.model_id"
            :current-reasoning-effort="currentJob.reasoning_effort"
            :disabled="regenerating"
            @regenerate="handleRegenerate"
          />

          <button
            class="btn-danger"
            :disabled="deleting"
            @click="handleDelete"
          >
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>

        <!-- CV Preview -->
        <CvPreview
          v-if="currentJob.status === 'complete' && currentJob.tailored_cv"
          :cv="currentJob.tailored_cv"
        />

        <!-- Failed state error -->
        <ErrorBanner
          v-if="currentJob.status === 'failed'"
          message="Generation failed. Try a different model or lower the creativity level."
          @retry="handleRegenerate"
        />
      </template>
    </div>

    <!-- Cover Letter Tab -->
    <div v-show="activeTab === 'cover-letter'" class="tab-panel">
      <CoverLetterSection
        v-if="currentJob.status === 'complete' || currentJob.cover_letter_text || currentJob.cl_history?.length"
        :job-id="jobId"
        :job-status="currentJob.status"
        :current-model="currentJob.model"
        :existing-cover-letter="currentJob.cover_letter_text ?? null"
        :existing-notes="currentJob.cover_letter_notes ?? null"
        :existing-cl-model="currentJob.cover_letter_model ?? null"
        :existing-cl-tone="currentJob.cover_letter_tone ?? null"
        :cl-history="currentJob.cl_history ?? null"
      />
      <p v-else-if="['complete', 'failed', 'cancelled'].includes(currentJob.status)" class="tab-empty-state">No cover letter yet. Paste in your notes and generate one.</p>
      <p v-else class="tab-empty-state">CV is still generating. Cover letter will be available after.</p>
    </div>

    <!-- Analysis Tab -->
    <div v-show="activeTab === 'analysis' && ['complete', 'failed', 'cancelled'].includes(currentJob.status)" class="tab-panel">
      <!-- Gap Analysis -->
      <section v-if="currentJob.gap_diff && currentJob.gap_diff.length > 0" class="analysis-section">
        <h3 class="section-heading">Gap Analysis</h3>
        <GapDiffTable :items="currentJob.gap_diff" />
      </section>

      <!-- Tailoring Notes -->
      <TailoringNotes
        v-if="currentJob.tailored_cv && currentJob.tailored_cv.tailoring_notes && currentJob.tailored_cv.tailoring_notes.length > 0"
        :notes="currentJob.tailored_cv.tailoring_notes"
      />

      <p v-if="!currentJob.gap_diff?.length && !currentJob.tailored_cv?.tailoring_notes?.length" class="tab-empty-state">
        Analysis runs automatically when your CV is generated.
      </p>
    </div>

    <!-- Job Listing Tab -->
    <div v-show="activeTab === 'job-listing'" class="tab-panel">
      <section class="analysis-section">
        <h3 class="section-heading">Job Listing</h3>
        <div class="listing-field">
          <label class="listing-label">Job Link</label>
          <input
            v-model="currentJob.job_link"
            type="url"
            class="listing-input"
            placeholder="https://..."
          />
        </div>
        <div class="listing-field">
          <label class="listing-label">Job Description</label>
          <textarea
            v-model="currentJob.job_text"
            class="listing-textarea"
            rows="16"
            placeholder="Paste the job listing here..."
          />
        </div>
        <div class="listing-actions">
          <button
            class="btn-secondary"
            :disabled="savingListing"
            @click="handleSaveListing"
          >
            {{ savingListing ? 'Saving...' : 'Save Changes' }}
          </button>
          <button
            class="btn-secondary"
            :disabled="!currentJob.job_text"
            @click="handleDownloadJobText"
          >
            Download .txt
          </button>
        </div>
      </section>
    </div>

  </div>
</template>

<style scoped>
/* Loading state */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 0;
}

/* Main detail layout */
.job-detail-view {
  display: flex;
  flex-direction: column;
}

/* Header */
.job-header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-bottom: 4px;
}

.job-link {
  display: inline-block;
  margin-bottom: 20px;
  font-size: 13px;
  color: var(--color-accent-primary);
  text-decoration: none;
  word-break: break-all;
}

.job-link:hover {
  text-decoration: underline;
}

.model-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 2px 8px;
}

.applied-toggle {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  background: var(--color-surface-1);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 150ms ease;
}
.applied-toggle:hover {
  border-color: var(--color-success-primary);
  color: var(--color-success-primary);
}
.applied-toggle--active {
  background: var(--color-success-secondary);
  border-color: var(--color-success-primary);
  color: var(--color-success-primary);
}

.applied-date {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-success-primary);
  background: var(--color-success-secondary);
  border: 1px solid var(--color-success-primary);
  border-radius: 4px;
  padding: 2px 8px;
}

.company-heading {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
}

/* Running state actions */
.running-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

/* Spinner + status text container */
.spinner-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 0;
}

.status-text {
  font-size: 14px;
  color: var(--color-text-secondary);
}

/* Tab bar */
.tab-bar {
  display: flex;
  gap: 0;
  height: 44px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 24px;
}

.tab-btn {
  height: 44px;
  padding: 0 20px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: color 150ms ease, border-color 150ms ease;
}

.tab-btn:hover {
  color: var(--color-text-primary);
}

.tab-btn--active {
  color: var(--color-accent-primary);
  border-bottom-color: var(--color-accent-primary);
}

.tab-panel {
  /* No animation — instant swap via v-show */
}

.tab-empty-state {
  font-size: 14px;
  color: var(--color-text-secondary);
  padding: 32px 0;
}

/* Action buttons row */
.action-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

/* Primary button (Download PDF) */
.btn-primary {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: var(--color-accent-primary);
  border: none;
  color: var(--color-text-inverted);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background-color 150ms ease;
}
.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-primary-hover);
}
.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Secondary button (Cancel Job) */
.btn-secondary {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  color: var(--color-text-primary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 150ms ease, background-color 150ms ease;
}
.btn-secondary:hover:not(:disabled) {
  background: var(--color-surface-3);
  border-color: var(--color-border);
}
.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Danger button (Delete) */
.btn-danger {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 150ms ease, color 150ms ease;
}
.btn-danger:hover:not(:disabled) {
  border-color: #dc2626;
  color: #dc2626;
}
.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Spinner inside primary button */
.btn-spinner {
  width: 16px !important;
  height: 16px !important;
  border-width: 2px !important;
}

/* CV version history */
.cv-history--top {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.history-heading {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: border-color 150ms ease, color 150ms ease, background-color 150ms ease;
  text-align: left;
}

.history-btn:hover {
  border-color: var(--color-accent-primary);
  color: var(--color-accent-primary);
  background-color: var(--color-surface-2);
}

.history-meta {
  font-weight: 400;
  font-size: 11px;
  color: var(--color-text-tertiary);
}

/* Analysis section headings */
.analysis-section {
  margin-bottom: 32px;
}

.section-heading {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 16px;
}

/* Job listing editor */
.listing-field {
  margin-bottom: 12px;
}

.listing-actions {
  display: flex;
  gap: 8px;
}

.listing-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.listing-input {
  width: 100%;
  padding: 8px 12px;
  background-color: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary);
  box-sizing: border-box;
}

.listing-input:focus {
  outline: none;
  border-color: var(--color-accent-primary);
}

.listing-textarea {
  width: 100%;
  padding: 12px;
  background-color: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  color: var(--color-text-primary);
  line-height: 1.6;
  resize: vertical;
  box-sizing: border-box;
}

.listing-textarea:focus {
  outline: none;
  border-color: var(--color-accent-primary);
}

/* Job listing text */
.job-text-content {
  font-size: 13px;
  color: var(--color-text-secondary);
  background: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}
</style>
