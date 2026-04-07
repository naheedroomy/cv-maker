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
    <!-- Header: company name + status badge + model -->
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

    <!-- Action buttons -->
    <div class="action-buttons">
      <!-- Cancel Job: visible when pending or running -->
      <button
        v-if="currentJob.status === 'pending' || currentJob.status === 'running'"
        class="btn-cancel"
        :disabled="cancelling"
        @click="handleCancel"
      >
        {{ cancelling ? 'Cancelling...' : 'Cancel Job' }}
      </button>

      <!-- Download PDF: visible only when complete -->
      <button
        v-if="currentJob.status === 'complete'"
        class="btn-download"
        :disabled="downloading"
        @click="handleDownload"
      >
        <LoadingSpinner v-if="downloading" class="btn-spinner" />
        {{ downloading ? 'Downloading...' : 'Download PDF' }}
      </button>

      <!-- Regenerate panel: visible on complete, failed, or cancelled -->
      <RegeneratePanel
        v-if="['complete', 'failed', 'cancelled'].includes(currentJob.status)"
        :current-model="currentJob.model"
        :current-creativity-level="currentJob.creativity_level"
        :disabled="regenerating"
        @regenerate="handleRegenerate"
      />

      <!-- Delete Job: always visible -->
      <button
        class="btn-delete"
        :disabled="deleting"
        @click="handleDelete"
      >
        {{ deleting ? 'Deleting...' : 'Delete' }}
      </button>
    </div>

    <!-- Error banner: failed status or store error -->
    <ErrorBanner
      v-if="error"
      :message="error"
      @retry="handleRegenerate"
    />
    <ErrorBanner
      v-else-if="currentJob.status === 'failed'"
      message="The CV generation failed. Click retry to regenerate."
      @retry="handleRegenerate"
    />

    <!-- Spinner + status text: pending or running -->
    <div
      v-if="currentJob.status === 'pending' || currentJob.status === 'running'"
      class="spinner-container"
    >
      <LoadingSpinner />
      <p class="status-text">{{ statusText[currentJob.status] }}</p>
    </div>

    <!-- Skeleton sections: running (before complete) -->
    <template v-if="currentJob.status === 'running'">
      <SkeletonSection title="Summary" :lines="3" />
      <SkeletonSection title="Experience" :lines="5" />
      <SkeletonSection title="Skills" :lines="2" />
      <SkeletonSection title="Education" :lines="3" />
    </template>

    <!-- CV Preview: complete with tailored_cv -->
    <CvPreview
      v-if="currentJob.status === 'complete' && currentJob.tailored_cv"
      :cv="currentJob.tailored_cv"
    />

    <!-- Gap Analysis: complete with gap_diff -->
    <section
      v-if="currentJob.gap_diff && currentJob.gap_diff.length > 0"
      class="gap-analysis-section"
    >
      <h3 class="gap-heading">Gap Analysis</h3>
      <GapDiffTable :items="currentJob.gap_diff" />
    </section>

    <!-- AI Tailoring Notes -->
    <TailoringNotes
      v-if="currentJob.tailored_cv && currentJob.tailored_cv.tailoring_notes && currentJob.tailored_cv.tailoring_notes.length > 0"
      :notes="currentJob.tailored_cv.tailoring_notes"
    />

    <!-- Cover Letter Section: visible when job is complete (per D-01) -->
    <CoverLetterSection
      v-if="currentJob.status === 'complete'"
      :job-id="jobId"
      :job-status="currentJob.status"
      :current-model="currentJob.model"
      :existing-cover-letter="currentJob.cover_letter_text ?? null"
      :existing-notes="currentJob.cover_letter_notes ?? null"
    />

    <!-- Job Listing Text -->
    <section
      v-if="currentJob.job_text"
      class="job-text-section"
    >
      <h3 class="section-heading">Job Listing</h3>
      <pre class="job-text-content">{{ currentJob.job_text }}</pre>
    </section>
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

/* Action buttons row */
.action-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

/* Cancel button */
.btn-cancel {
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
.btn-cancel:hover:not(:disabled) {
  border-color: #dc2626;
  color: #dc2626;
}
.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Download PDF button */
.btn-download {
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
.btn-download:hover:not(:disabled) {
  background: #1d4ed8;
}
.btn-download:disabled {
  background: #93c5fd;
  cursor: not-allowed;
}

/* Spinner inside download button */
.btn-spinner {
  width: 16px !important;
  height: 16px !important;
  border-width: 2px !important;
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

/* Gap analysis section */
.gap-analysis-section {
  margin-top: 48px;
}

.gap-heading,
.section-heading {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 16px;
}

/* Delete button */
.btn-delete {
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
.btn-delete:hover:not(:disabled) {
  border-color: #dc2626;
  color: #dc2626;
}
.btn-delete:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Job listing text */
.job-text-section {
  margin-top: 48px;
}

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
