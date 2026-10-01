<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useCvStore } from '@/stores/cvStore'
import ModelSelector from '@/components/ModelSelector.vue'
import CreativitySlider from '@/components/CreativitySlider.vue'
import { apiFetch } from '@/utils/apiFetch'

const props = defineProps<{
  currentModel: string
  currentCreativityLevel: number
  disabled: boolean
  currentNotes?: string | null
  currentModelId?: string | null
  currentReasoningEffort?: string | null
  currentBaseCvId?: string | null
}>()

const emit = defineEmits<{
  (
    e: 'regenerate',
    model: string,
    creativityLevel: number,
    userNotes?: string,
    modelId?: string,
    reasoningEffort?: string,
    baseCvId?: string,
  ): void
}>()

const cvStore = useCvStore()

const panelOpen = ref(false)
const selectedModel = ref(props.currentModel)
const selectedModelId = ref(props.currentModelId ?? '')
const selectedReasoningEffort = ref(props.currentReasoningEffort ?? 'auto')
const selectedCreativity = ref(Math.min(3, props.currentCreativityLevel))
const userNotes = ref(props.currentNotes ?? '')
const selectedBaseCvId = ref(props.currentBaseCvId ?? '')

// Provider availability
const claudeApiAvailable = ref(false)
const geminiAvailable = ref(false)
const openaiAvailable = ref(false)
const geminiWebAvailable = ref(false)

// Fetch provider config on mount and base CVs if needed
onMounted(() => {
  if (cvStore.baseCvs.length === 0) {
    cvStore.fetchBaseCvs()
  }
  apiFetch('/api/config')
    .then(r => r.ok ? r.json() : {})
    .then((data: Record<string, unknown>) => {
      claudeApiAvailable.value = data.claude_api_available === true
      geminiAvailable.value = data.gemini_available === true
      openaiAvailable.value = data.openai_available === true
      geminiWebAvailable.value = data.gemini_web_available === true
    })
    .catch(() => {})
})

// Reset selections when navigating to a different job
watch(() => props.currentModel, (val) => {
  selectedModel.value = val
})
watch(() => props.currentCreativityLevel, (val) => {
  selectedCreativity.value = Math.min(3, val)
})
watch(() => props.currentNotes, (val) => {
  userNotes.value = val ?? ''
})
watch(() => props.currentModelId, (val) => {
  selectedModelId.value = val ?? ''
})
watch(() => props.currentReasoningEffort, (val) => {
  selectedReasoningEffort.value = val ?? 'auto'
})
watch(() => props.currentBaseCvId, (val) => {
  selectedBaseCvId.value = val ?? ''
})
watch(
  () => cvStore.baseCvs,
  (cvs) => {
    if (!selectedBaseCvId.value && cvs.length > 0) {
      const def = cvs.find((c) => c.is_default) || cvs[0]
      if (def) selectedBaseCvId.value = def.id
    }
  },
  { immediate: true },
)

function handleRegenerate(): void {
  emit(
    'regenerate',
    selectedModel.value,
    selectedCreativity.value,
    userNotes.value,
    selectedModelId.value || undefined,
    selectedReasoningEffort.value || undefined,
    selectedBaseCvId.value || undefined,
  )
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
      <div v-if="cvStore.baseCvs.length > 0" class="field">
        <label class="field-label" for="regen-base-cv">Base CV</label>
        <select id="regen-base-cv" v-model="selectedBaseCvId" class="field-select" :disabled="disabled">
          <option v-for="cv in cvStore.baseCvs" :key="cv.id" :value="cv.id">
            {{ cv.name }} {{ cv.is_default ? '(Default)' : '' }}
          </option>
        </select>
      </div>

      <ModelSelector
        v-model="selectedModel"
        v-model:model-id="selectedModelId"
        v-model:reasoning-effort="selectedReasoningEffort"
        :claude-api-available="claudeApiAvailable"
        :gemini-available="geminiAvailable"
        :openai-available="openaiAvailable"
        :gemini-web-available="geminiWebAvailable"
        :disabled="disabled"
        :show-model-details="true"
      />
      <CreativitySlider
        v-model="selectedCreativity"
        :disabled="disabled"
      />
      <div class="field">
        <label class="field-label" for="regen-notes">Custom Instructions (optional)</label>
        <textarea
          id="regen-notes"
          v-model="userNotes"
          class="field-textarea field-textarea--small"
          placeholder="e.g. replace GCP with AWS on HiAcuity work experience, emphasize platform engineering..."
          :disabled="disabled"
          rows="3"
        ></textarea>
      </div>
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
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 150ms ease, color 150ms ease;
}
.btn-regenerate-toggle:hover:not(:disabled) {
  border-color: var(--color-text-primary);
  color: var(--color-text-primary);
}
.btn-regenerate-toggle:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.regenerate-options {
  margin-top: 12px;
  padding: 16px;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.btn-regenerate-now {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: var(--color-accent-primary);
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
  transition: background-color 150ms ease, opacity 150ms ease;
}
.btn-regenerate-now:hover:not(:disabled) {
  background: var(--color-accent-primary-hover);
}
.btn-regenerate-now:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.field-select {
  width: 100%;
  height: 40px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  background-color: var(--color-surface-1);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary);
  outline: none;
  box-sizing: border-box;
  transition: border-color 150ms ease;
}

.field-select:focus {
  border-color: var(--color-accent-primary);
}

.field-select:disabled {
  background: var(--color-surface-2);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.field-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  background-color: var(--color-surface-1);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary);
  resize: vertical;
  box-sizing: border-box;
}

.field-textarea:disabled {
  background: var(--color-surface-2);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.field-textarea--small {
  min-height: 72px;
}
</style>
