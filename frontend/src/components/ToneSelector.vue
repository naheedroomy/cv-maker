<script setup lang="ts">
import '@/assets/selector.css'

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
    <div class="pill-group" role="group" aria-label="Select cover letter tone">
      <button
        v-for="opt in options"
        :key="opt.value"
        type="button"
        class="pill-option"
        :class="{ 'pill-option--active': modelValue === opt.value }"
        :disabled="disabled"
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
.tone-selector {
  margin-bottom: 16px;
}
</style>
