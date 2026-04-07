<script setup lang="ts">
const props = defineProps<{
  modelValue: string
  disabled: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const options = [
  { value: 'formal', label: 'Formal', hint: 'Traditional corporate style with formal greetings and professional closings' },
  { value: 'professional', label: 'Professional', hint: 'Clear and direct, leads with specifics, no fluff' },
  { value: 'confident', label: 'Confident', hint: 'Assertive with specific achievements, owns the work' },
  { value: 'direct', label: 'Direct', hint: 'Facts only, no warmth or flair, lets the work speak' },
  { value: 'casual', label: 'Casual', hint: 'Conversational with personality, uses contractions' },
] as const

function select(tone: string): void {
  if (props.disabled) return
  emit('update:modelValue', tone)
}

function hintText(): string {
  const opt = options.find(o => o.value === props.modelValue)
  return opt ? opt.hint : ''
}
</script>

<template>
  <div class="tone-selector">
    <label class="field-label">Tone</label>
    <div class="tone-toggle" role="group" aria-label="Select cover letter tone">
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        class="tone-option"
        :class="{ 'tone-option--active': modelValue === opt.value }"
        :disabled="disabled"
        :aria-pressed="modelValue === opt.value"
        @click="select(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>
    <p class="tone-hint">{{ hintText() }}</p>
  </div>
</template>

<style scoped>
.tone-selector {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
}

.tone-toggle {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.tone-option {
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

.tone-option:hover:not(.tone-option--active):not(:disabled) {
  background: #f3f4f6;
}

.tone-option--active {
  background: #2563eb;
  color: #ffffff;
}

.tone-option:disabled {
  color: #6b7280;
  cursor: not-allowed;
}

.tone-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 6px;
  margin-bottom: 0;
}
</style>
