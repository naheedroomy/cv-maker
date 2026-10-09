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
const geminiWebAvailable = ref(false)

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
      geminiWebAvailable.value = data.gemini_web_available === true
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
    <header class="page-heading"><span class="page-kicker">FROM TEXT TO BASE CV / 03</span><h1 class="page-title">Bring your work <em>with you.</em></h1><p class="page-description">Upload a text file or paste your CV. We’ll organize it into a base CV you can use for future applications. For a PDF, copy the text from your PDF viewer first.</p></header>

    <div v-if="successMessage" class="banner banner--success" role="status">
      <span class="banner-icon">&#10003;</span>
      {{ successMessage }}
    </div>

    <div v-if="errorMessage" class="banner banner--error" role="alert">
      <span class="banner-icon">&#9888;</span>
      {{ errorMessage }}
    </div>

    <section class="converter-sheet" aria-label="Import your CV">
    <div class="sheet-topline"><span>01 — YOUR SOURCE TEXT</span><span>↗</span></div>
    <div class="converter-fields">
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
      :gemini-web-available="geminiWebAvailable"
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
      <span>{{ converting ? 'Organizing your CV…' : 'Create base CV' }}</span>
    </button>

    </div>
    </section>

    <!-- Parsed YAML preview -->
    <div v-if="yamlContent" class="yaml-preview">
      <h2 class="yaml-heading">Your generated base CV <span>(YAML)</span></h2>
      <pre class="yaml-content">{{ yamlContent }}</pre>
    </div>
  </div>
</template>

<style scoped>
.cv-converter-view { max-width: 800px; }
.page-heading { margin-bottom: 29px; }
.page-kicker { color: var(--color-text-secondary); font-size: 10px; font-weight: 800; letter-spacing: .13em; }
.page-title em { font-style: normal; text-decoration: underline; text-decoration-color: var(--color-highlight); text-decoration-thickness: .13em; }
.converter-sheet, .yaml-preview { background: var(--color-surface-1); border: 1px solid var(--color-border); border-radius: 5px; overflow: hidden; }
.sheet-topline { display: flex; justify-content: space-between; padding: 15px 26px; border-bottom: 1px solid var(--color-border); color: var(--color-text-secondary); font-size: 10px; font-weight: 800; letter-spacing: .09em; }
.converter-fields { padding: 27px 30px 30px; }
@media (max-width: 600px) { .converter-fields { padding: 22px 19px; } .sheet-topline { padding-inline: 19px; } }

.page-title {
  margin: 13px 0 8px;
  font-size: clamp(34px, 3.5vw, 52px);
  font-weight: 800;
  letter-spacing: -.055em;
  line-height: 1.12;
  color: var(--color-text-primary);
}

.page-description {
  font-size: 14px;
  color: var(--color-text-secondary);
  max-width: 560px;
  line-height: 1.6;
}

.page-description code {
  background: var(--color-surface-2);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: var(--color-text-secondary);
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
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-border);
}

.banner--error {
  background: var(--color-error-bg);
  color: var(--color-error-text);
  border: 1px solid var(--color-error-border);
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
  color: var(--color-text-primary);
  margin-bottom: 6px;
}

.required-star {
  color: var(--color-error);
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 6px;
}

.file-input {
  display: block;
  max-width: 100%;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.file-input::file-selector-button {
  margin-right: 12px;
  padding: 9px 13px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-surface-2);
  color: var(--color-text-primary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.file-input:focus-visible { outline: 2px solid var(--color-accent-primary); outline-offset: 3px; }

.file-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-textarea {
  display: block;
  width: 100%;
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
  box-sizing: border-box;
}

.field-textarea:focus {
  border-color: var(--color-accent-primary);
}

.field-textarea:disabled {
  background: var(--color-surface-2);
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

.convert-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 40px;
  padding: 0 24px;
  background: var(--color-accent-primary);
  color: var(--color-text-inverted);
  font-size: 14px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 150ms ease, opacity 150ms ease;
  margin-top: 8px;
}

.convert-btn:hover:not(:disabled) {
  background: var(--color-accent-primary-hover);
}

.convert-btn--disabled,
.convert-btn:disabled {
  background: var(--color-accent-primary);
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: var(--color-text-inverted);
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
  margin-top: 25px;
  padding: 25px 29px;
}

.yaml-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}
.yaml-heading span { color: var(--color-text-secondary); font-size: 12px; font-weight: 500; }

.yaml-content {
  font-size: 13px;
  color: var(--color-text-primary);
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  max-height: 500px;
  overflow: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
</style>
