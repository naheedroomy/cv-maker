<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import ModelSelector from '@/components/ModelSelector.vue'
import CreativitySlider from '@/components/CreativitySlider.vue'

const props = defineProps<{
  currentModel: string
  currentCreativityLevel: number
  disabled: boolean
}>()

const emit = defineEmits<{
  (e: 'regenerate', model: string, creativityLevel: number): void
}>()

const panelOpen = ref(false)
const selectedModel = ref(props.currentModel)
const selectedCreativity = ref(props.currentCreativityLevel)

// Provider availability
const claudeApiAvailable = ref(false)
const geminiAvailable = ref(false)
const openaiAvailable = ref(false)

// Fetch provider config on mount
onMounted(() => {
  fetch('/api/config')
    .then(r => r.ok ? r.json() : {})
    .then(data => {
      claudeApiAvailable.value = data.claude_api_available === true
      geminiAvailable.value = data.gemini_available === true
      openaiAvailable.value = data.openai_available === true
    })
    .catch(() => {})
})

// Reset selections when navigating to a different job
watch(() => props.currentModel, (val) => {
  selectedModel.value = val
})
watch(() => props.currentCreativityLevel, (val) => {
  selectedCreativity.value = val
})

function handleRegenerate(): void {
  emit('regenerate', selectedModel.value, selectedCreativity.value)
  panelOpen.value = false
}
</script>

<template>
  <div class="regenerate-panel">
    <!-- Toggle button: always visible -->
    <button
      class="btn-regenerate-toggle"
      :disabled="disabled"
      @click="panelOpen = !panelOpen"
    >
      {{ disabled ? 'Regenerating...' : (panelOpen ? 'Cancel' : 'Regenerate') }}
    </button>

    <!-- Expandable panel -->
    <div v-if="panelOpen" class="regenerate-options">
      <ModelSelector
        v-model="selectedModel"
        :claude-api-available="claudeApiAvailable"
        :gemini-available="geminiAvailable"
        :openai-available="openaiAvailable"
        :disabled="disabled"
      />
      <CreativitySlider
        v-model="selectedCreativity"
        :disabled="disabled"
      />
      <button
        class="btn-regenerate-now"
        :disabled="disabled"
        @click="handleRegenerate"
      >
        Regenerate Now
      </button>
    </div>
  </div>
</template>

<style scoped>
.btn-regenerate-toggle {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: #f59e0b;
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 150ms ease;
}
.btn-regenerate-toggle:hover:not(:disabled) {
  background: #d97706;
}
.btn-regenerate-toggle:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.regenerate-options {
  margin-top: 12px;
  padding: 16px;
  background: #f8f9fa;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.btn-regenerate-now {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: #f59e0b;
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
  transition: background-color 150ms ease;
}
.btn-regenerate-now:hover:not(:disabled) {
  background: #d97706;
}
.btn-regenerate-now:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
