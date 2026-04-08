<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue'
import { storeToRefs } from 'pinia'
import ToneSelector from '@/components/ToneSelector.vue'
import ModelSelector from '@/components/ModelSelector.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { apiFetch } from '@/utils/apiFetch'
import { useJobStore } from '@/stores/jobStore'

const props = defineProps<{
  jobId: string
  jobStatus: string
  currentModel: string
  existingCoverLetter: string | null
  existingNotes: string | null
  existingClModel: string | null
  existingClTone: string | null
}>()

const store = useJobStore()
const { currentJob } = storeToRefs(store)

const selectedModel = ref(props.currentModel)
const tone = ref('professional')
const userNotes = ref(props.existingNotes ?? '')
const coverLetterText = ref(props.existingCoverLetter ?? '')
const generating = ref(false)
const saving = ref(false)
const copied = ref(false)
const showForm = ref(false)

const claudeCliAvailable = ref(true)
const claudeApiAvailable = ref(false)
const geminiAvailable = ref(false)
const openaiAvailable = ref(false)

// Detect if cover letter is generating in background (empty string = generating)
const isGeneratingInBackground = computed(() =>
  props.existingCoverLetter === '' && !coverLetterText.value
)

onMounted(async () => {
  // If we load the page and cover letter is generating, show spinner
  if (props.existingCoverLetter === '') {
    generating.value = true
    coverLetterText.value = ''
  }

  try {
    const res = await apiFetch('/api/config')
    const data = await res.json() as Record<string, unknown>
    claudeCliAvailable.value = data.claude_cli_available !== false
    claudeApiAvailable.value = data.claude_api_available === true
    geminiAvailable.value = data.gemini_available === true
    openaiAvailable.value = data.openai_available === true
  } catch { /* keep optimistic defaults */ }
})

// Sync cover letter from props — detect when background generation completes
watch(() => props.existingCoverLetter, (val) => {
  if (val && val.length > 0) {
    // Cover letter arrived — generation complete
    coverLetterText.value = val
    generating.value = false
    showForm.value = false
  } else if (val === null && generating.value) {
    // Generation failed — worker reset to null
    generating.value = false
  }
})

watch(() => props.existingNotes, (val) => {
  if (val !== null && val !== userNotes.value) {
    userNotes.value = val
  }
})

async function handleGenerate(): Promise<void> {
  generating.value = true
  coverLetterText.value = ''
  try {
    const result = await store.generateCoverLetter(
      props.jobId,
      selectedModel.value,
      tone.value,
      userNotes.value,
    )
    coverLetterText.value = result
    showForm.value = false
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Cover letter generation failed'
  } finally {
    generating.value = false
  }
}

