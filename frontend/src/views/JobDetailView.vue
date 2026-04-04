<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useJobStore } from '@/stores/jobStore'
import StatusBadge from '@/components/StatusBadge.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import SkeletonSection from '@/components/SkeletonSection.vue'
import CvPreview from '@/components/CvPreview.vue'
import GapDiffTable from '@/components/GapDiffTable.vue'
import TailoringNotes from '@/components/TailoringNotes.vue'

const route = useRoute()
const store = useJobStore()
const { currentJob, error } = storeToRefs(store)
const jobId = route.params.id as string

const cancelling = ref(false)
const downloading = ref(false)

const statusText: Record<string, string> = {
  pending: 'Analyzing job...',
  running: 'Generating tailored CV...',
  complete: 'CV ready',
  failed: 'Generation failed',
  cancelled: 'Cancelled',
}

onMounted(async () => {
  await store.fetchJob(jobId)
  if (currentJob.value && !['complete', 'failed', 'cancelled'].includes(currentJob.value.status)) {
    store.openSSE(jobId)
  }
})

onUnmounted(() => {
  store.closeSSE()
})

async function handleCancel() {
  cancelling.value = true
  try {
    await store.cancelJob(jobId)
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
    await store.downloadPdf(jobId, currentJob.value.company_name)
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Download failed'
  } finally {
    downloading.value = false
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
    <!-- Header: company name + status badge -->
    <div class="job-header">
      <h2 class="company-heading">{{ currentJob.company_name }}</h2>
      <StatusBadge :status="currentJob.status" />
    </div>

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
    </div>

    <!-- Error banner: failed status or store error -->
    <ErrorBanner
      v-if="error"
      :message="error"
      @retry="store.fetchJob(jobId)"
    />
    <ErrorBanner
      v-else-if="currentJob.status === 'failed'"
      message="The CV generation failed. Please try again."
      @retry="store.fetchJob(jobId)"
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
  margin-bottom: 24px;
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

.gap-heading {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 16px;
}
</style>
