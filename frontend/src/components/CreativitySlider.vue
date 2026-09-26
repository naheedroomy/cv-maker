<script setup lang="ts">
import '@/assets/selector.css'

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
  { value: 2, label: '2', hint: 'Balanced — standard ATS tailoring, tech weaving, inferred experience (default)' },
  { value: 3, label: '3', hint: 'Selective — swap equivalent tech in one role, no new claims' },
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
    <div class="pill-group" role="group" aria-label="Select creativity level">
      <button
        v-for="level in levels"
        :key="level.value"
        type="button"
        class="pill-option"
        :class="{
          'pill-option--active': modelValue === level.value,
        }"
        :disabled="disabled"
        :aria-pressed="modelValue === level.value"
        @click="select(level.value)"
      >
        {{ level.label }}
      </button>
    </div>
    <p class="field-hint">
      {{ hintText() }}
    </p>
  </div>
</template>

<style scoped>
.creativity-slider {
  margin-bottom: 16px;
}
</style>