async function handleCopy(): Promise<void> {
  await navigator.clipboard.writeText(coverLetterText.value)
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

async function handleSaveAndDownload(): Promise<void> {
  saving.value = true
  try {
    await store.saveCoverLetter(props.jobId, coverLetterText.value, userNotes.value)
    const companyName = currentJob.value?.company_name ?? 'Company'
    await store.downloadCoverLetterPdf(props.jobId, companyName)
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Save and download failed'
  } finally {
    saving.value = false
  }
}

function handleRegenerate(): void {
  coverLetterText.value = ''
  showForm.value = true
}
</script>

<template>
  <section class="cover-letter-section">

    <!-- Generating state: spinner -->
    <div v-if="generating" class="generating-state">
      <LoadingSpinner />
      <p class="generating-text">Generating cover letter...</p>
    </div>

    <!-- State 1: No cover letter yet, show generate trigger -->
    <div v-else-if="!coverLetterText && !showForm">
      <button class="btn-generate-trigger" @click="showForm = true">
        Generate Cover Letter
      </button>
    </div>

    <!-- State 2: Form visible (model + tone + generate, then optional notes) -->
    <div v-else-if="showForm && !coverLetterText" class="cover-letter-form">
      <div class="form-row">
        <ModelSelector
          v-model="selectedModel"
          :claude-cli-available="claudeCliAvailable"
          :claude-api-available="claudeApiAvailable"
          :gemini-available="geminiAvailable"
          :openai-available="openaiAvailable"
          :disabled="generating"
        />
        <ToneSelector v-model="tone" :disabled="generating" />
      </div>
      <button
        class="btn-generate"
        :disabled="generating"
        @click="handleGenerate"
      >
        Generate Cover Letter
      </button>
      <div class="form-field">
        <label class="field-label">Notes (optional)</label>
        <textarea
          v-model="userNotes"
          class="notes-textarea"
          placeholder="Add notes to guide the cover letter: 'mention I'm relocating to Berlin', 'highlight the K8s migration project', 'I know someone at this company'..."
          rows="3"
          :disabled="generating"
        />
      </div>
    </div>

    <!-- State 3: Cover letter generated — editable preview -->
    <div v-else-if="coverLetterText" class="cover-letter-preview">
      <div v-if="existingClModel || existingClTone" class="cl-meta">
        <span v-if="existingClModel" class="cl-badge">{{ { 'claude-haiku': 'Claude CLI', 'claude-api': 'Claude API', 'gemini-flash': 'Gemini', 'openai': 'OpenAI' }[existingClModel] || existingClModel }}</span>
        <span v-if="existingClTone" class="cl-badge">{{ existingClTone.charAt(0).toUpperCase() + existingClTone.slice(1) }}</span>
      </div>
      <textarea
        v-model="coverLetterText"
        class="cover-letter-editor"
        rows="20"
      />
      <div class="cover-letter-actions">
        <button class="btn-copy" :class="{ 'btn-copy--copied': copied }" @click="handleCopy">
          {{ copied ? 'Copied!' : 'Copy to Clipboard' }}
        </button>
        <button
          class="btn-save-download"
          :disabled="saving"
          @click="handleSaveAndDownload"
        >
          {{ saving ? 'Saving...' : 'Save & Download PDF' }}
        </button>
        <button
          class="btn-regenerate-cl"
          @click="handleRegenerate"
        >
          Regenerate
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.cover-letter-section {
}

.generating-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 0;
}

.generating-text {
  font-size: 14px;
  color: #6b7280;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
}

.btn-generate-trigger {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: #2563eb;
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.btn-generate-trigger:hover {
  background: #1d4ed8;
}

.cover-letter-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-start;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.notes-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  color: #111827;
  resize: vertical;
  box-sizing: border-box;
}

.notes-textarea:disabled {
  background: #f9fafb;
  color: #6b7280;
  cursor: not-allowed;
}

.btn-generate {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: #2563eb;
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background-color 150ms ease;
  align-self: flex-start;
}

.btn-generate:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cl-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.cl-badge {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  background: #f3f4f6;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 2px 8px;
}

.cover-letter-preview {
  display: flex;
  flex-direction: column;
}

.cover-letter-editor {
  width: 100%;
  min-height: 300px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.6;
  font-family: inherit;
  color: #111827;
  resize: vertical;
  box-sizing: border-box;
}

.cover-letter-actions {
  display: flex;
  flex-direction: row;
  gap: 8px;
  margin-top: 12px;
}

.btn-copy {
  height: 40px;
  padding: 0 20px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 150ms ease, color 150ms ease, background-color 150ms ease;
}

.btn-copy:hover:not(.btn-copy--copied) {
  border-color: #2563eb;
  color: #2563eb;
}

.btn-copy--copied {
  border-color: #16a34a;
  color: #16a34a;
}

.btn-save-download {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: #2563eb;
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.btn-save-download:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-save-download:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-regenerate-cl {
  height: 40px;
  padding: 0 20px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid #e2e8f0;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 150ms ease, color 150ms ease;
}

.btn-regenerate-cl:hover:not(:disabled) {
  border-color: #374151;
}

.btn-regenerate-cl:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
