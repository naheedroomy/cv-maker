<script setup lang="ts">
import '@/assets/selector.css'

const props = defineProps<{
  modelValue: string
  claudeApiAvailable: boolean
  geminiAvailable: boolean
  openaiAvailable: boolean
  disabled: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const options = [
  { value: 'claude-api', label: 'Claude API', hint: 'Requires Anthropic API key (set in Settings)' },
  { value: 'gemini-flash', label: 'Gemini', hint: 'Requires Gemini API key (set in Settings)' },
  { value: 'openai', label: 'OpenAI', hint: 'Requires OpenAI API key (set in Settings)' },
] as const

function select(model: string): void {
  if (props.disabled) return
  if (isDisabledOption(model)) return
  emit('update:modelValue', model)
}

function hintText(): string {
  if (props.modelValue === 'claude-api' && !props.claudeApiAvailable) {
    return 'Set your Anthropic API key in Settings.'
  }
  if (props.modelValue === 'gemini-flash' && !props.geminiAvailable) {
    return 'Set your Gemini API key in Settings.'
  }
  if (props.modelValue === 'openai' && !props.openaiAvailable) {
    return 'Set your OpenAI API key in Settings.'
  }
  const opt = options.find(o => o.value === props.modelValue)
  return opt ? opt.hint : ''
}

function isDisabledOption(value: string): boolean {
  if (value === 'claude-api' && !props.claudeApiAvailable) return true
  if (value === 'gemini-flash' && !props.geminiAvailable) return true
  if (value === 'openai' && !props.openaiAvailable) return true
  return false
}
</script>

<template>
  <div class="model-selector">
    <label class="field-label">AI model</label>
    <div class="pill-group" role="group" aria-label="Select AI model">
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        class="pill-option"
        :class="{
          'pill-option--active': modelValue === opt.value,
          'pill-option--disabled': isDisabledOption(opt.value),
        }"
        :disabled="disabled || isDisabledOption(opt.value)"
        :aria-pressed="modelValue === opt.value"
        @click="select(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>
    <p class="field-hint">{{ hintText() }}</p>
  </div>
</template>

<style scoped>
.model-selector {
  margin-bottom: 16px;
}
</style>
