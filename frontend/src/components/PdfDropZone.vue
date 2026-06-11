<script setup lang="ts">
import { ref } from 'vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const props = defineProps<{
  uploading: boolean
  uploadProgress: string
}>()

const emit = defineEmits<{
  upload: [file: File]
}>()

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
  emit('upload', file)
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
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    @click="openFilePicker"
    role="button"
    :aria-disabled="uploading"
    :tabindex="uploading ? -1 : 0"
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
      <p class="drop-subtitle">PDF files only</p>
    </div>
  </div>
</template>

<style scoped>
.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  padding: 48px 24px;
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
