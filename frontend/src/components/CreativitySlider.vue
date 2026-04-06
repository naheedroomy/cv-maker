<script setup lang="ts">
const props = defineProps<{
  modelValue: number
  disabled: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>()

const levels = [
  { value: 0, label: '0', hint: 'Strict — reorder only, zero content changes' },
  { value: 1, label: '1', hint: 'Conservative — emphasize and reframe existing content only' },
  { value: 2, label: '2', hint: 'Moderate — title tweaks, tech weaving, inferred experience (default)' },
  { value: 3, label: '3', hint: 'Forward — aggressively expand partial matches, more inferences' },
  { value: 4, label: '4', hint: 'Bold — fill gaps with plausible claims, speculative additions' },
  { value: 5, label: '5', hint: 'Creative — invent freely, maximize relevance at cost of accuracy' },
] as const

function select(value: number): void {
  if (props.disabled) return
  emit('update:modelValue', value)
}

function hintText(): string {
  const level = levels.find(l => l.value === props.modelValue)
  return level ? level.hint : ''
}
</script>

<template>
  <div class="creativity-slider">
    <label class="field-label">Creativity level</label>
    <div class="creativity-toggle" role="group" aria-label="Select creativity level">
      <button
        v-for="level in levels"
        :key="level.value"
        type="button"
        class="creativity-option"
        :class="{
          'creativity-option--active': modelValue === level.value,
        }"
        :disabled="disabled"
        :aria-pressed="modelValue === level.value"
        @click="select(level.value)"
      >
        {{ level.label }}
      </button>
    </div>
    <p
      class="creativity-hint"
      :class="{ 'creativity-hint--warning': modelValue >= 4 }"
    >
      {{ hintText() }}
    </p>
  </div>
</template>

<style scoped>
.creativity-slider {
  margin-bottom: 16px;
}

.field-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 6px;
}

.creativity-toggle {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.creativity-option {
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

.creativity-option:hover:not(.creativity-option--active):not(:disabled) {
  background: #f3f4f6;
}

.creativity-option--active {
  background: #2563eb;
  color: #ffffff;
}

.creativity-option:disabled {
  color: #6b7280;
  cursor: not-allowed;
}

.creativity-hint {
  font-size: 12px;
  color: #6b7280;
  margin-top: 6px;
  margin-bottom: 0;
}

.creativity-hint--warning {
  color: #dc2626;
}
</style>
