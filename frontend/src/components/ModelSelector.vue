<script setup lang="ts">
const props = defineProps<{
  modelValue: string
  geminiAvailable: boolean
  openaiAvailable: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const options = [
  { value: 'claude-haiku', label: 'Claude Haiku', hint: 'Fast and free — uses your Claude subscription' },
  { value: 'gemini-flash', label: 'Gemini Flash-Lite', hint: 'Fast and cheap — requires a GEMINI_API_KEY' },
  { value: 'openai', label: 'OpenAI', hint: 'Works with any OpenAI-compatible API endpoint (Groq, Together AI, Ollama, etc.)' },
] as const

function select(model: string): void {
  if (props.disabled) return
  if (model === 'gemini-flash' && !props.geminiAvailable) return
  if (model === 'openai' && !props.openaiAvailable) return
  emit('update:modelValue', model)
}

function hintText(): string {
  if (props.modelValue === 'gemini-flash' && !props.geminiAvailable) {
    return 'Gemini requires a GEMINI_API_KEY — not configured.'
  }
  if (props.modelValue === 'openai' && !props.openaiAvailable) {
    return 'OpenAI requires OPENAI_API_KEY — not configured.'
  }
  const opt = options.find(o => o.value === props.modelValue)
  return opt ? opt.hint : ''
}

function isDisabledOption(value: string): boolean {
  if (value === 'gemini-flash' && !props.geminiAvailable) return true
  if (value === 'openai' && !props.openaiAvailable) return true
  return false
}
</script>

<template>
  <div class="model-selector">
    <label class="field-label">AI model</label>
    <div class="model-toggle" role="group" aria-label="Select AI model">
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        class="model-option"
        :class="{
          'model-option--active': modelValue === opt.value,
          'model-option--disabled': isDisabledOption(opt.value),
        }"
        :disabled="disabled || isDisabledOption(opt.value)"
        :aria-pressed="modelValue === opt.value"
        @click="select(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>
    <p class="model-hint">{{ hintText() }}</p>
  </div>
</template>

<style scoped>
.model-selector {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
}

.model-toggle {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.model-option {
  height: 32px;
  padding: 0 16px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.model-option:hover:not(.model-option--active):not(.model-option--disabled) {
  background: #f3f4f6;
}

.model-option--active {
  background: #2563eb;
  color: #ffffff;
}

.model-option--disabled {
  color: #6b7280;
  cursor: not-allowed;
}

.model-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 6px;
  margin-bottom: 0;
}
</style>
