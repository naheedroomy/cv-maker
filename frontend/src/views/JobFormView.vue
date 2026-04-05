<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useJobStore } from '@/stores/jobStore'
import ErrorBanner from '@/components/ErrorBanner.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import ModelSelector from '@/components/ModelSelector.vue'

const router = useRouter()
const store = useJobStore()

const companyName = ref('')
const jobLink = ref('')
const jobText = ref('')
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const selectedModel = ref('claude-haiku')
const geminiAvailable = ref(false)
const openaiAvailable = ref(false)

const canSubmit = computed(
  () => companyName.value.trim() !== '' && jobText.value.trim() !== '' && !submitting.value,
)

onMounted(async () => {
  try {
    const res = await fetch('/api/config')
    if (res.ok) {
      const data = await res.json()
      geminiAvailable.value = data.gemini_available === true
      openaiAvailable.value = data.openai_available === true
    }
  } catch {
    // Fail safe: leave geminiAvailable as false
  }
})

async function handleSubmit(): Promise<void> {
  if (!canSubmit.value) return
  submitting.value = true
  errorMessage.value = null
  try {
    const id = await store.submitJob({
      company_name: companyName.value.trim(),
      job_link: jobLink.value.trim() || undefined,
      job_text: jobText.value.trim(),
      model: selectedModel.value,
    })
    await router.push('/jobs/' + id)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'An unexpected error occurred.'
  } finally {
    submitting.value = false
  }
}

function handleRetry(): void {
  errorMessage.value = null
}
</script>

<template>
  <div class="job-form-view">
    <h1 class="page-title">CV Maker</h1>

    <ErrorBanner
      v-if="errorMessage"
      :message="errorMessage"
      @retry="handleRetry"
    />

    <form class="job-form" @submit.prevent="handleSubmit" novalidate>
      <div class="field">
        <label for="company-name" class="field-label">
          Company name <span class="required-star" aria-hidden="true">*</span>
        </label>
        <input
          id="company-name"
          v-model="companyName"
          type="text"
          class="field-input"
          placeholder="e.g. Acme Corp"
          aria-required="true"
          :disabled="submitting"
        />
      </div>

      <div class="field">
        <label for="job-link" class="field-label">Job link (optional)</label>
        <input
          id="job-link"
          v-model="jobLink"
          type="url"
          class="field-input"
          placeholder="https://..."
          :disabled="submitting"
        />
      </div>

      <div class="field">
        <label for="job-text" class="field-label">
          Job description <span class="required-star" aria-hidden="true">*</span>
        </label>
        <textarea
          id="job-text"
          v-model="jobText"
          class="field-textarea"
          placeholder="Paste the full job listing here..."
          aria-required="true"
          :disabled="submitting"
        ></textarea>
      </div>

      <ModelSelector
        v-model="selectedModel"
        :gemini-available="geminiAvailable"
        :openai-available="openaiAvailable"
        :disabled="submitting"
      />

      <button
        type="submit"
        class="submit-btn"
        :disabled="!canSubmit"
        :class="{ 'submit-btn--disabled': !canSubmit }"
      >
        <LoadingSpinner v-if="submitting" class="btn-spinner" />
        <span>{{ submitting ? 'Submitting...' : 'Generate CV' }}</span>
      </button>
    </form>
  </div>
</template>

<style scoped>
.job-form-view {
  max-width: 640px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 24px;
}

.job-form {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.field {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
}

.required-star {
  color: #dc2626;
}

.field-input {
  display: block;
  width: 100%;
  height: 40px;
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  color: #111827;
  background: #ffffff;
  outline: none;
  transition: border-color 150ms ease;
}

.field-input:focus {
  border-color: #2563eb;
}

.field-input:disabled {
  background: #f8f9fa;
  color: #6b7280;
  cursor: not-allowed;
}

.field-textarea {
  display: block;
  width: 100%;
  height: 200px;
  padding: 8px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  color: #111827;
  background: #ffffff;
  outline: none;
  resize: vertical;
  transition: border-color 150ms ease;
}

.field-textarea:focus {
  border-color: #2563eb;
}

.field-textarea:disabled {
  background: #f8f9fa;
  color: #6b7280;
  cursor: not-allowed;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 40px;
  padding: 0 24px;
  background: #2563eb;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 150ms ease;
  align-self: flex-start;
  margin-top: 8px;
}

.submit-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.submit-btn--disabled,
.submit-btn:disabled {
  background: #93c5fd;
  cursor: not-allowed;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border-width: 2px;
}
</style>
