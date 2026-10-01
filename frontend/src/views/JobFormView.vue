<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useJobStore } from '@/stores/jobStore'
import { useCvStore } from '@/stores/cvStore'
import ErrorBanner from '@/components/ErrorBanner.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import ModelSelector from '@/components/ModelSelector.vue'
import CreativitySlider from '@/components/CreativitySlider.vue'
import { apiFetch } from '@/utils/apiFetch'

const router = useRouter()
const store = useJobStore()
const cvStore = useCvStore()

const companyName = ref('')
const jobLink = ref('')
const jobText = ref('')
const userNotes = ref('')
const selectedBaseCvId = ref('')
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const selectedModel = ref('gemini-flash')
const selectedModelId = ref('')
const selectedReasoningEffort = ref('auto')
const selectedCreativity = ref(2)
const claudeApiAvailable = ref(false)
const geminiAvailable = ref(false)
const openaiAvailable = ref(false)
const geminiWebAvailable = ref(false)

const canSubmit = computed(
  () => companyName.value.trim() !== '' && jobText.value.trim() !== '' && !submitting.value,
)

watch(
  () => cvStore.baseCvs,
  (cvs) => {
    if (cvs.length > 0 && (!selectedBaseCvId.value || !cvs.some((c) => c.id === selectedBaseCvId.value))) {
      const def = cvs.find((c) => c.is_default) || cvs[0]
      if (def) {
        selectedBaseCvId.value = def.id
      }
    }
  },
  { immediate: true },
)

onMounted(async () => {
  cvStore.fetchBaseCvs()
  try {
    const res = await apiFetch('/api/config')
    if (res.ok) {
      const data = await res.json()
      claudeApiAvailable.value = data.claude_api_available === true
      geminiAvailable.value = data.gemini_available === true
      openaiAvailable.value = data.openai_available === true
      geminiWebAvailable.value = data.gemini_web_available === true
      // Auto-select first available model if default is unavailable
      if (!geminiAvailable.value && selectedModel.value === 'gemini-flash') {
        if (claudeApiAvailable.value) selectedModel.value = 'claude-api'
        else if (openaiAvailable.value) selectedModel.value = 'openai'
      }
    }
  } catch {
    // Fail safe: leave claude CLI as true (optimistic)
  }
})

async function handleSubmit(): Promise<void> {
  if (!canSubmit.value) return
  submitting.value = true
  errorMessage.value = null
  try {
    const id = await store.submitJob({
      company_name: companyName.value.trim(),
      job_link: jobLink.value.trim(),
      job_text: jobText.value.trim(),
      model: selectedModel.value,
      model_id: selectedModelId.value || undefined,
      reasoning_effort: selectedReasoningEffort.value || undefined,
      creativity_level: selectedCreativity.value,
      user_notes: userNotes.value.trim(),
      base_cv_id: selectedBaseCvId.value || undefined,
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

      <div class="field">
        <label for="user-notes" class="field-label">Generation notes (optional)</label>
        <textarea
          id="user-notes"
          v-model="userNotes"
          class="field-textarea field-textarea--small"
          placeholder="Optional instructions: emphasize platform work, keep this under two pages, include SQS if supported by my CV."
          :disabled="submitting"
        ></textarea>
      </div>

      <div v-if="cvStore.baseCvs.length > 0" class="field">
        <label for="base-cv-select" class="field-label">Base CV</label>
        <select id="base-cv-select" v-model="selectedBaseCvId" class="field-select" :disabled="submitting">
          <option v-for="cv in cvStore.baseCvs" :key="cv.id" :value="cv.id">
            {{ cv.name }} {{ cv.is_default ? '(Default)' : '' }}
          </option>
        </select>
      </div>

      <ModelSelector
        v-model="selectedModel"
        v-model:model-id="selectedModelId"
        v-model:reasoning-effort="selectedReasoningEffort"
        :claude-api-available="claudeApiAvailable"
        :gemini-available="geminiAvailable"
        :openai-available="openaiAvailable"
        :gemini-web-available="geminiWebAvailable"
        :disabled="submitting"
        :show-model-details="true"
      />

      <CreativitySlider
        v-model="selectedCreativity"
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
  color: var(--color-text-primary);
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
  color: var(--color-text-primary);
  margin-bottom: 6px;
}

.required-star {
  color: var(--color-error);
}

.field-input,
.field-select {
  display: block;
  width: 100%;
  height: 40px;
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary);
  background: var(--color-surface-1);
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms ease;
}

.field-input:focus,
.field-select:focus {
  border-color: var(--color-accent-primary);
}

.field-input:disabled,
.field-select:disabled {
  background: var(--color-surface-2);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.field-textarea {
  display: block;
  width: 100%;
  height: 200px;
  padding: 8px 16px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary);
  background: var(--color-surface-1);
  outline: none;
  resize: vertical;
  transition: border-color 150ms ease;
}

.field-textarea:focus {
  border-color: var(--color-accent-primary);
}

.field-textarea:disabled {
  background: var(--color-surface-2);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.field-textarea--small {
  height: 80px;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 40px;
  padding: 0 24px;
  background: var(--color-accent-primary);
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
  background: var(--color-accent-primary-hover);
}

.submit-btn--disabled,
.submit-btn:disabled {
  background: var(--color-accent-primary);
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border-width: 2px;
}
</style>
