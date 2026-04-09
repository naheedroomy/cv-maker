<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import ModelSelector from '@/components/ModelSelector.vue'
import { apiFetch } from '@/utils/apiFetch'

const cvText = ref('')
const converting = ref(false)
const successMessage = ref<string | null>(null)
const errorMessage = ref<string | null>(null)
const yamlContent = ref<string | null>(null)
const selectedModel = ref('gemini-flash')
const claudeApiAvailable = ref(false)
const geminiAvailable = ref(false)
const openaiAvailable = ref(false)

const canConvert = computed(
  () => cvText.value.trim() !== '' && !converting.value,
)

onMounted(async () => {
  try {
    const res = await apiFetch('/api/config')
    if (res.ok) {
      const data = await res.json()
      claudeApiAvailable.value = data.claude_api_available === true
      geminiAvailable.value = data.gemini_available === true
      openaiAvailable.value = data.openai_available === true
    }
  } catch {}
})

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (!file.name.endsWith('.txt')) {
    errorMessage.value = 'Only .txt files are supported for upload. For PDFs, please copy and paste your CV text into the textarea below.'
    input.value = ''
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    cvText.value = (e.target?.result as string) ?? ''
    successMessage.value = null
    errorMessage.value = null
    yamlContent.value = null
  }
  reader.onerror = () => {
    errorMessage.value = 'Failed to read the file. Please paste your CV text instead.'
  }
  reader.readAsText(file)
}

async function handleConvert(): Promise<void> {
  if (!canConvert.value) return
  converting.value = true
  successMessage.value = null
  errorMessage.value = null
  yamlContent.value = null

  try {
    const response = await apiFetch('/api/cv/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cv_text: cvText.value.trim(), model: selectedModel.value }),
    })

    if (!response.ok) {
      throw new Error(`Server error: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()

    if (data.success) {
      const name = data.contact_name ? ` for ${data.contact_name}` : ''
      successMessage.value = `${data.message}${name}.`
      yamlContent.value = data.yaml_content || null
    } else {
      errorMessage.value = data.message || 'Conversion failed. Please try again.'
    }
  } catch (err) {
    if (err instanceof Error && err.message.startsWith('Server error:')) {
      errorMessage.value = err.message
    } else {
      errorMessage.value = 'Network error — could not reach the server. Is the backend running?'
    }
  } finally {
    converting.value = false
  }
}
</script>

<template>
  <div class="cv-converter-view">
    <h1 class="page-title">Import Base CV</h1>
    <p class="page-description">
      Upload a <strong>.txt</strong> file or paste your existing CV text to generate your
      <code>base_cv.yaml</code>. For PDFs, copy the text from your PDF viewer and paste it below.
    </p>

    <div v-if="successMessage" class="banner banner--success" role="status">
      <span class="banner-icon">&#10003;</span>
      {{ successMessage }}
    </div>

    <div v-if="errorMessage" class="banner banner--error" role="alert">
      <span class="banner-icon">&#9888;</span>
      {{ errorMessage }}
    </div>

    <div class="field">
      <label for="cv-file" class="field-label">Upload CV file (.txt)</label>
      <input
        id="cv-file"
        type="file"
        accept=".txt"
        class="file-input"
        :disabled="converting"
        @change="handleFileChange"
      />
      <p class="field-hint">Selecting a file will populate the text area below.</p>
    </div>

    <div class="field">
      <label for="cv-text" class="field-label">
        CV text <span class="required-star" aria-hidden="true">*</span>
      </label>
      <textarea
        id="cv-text"
        v-model="cvText"
        class="field-textarea"
        placeholder="Paste your CV text here..."
        :disabled="converting"
        rows="14"
      ></textarea>
    </div>

    <ModelSelector
      v-model="selectedModel"
      :claude-api-available="claudeApiAvailable"
      :gemini-available="geminiAvailable"
      :openai-available="openaiAvailable"
      :disabled="converting"
    />

    <button
      type="button"
      class="convert-btn"
      :disabled="!canConvert"
      :class="{ 'convert-btn--disabled': !canConvert }"
      @click="handleConvert"
    >
      <span v-if="converting" class="spinner" aria-hidden="true"></span>
      <span>{{ converting ? 'Converting...' : 'Convert to YAML' }}</span>
    </button>

    <!-- Parsed YAML preview -->
    <div v-if="yamlContent" class="yaml-preview">
      <h3 class="yaml-heading">Generated base_cv.yaml</h3>
      <pre class="yaml-content">{{ yamlContent }}</pre>
    </div>
  </div>
</template>

<style scoped>
.cv-converter-view {
  max-width: 640px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 8px;
}

.page-description {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 24px;
  line-height: 1.6;
}

.page-description code {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #374151;
}

.banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.5;
}

.banner--success {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
}

.banner--error {
  background: #fee2e2;
  color: #7f1d1d;
  border: 1px solid #fca5a5;
}

.banner-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
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

.field-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 6px;
}

.file-input {
  display: block;
  font-size: 14px;
  font-family: inherit;
  color: #374151;
  cursor: pointer;
}

.file-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-textarea {
  display: block;
  width: 100%;
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
  box-sizing: border-box;
}

.field-textarea:focus {
  border-color: #2563eb;
}

.field-textarea:disabled {
  background: #f8f9fa;
  color: #6b7280;
  cursor: not-allowed;
}

.convert-btn {
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
  margin-top: 8px;
}

.convert-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.convert-btn--disabled,
.convert-btn:disabled {
  background: #93c5fd;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* YAML preview */
.yaml-preview {
  margin-top: 32px;
}

.yaml-heading {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 12px;
}

.yaml-content {
  font-size: 13px;
  color: #374151;
  background: #f8f9fa;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  max-height: 500px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
</style>
