<script setup lang="ts">
import { ref } from 'vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const props = defineProps<{
  uploading: boolean
  uploadProgress: string
}>()

const emit = defineEmits<{
  upload: [file: File, options?: { provider: string; model: string }]
}>()

const VISION_MODELS = [
  { label: 'Gemini 2.5 Flash (Default)', model: 'gemini-2.5-flash', provider: 'gemini' },
  { label: 'Gemini 2.5 Pro', model: 'gemini-2.5-pro', provider: 'gemini' },
  { label: 'OpenAI GPT-4o', model: 'gpt-4o', provider: 'openai' },
  { label: 'OpenAI GPT-4o-mini', model: 'gpt-4o-mini', provider: 'openai' },
] as const

const selectedModel = ref('gemini-2.5-flash')
const isDragOver = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

function onDragOver(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = true
}

function onDragLeave() {
  isDragOver.value = false
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) handleFile(file)
}

function onFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) handleFile(file)
  // Reset input so same file can be re-uploaded
  input.value = ''
}

function handleFile(file: File) {
  if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
    alert('Please select a PDF file.')
    return
  }
  const match = VISION_MODELS.find((m) => m.model === selectedModel.value) ?? VISION_MODELS[0]
  emit('upload', file, { provider: match.provider, model: match.model })
}

function openFilePicker() {
  if (props.uploading) return
  fileInputRef.value?.click()
}
</script>

<template>
  <div
    class="drop-zone"
    :class="{ 'drop-zone--dragover': isDragOver, 'drop-zone--uploading': uploading }"
    role="button"
    :aria-disabled="uploading"
    :tabindex="uploading ? -1 : 0"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    @click="openFilePicker"
    @keydown.enter="openFilePicker"
    @keydown.space.prevent="openFilePicker"
  >
    <input
      ref="fileInputRef"
      type="file"
      accept=".pdf,application/pdf"
      class="file-input"
      @change="onFileInputChange"
    />

    <div v-if="uploading" class="upload-state">
      <LoadingSpinner />
      <span class="upload-text">{{ uploadProgress || 'Parsing PDF...' }}</span>
    </div>

    <div v-else class="idle-state">
      <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
      </svg>
      <p class="drop-title">Drop your CV (PDF) here or click to browse</p>
      <p class="drop-subtitle">PDF files only (max 10MB)</p>

      <div class="model-picker-container" @click.stop @keydown.stop>
        <label for="vision-model-select" class="model-picker-label">Parser Model:</label>
        <select
          id="vision-model-select"
          v-model="selectedModel"
          class="model-picker-select"
          :disabled="uploading"
          @click.stop
        >
          <option v-for="item in VISION_MODELS" :key="item.model" :value="item.model">
            {{ item.label }}
          </option>
        </select>
      </div>
    </div>
  </div>
</template>

<style scoped>
.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  padding: 36px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
  background-color: var(--color-surface-1);
  user-select: none;
}

.drop-zone:hover:not(.drop-zone--uploading) {
  border-color: var(--color-accent-primary);
  background-color: var(--color-accent-secondary);
}

.drop-zone--dragover {
  border-color: var(--color-accent-primary);
  background-color: var(--color-accent-secondary);
}

.drop-zone--uploading {
  cursor: default;
  opacity: 0.8;
}

.file-input {
  display: none;
}

.idle-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--color-text-tertiary);
}

.upload-icon {
  width: 40px;
  height: 40px;
  color: var(--color-text-tertiary);
}

.drop-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin: 0;
}

.drop-subtitle {
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin: 0;
}

.model-picker-container {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  padding: 6px 12px;
  background-color: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  cursor: default;
}

.model-picker-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.model-picker-select {
  background-color: var(--color-surface-1);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s ease;
}

.model-picker-select:focus {
  border-color: var(--color-accent-primary);
}

.upload-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-text {
  font-size: 14px;
  color: var(--color-text-tertiary);
}
</style>
