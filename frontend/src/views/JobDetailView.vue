<script setup lang="ts">
import { ref, watch, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useJobStore } from '@/stores/jobStore'
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
const activeTab = ref<'cv' | 'cover-letter' | 'analysis'>('cv')

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
  if (currentJob.value && !['complete', 'failed', 'cancelled'].includes(currentJob.value.status)) {
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

async function handleRegenerate(model?: string, creativityLevel?: number) {
  if (!currentJob.value) return
  regenerating.value = true
  try {
    const newId = await store.regenerateJob(currentJob.value, model, creativityLevel)
    router.push(`/jobs/${newId}`)
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
      <button
        class="applied-toggle"
        :class="{ 'applied-toggle--active': currentJob.applied }"
        @click="store.toggleApplied(jobId)"
      >{{ currentJob.applied ? 'Applied' : 'Not Applied' }}</button>
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

    <!-- Zone 2: LOADING/RUNNING STATE (replaces tab area when not complete/failed/cancelled) -->
    <template v-if="!['complete', 'failed', 'cancelled'].includes(currentJob.status)">
      <!-- Spinner + status text: pending or running -->
      <div
        v-if="currentJob.status === 'pending' || currentJob.status === 'running'"
        class="spinner-container"
      >
        <LoadingSpinner />
        <p class="status-text">{{ statusText[currentJob.status] }}</p>
      </div>

      <!-- Skeleton sections: running -->
      <template v-if="currentJob.status === 'running'">
        <SkeletonSection title="Summary" :lines="3" />
        <SkeletonSection title="Experience" :lines="5" />
        <SkeletonSection title="Skills" :lines="2" />
        <SkeletonSection title="Education" :lines="3" />
      </template>

      <!-- Cancel Job button -->
      <div v-if="currentJob.status === 'pending' || currentJob.status === 'running'" class="running-actions">
        <button
          class="btn-secondary"
          :disabled="cancelling"
          @click="handleCancel"
        >
          {{ cancelling ? 'Cancelling...' : 'Cancel Job' }}
        </button>
      </div>
    </template>

    <!-- Zone 3: TAB BAR (only when complete, failed, or cancelled) -->
    <div v-if="['complete', 'failed', 'cancelled'].includes(currentJob.status)" class="tab-bar">
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
    </div>

    <!-- Zone 4: TAB PANELS -->

    <!-- CV Tab -->
    <div v-show="activeTab === 'cv' && ['complete', 'failed', 'cancelled'].includes(currentJob.status)" class="tab-panel">
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
          v-if="['complete', 'failed', 'cancelled'].includes(currentJob.status)"
          :current-model="currentJob.model"
          :current-creativity-level="currentJob.creativity_level"
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
    </div>

    <!-- Cover Letter Tab -->
    <div v-show="activeTab === 'cover-letter' && ['complete', 'failed', 'cancelled'].includes(currentJob.status)" class="tab-panel">
      <CoverLetterSection
        v-if="currentJob.status === 'complete'"
        :job-id="jobId"
        :job-status="currentJob.status"
        :current-model="currentJob.model"
        :existing-cover-letter="currentJob.cover_letter_text ?? null"
        :existing-notes="currentJob.cover_letter_notes ?? null"
      />
      <p v-else class="tab-empty-state">No cover letter yet. Paste in your notes and generate one.</p>
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

      <!-- Job Listing Text -->
      <section v-if="currentJob.job_text" class="analysis-section">
        <h3 class="section-heading">Job Listing</h3>
        <pre class="job-text-content">{{ currentJob.job_text }}</pre>
      </section>

      <p v-if="!currentJob.gap_diff?.length && !currentJob.tailored_cv?.tailoring_notes?.length && !currentJob.job_text" class="tab-empty-state">
        Analysis runs automatically when your CV is generated.
      </p>
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
  gap: 12px;
  margin-bottom: 4px;
}

.job-link {
  display: inline-block;
  margin-bottom: 20px;
  font-size: 13px;
  color: #2563eb;
  text-decoration: none;
  word-break: break-all;
}

.job-link:hover {
  text-decoration: underline;
}

.model-badge {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  background: #f3f4f6;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 2px 8px;
}

.applied-toggle {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 4px;
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #6b7280;
  cursor: pointer;
  transition: all 150ms ease;
}
.applied-toggle:hover {
  border-color: #16a34a;
  color: #16a34a;
}
.applied-toggle--active {
  background: #dcfce7;
  border-color: #16a34a;
  color: #16a34a;
}

.company-heading {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
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
  color: #6b7280;
}

/* Tab bar */
.tab-bar {
  display: flex;
  gap: 0;
  height: 44px;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 24px;
}

.tab-btn {
  height: 44px;
  padding: 0 20px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #6b7280;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: color 150ms ease, border-color 150ms ease;
}

.tab-btn:hover {
  color: #111827;
}

.tab-btn--active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}

.tab-panel {
  /* No animation — instant swap via v-show */
}

.tab-empty-state {
  font-size: 14px;
  color: #6b7280;
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
  background: #2563eb;
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background-color 150ms ease;
}
.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
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
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 150ms ease, color 150ms ease;
}
.btn-secondary:hover:not(:disabled) {
  border-color: #374151;
  color: #111827;
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
  border: 1px solid #e2e8f0;
  color: #6b7280;
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

/* Analysis section headings */
.analysis-section {
  margin-bottom: 32px;
}

.section-heading {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 16px;
}

/* Job listing text */
.job-text-content {
  font-size: 13px;
  color: #374151;
  background: #f8f9fa;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  max-height: 400px;
  overflow-y: auto;
}
</style>
