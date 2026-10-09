<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import '@/assets/selector.css'
import { apiFetch } from '@/utils/apiFetch'

interface ModelOption {
  id: string
  label: string
}

const props = withDefaults(
  defineProps<{
    modelValue: string
    claudeApiAvailable: boolean
    geminiAvailable: boolean
    openaiAvailable: boolean
    geminiWebAvailable: boolean
    disabled: boolean
    modelId?: string
    reasoningEffort?: string
    showModelDetails?: boolean
  }>(),
  {
    modelId: '',
    reasoningEffort: 'auto',
    showModelDetails: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'update:modelId', value: string): void
  (e: 'update:reasoningEffort', value: string): void
}>()

const options = [
  { value: 'claude-api', label: 'Claude API', hint: 'Requires Anthropic API key (set in Settings)' },
  { value: 'gemini-flash', label: 'Gemini', hint: 'Requires Gemini API key (set in Settings)' },
  { value: 'openai', label: 'OpenAI', hint: 'Requires OpenAI API key (set in Settings)' },
  { value: 'gemini-web', label: 'Gemini Web', hint: 'Requires Gemini web cookie (set in Settings)' },
] as const

const defaultSettings = ref<Record<string, string>>({})
const modelsCache = ref<Record<string, ModelOption[]>>({})
const fetchingModels = ref(false)

function isProviderAvailable(val: string): boolean {
  if (val === 'claude-api') return props.claudeApiAvailable
  if (val === 'gemini-flash') return props.geminiAvailable
  if (val === 'openai') return props.openaiAvailable
  if (val === 'gemini-web') return props.geminiWebAvailable
  return false
}

function supportsReasoning(provider: string): boolean {
  return ['gemini-flash', 'claude-api', 'openai'].includes(provider)
}

function select(model: string): void {
  if (props.disabled) return
  if (isDisabledOption(model)) return
  emit('update:modelValue', model)
  if (props.showModelDetails) {
    syncDefaultsForProvider(model)
  }
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
  if (props.modelValue === 'gemini-web' && !props.geminiWebAvailable) {
    return 'Set your Gemini web cookie (__Secure-1PSID) in Settings.'
  }
  const opt = options.find(o => o.value === props.modelValue)
  return opt ? opt.hint : ''
}

function isDisabledOption(value: string): boolean {
  if (value === 'claude-api' && !props.claudeApiAvailable) return true
  if (value === 'gemini-flash' && !props.geminiAvailable) return true
  if (value === 'openai' && !props.openaiAvailable) return true
  if (value === 'gemini-web' && !props.geminiWebAvailable) return true
  return false
}

function syncDefaultsForProvider(provider: string) {
  const defModel = defaultSettings.value[`${provider}_model`] || ''
  const defReasoning = defaultSettings.value[`${provider}_reasoning`] || 'auto'
  emit('update:modelId', defModel)
  emit('update:reasoningEffort', defReasoning)
}

async function loadModels(forceRefresh = false) {
  const provider = props.modelValue
  if (!forceRefresh && modelsCache.value[provider] && modelsCache.value[provider].length > 0) {
    return
  }
  fetchingModels.value = true
  try {
    const provParam = provider === 'gemini-flash' ? 'gemini' : provider
    const res = await apiFetch(`/api/settings/models?provider=${provParam}`)
    if (res.ok) {
      const data = await res.json()
      if (data.models && Array.isArray(data.models)) {
        modelsCache.value[provider] = data.models
      }
    }
  } catch {
    // Keep cached or fallback
  } finally {
    fetchingModels.value = false
  }
}

onMounted(async () => {
  if (props.showModelDetails) {
    try {
      const res = await apiFetch('/api/settings')
      if (res.ok) {
        const data = await res.json()
        defaultSettings.value = {
          'gemini-flash_model': data.gemini_model,
          'gemini-flash_reasoning': data.gemini_reasoning_effort,
          'claude-api_model': data.claude_api_model,
          'claude-api_reasoning': data.claude_reasoning_effort,
          'openai_model': data.openai_model,
          'openai_reasoning': data.openai_reasoning_effort,
          'gemini-web_model': data.gemini_web_model,
        }
        if (!props.modelId) {
          syncDefaultsForProvider(props.modelValue)
        }
      }
    } catch {
      // Fallback
    }
    loadModels()
  }
})

watch(() => props.modelValue, (newVal) => {
  if (props.showModelDetails) {
    syncDefaultsForProvider(newVal)
    loadModels()
  }
})

const modelList = computed<ModelOption[]>(() => {
  const provider = props.modelValue
  const cached = modelsCache.value[provider] || []
  const current = props.modelId || defaultSettings.value[`${provider}_model`] || ''
  if (current && !cached.some(m => m.id === current)) {
    return [{ id: current, label: current }, ...cached]
  }
  return cached
})
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

    <!-- Detailed overrides for selected provider -->
    <div
      v-if="showModelDetails && isProviderAvailable(modelValue)"
      class="model-details-grid"
      :class="{ 'model-details-grid--single': !supportsReasoning(modelValue) }"
    >
      <div class="detail-field">
        <div class="detail-label-row">
          <label class="detail-label">Model variant</label>
          <button
            type="button"
            class="detail-refresh-btn"
            :disabled="disabled || fetchingModels"
            title="Refresh models for this provider"
            @click="loadModels(true)"
          >
            {{ fetchingModels ? '...' : '↻ Refresh' }}
          </button>
        </div>
        <select
          :value="modelId || defaultSettings[`${modelValue}_model`]"
          class="detail-select"
          :title="modelId || defaultSettings[`${modelValue}_model`]"
          :disabled="disabled || fetchingModels"
          @change="emit('update:modelId', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="m in modelList" :key="m.id" :value="m.id">
            {{ m.label }} ({{ m.id }})
          </option>
        </select>
      </div>

      <div v-if="supportsReasoning(modelValue)" class="detail-field">
        <label class="detail-label">Reasoning effort</label>
        <select
          :value="reasoningEffort || defaultSettings[`${modelValue}_reasoning`] || 'auto'"
          class="detail-select"
          :disabled="disabled"
          @change="emit('update:reasoningEffort', ($event.target as HTMLSelectElement).value)"
        >
          <option value="auto">Auto / Default</option>
          <option value="off">Off (Fastest)</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High (Deep reasoning)</option>
        </select>
      </div>
    </div>
  </div>
</template>

<style scoped>
.model-selector {
  margin-bottom: 16px;
}

.model-details-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  margin-top: 10px;
  padding: 12px;
  background: var(--color-surface-2);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.model-details-grid--single {
  grid-template-columns: minmax(0, 1fr);
}

@media (max-width: 540px) {
  .model-details-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.detail-field {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.detail-refresh-btn {
  background: none;
  border: none;
  color: var(--color-accent-primary);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  padding: 1px 4px;
  border-radius: 3px;
  transition: opacity 150ms ease;
}

.detail-refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.detail-select {
  display: block;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  text-overflow: ellipsis;
  height: 36px;
  padding: 0 8px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 13px;
  color: var(--color-text-primary);
  background-color: var(--color-surface-1);
  cursor: pointer;
  outline: none;
}

.detail-select:focus {
  border-color: var(--color-accent-primary);
}
</style>
