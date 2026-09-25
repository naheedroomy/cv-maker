<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiFetch } from '@/utils/apiFetch'

interface Settings {
  claude_cli_model: string
  claude_api_model: string
  claude_reasoning_effort: string
  gemini_model: string
  gemini_reasoning_effort: string
  openai_model: string
  openai_reasoning_effort: string
  openai_base_url: string
  cv_filename: string
  anthropic_api_key: string
  gemini_api_key: string
  openai_api_key: string
  gemini_web_psid: string
  gemini_web_model: string
}

interface ModelOption {
  id: string
  label: string
}

const activeTab = ref<'general' | 'claude-cli' | 'claude-api' | 'gemini' | 'openai' | 'gemini-web'>('general')
const settings = ref<Settings>({
  claude_cli_model: 'haiku',
  claude_api_model: 'claude-haiku-4-5',
  claude_reasoning_effort: 'auto',
  gemini_model: 'gemini-2.5-flash',
  gemini_reasoning_effort: 'auto',
  openai_model: 'gpt-4o-mini',
  openai_reasoning_effort: 'auto',
  openai_base_url: '',
  cv_filename: '',
  anthropic_api_key: '',
  gemini_api_key: '',
  openai_api_key: '',
  gemini_web_psid: '',
  gemini_web_model: 'gemini-3-pro',
})
const saving = ref(false)
const saved = ref(false)
const error = ref<string | null>(null)
const cookieChecking = ref(false)
const cookieStatus = ref<{ ok: boolean; message: string } | null>(null)

const providerModels = ref<Record<string, ModelOption[]>>({
  'claude-cli': [],
  'claude-api': [],
  'gemini': [],
  'openai': [],
  'gemini-web': [],
})
const fetchingModels = ref<Record<string, boolean>>({
  'claude-cli': false,
  'claude-api': false,
  'gemini': false,
  'openai': false,
  'gemini-web': false,
})
const modelFetchErrors = ref<Record<string, string | null>>({
  'claude-cli': null,
  'claude-api': null,
  'gemini': null,
  'openai': null,
  'gemini-web': null,
})

const reasoningOptions = [
  { value: 'auto', label: 'Auto / Default' },
  { value: 'off', label: 'Off' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
]

function ensureCurrentModelInOptions(provider: string) {
  const currentModel =
    provider === 'claude-cli' ? settings.value.claude_cli_model :
    provider === 'claude-api' ? settings.value.claude_api_model :
    provider === 'gemini' ? settings.value.gemini_model :
    provider === 'openai' ? settings.value.openai_model :
    provider === 'gemini-web' ? settings.value.gemini_web_model : ''

  if (currentModel && !providerModels.value[provider]?.some(m => m.id === currentModel)) {
    providerModels.value[provider] = [
      { id: currentModel, label: currentModel },
      ...(providerModels.value[provider] || []),
    ]
  }
}

function getProviderOptions(provider: string): ModelOption[] {
  ensureCurrentModelInOptions(provider)
  return providerModels.value[provider] || []
}

async function fetchModels(provider: 'claude-cli' | 'claude-api' | 'gemini' | 'openai' | 'gemini-web') {
  fetchingModels.value[provider] = true
  modelFetchErrors.value[provider] = null
  try {
    let url = `/api/settings/models?provider=${provider}`
    let apiKey = ''
    if (provider === 'claude-api' && settings.value.anthropic_api_key && !settings.value.anthropic_api_key.startsWith('***')) {
      apiKey = settings.value.anthropic_api_key
    } else if (provider === 'gemini' && settings.value.gemini_api_key && !settings.value.gemini_api_key.startsWith('***')) {
      apiKey = settings.value.gemini_api_key
    } else if (provider === 'openai' && settings.value.openai_api_key && !settings.value.openai_api_key.startsWith('***')) {
      apiKey = settings.value.openai_api_key
    }
    if (apiKey) {
      url += `&api_key=${encodeURIComponent(apiKey)}`
    }
    const res = await apiFetch(url)
    if (!res.ok) {
      throw new Error(`Failed to load models (${res.status})`)
    }
    const data = await res.json()
    if (data.models && Array.isArray(data.models)) {
      providerModels.value[provider] = data.models
      ensureCurrentModelInOptions(provider)
    }
  } catch (err) {
    modelFetchErrors.value[provider] = err instanceof Error ? err.message : 'Failed to fetch models'
  } finally {
    fetchingModels.value[provider] = false
  }
}

async function checkCookie() {
  cookieChecking.value = true
  cookieStatus.value = null
  try {
    const res = await apiFetch('/api/settings/check-gemini-web', { method: 'POST' })
    const data = await res.json()
    if (data.ok) {
      cookieStatus.value = { ok: true, message: `Connected — "${data.response}"` }
    } else {
      cookieStatus.value = { ok: false, message: data.error || 'Cookie invalid or expired' }
    }
  } catch {
    cookieStatus.value = { ok: false, message: 'Request failed — check network' }
  } finally {
    cookieChecking.value = false
  }
}

onMounted(async () => {
  try {
    const res = await apiFetch('/api/settings')
    if (res.ok) {
      settings.value = await res.json()
    }
  } catch {
    error.value = 'Failed to load settings'
  }
  fetchModels('claude-api')
  fetchModels('gemini')
  fetchModels('openai')
  fetchModels('claude-cli')
  fetchModels('gemini-web')
})

async function handleSave() {
  saving.value = true
  saved.value = false
  error.value = null
  try {
    // Build payload: if an API key field still shows a masked value (***xxxx),
    // omit it so the backend doesn't overwrite the stored key with the masked string.
    const payload: Partial<Settings> = { ...settings.value }
    const apiKeyFields = ['anthropic_api_key', 'gemini_api_key', 'openai_api_key', 'gemini_web_psid'] as const
    for (const field of apiKeyFields) {
      if (payload[field]?.startsWith('***')) {
        delete payload[field]
      }
    }
    const res = await apiFetch('/api/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error(`Save failed: ${res.status}`)
    settings.value = await res.json()
    saved.value = true
    setTimeout(() => { saved.value = false }, 2000)

    // Re-fetch models in case API key was updated
    fetchModels('claude-api')
    fetchModels('gemini')
    fetchModels('openai')
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Save failed'
  } finally {
    saving.value = false
  }
}

function selectTab(key: typeof activeTab.value) {
  activeTab.value = key
  if (key !== 'general' && (!providerModels.value[key] || providerModels.value[key].length === 0)) {
    fetchModels(key)
  }
}

const tabs = [
  { key: 'general' as const, label: 'General' },
  { key: 'claude-cli' as const, label: 'Claude CLI' },
  { key: 'claude-api' as const, label: 'Claude API' },
  { key: 'gemini' as const, label: 'Gemini' },
  { key: 'openai' as const, label: 'OpenAI' },
  { key: 'gemini-web' as const, label: 'Gemini Web' },
]
</script>

<template>
  <div class="settings-view">
    <h2 class="settings-title">Provider Settings</h2>
    <p class="settings-subtitle">Configure model names, endpoints, and API keys for each provider.</p>

    <!-- Tabs -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab"
        :class="{ 'tab--active': activeTab === tab.key }"
        @click="selectTab(tab.key)"
      >{{ tab.label }}</button>
    </div>

    <!-- General -->
    <div v-if="activeTab === 'general'" class="tab-content">
      <div class="field">
        <label class="field-label">CV Filename</label>
        <input v-model="settings.cv_filename" class="field-input" placeholder="e.g. Naheed-Roomy-CV" />
        <p class="field-hint">Name for generated PDF and LaTeX files. A short ID is appended automatically (e.g. <code>Naheed-Roomy-CV-3b062.pdf</code>). Leave empty to use the job ID as filename.</p>
      </div>
    </div>

    <!-- Claude CLI -->
    <div v-if="activeTab === 'claude-cli'" class="tab-content">
      <div class="field">
        <label class="field-label">Model</label>
        <select v-model="settings.claude_cli_model" class="field-input field-select">
          <option v-for="m in getProviderOptions('claude-cli')" :key="m.id" :value="m.id">
            {{ m.label }} ({{ m.id }})
          </option>
        </select>
        <p class="field-hint">Passed to <code>claude -p --model &lt;value&gt;</code>.</p>
      </div>
      <div class="field">
        <label class="field-label">Authentication</label>
        <p class="field-hint">Uses your Claude Code CLI subscription. No API key needed.</p>
      </div>
    </div>

    <!-- Claude API -->
    <div v-if="activeTab === 'claude-api'" class="tab-content">
      <div class="field">
        <div class="field-header-row">
          <label class="field-label">Model</label>
          <button
            type="button"
            class="btn-refresh-inline"
            :disabled="fetchingModels['claude-api']"
            @click="fetchModels('claude-api')"
          >
            {{ fetchingModels['claude-api'] ? 'Refreshing...' : '↻ Refresh Models' }}
          </button>
        </div>
        <select v-model="settings.claude_api_model" class="field-input field-select">
          <option v-for="m in getProviderOptions('claude-api')" :key="m.id" :value="m.id">
            {{ m.label }} ({{ m.id }})
          </option>
        </select>
        <p v-if="modelFetchErrors['claude-api']" class="field-error-hint">
          {{ modelFetchErrors['claude-api'] }}
        </p>
        <p class="field-hint">Models discovered from Anthropic API. Click Refresh to reload with your API key.</p>
      </div>
      <div class="field">
        <label class="field-label">Reasoning / Thinking Effort</label>
        <select v-model="settings.claude_reasoning_effort" class="field-input field-select">
          <option v-for="opt in reasoningOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <p class="field-hint">Controls extended or adaptive thinking for Claude 3.7+ and Claude 5 models.</p>
      </div>
      <div class="field">
        <label class="field-label">API Key</label>
        <input v-model="settings.anthropic_api_key" type="password" class="field-input" placeholder="sk-ant-..." />
        <p class="field-hint">Anthropic API key. Overrides <code>.env</code> value if set. Masked after save.</p>
      </div>
    </div>

    <!-- Gemini -->
    <div v-if="activeTab === 'gemini'" class="tab-content">
      <div class="field">
        <div class="field-header-row">
          <label class="field-label">Model</label>
          <button
            type="button"
            class="btn-refresh-inline"
            :disabled="fetchingModels['gemini']"
            @click="fetchModels('gemini')"
          >
            {{ fetchingModels['gemini'] ? 'Refreshing...' : '↻ Refresh Models' }}
          </button>
        </div>
        <select v-model="settings.gemini_model" class="field-input field-select">
          <option v-for="m in getProviderOptions('gemini')" :key="m.id" :value="m.id">
            {{ m.label }} ({{ m.id }})
          </option>
        </select>
        <p v-if="modelFetchErrors['gemini']" class="field-error-hint">
          {{ modelFetchErrors['gemini'] }}
        </p>
        <p class="field-hint">Models discovered from Google AI Studio. Click Refresh to reload with your API key.</p>
      </div>
      <div class="field">
        <label class="field-label">Reasoning / Thinking Effort</label>
        <select v-model="settings.gemini_reasoning_effort" class="field-input field-select">
          <option v-for="opt in reasoningOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <p class="field-hint">Controls thinking level (Low, Medium, High) or disables thinking for Gemini 2.5+ models.</p>
      </div>
      <div class="field">
        <label class="field-label">API Key</label>
        <input v-model="settings.gemini_api_key" type="password" class="field-input" placeholder="AIza..." />
        <p class="field-hint">Google AI API key. Overrides <code>.env</code> value if set. Masked after save.</p>
      </div>
    </div>

    <!-- OpenAI -->
    <div v-if="activeTab === 'openai'" class="tab-content">
      <div class="field">
        <div class="field-header-row">
          <label class="field-label">Model</label>
          <button
            type="button"
            class="btn-refresh-inline"
            :disabled="fetchingModels['openai']"
            @click="fetchModels('openai')"
          >
            {{ fetchingModels['openai'] ? 'Refreshing...' : '↻ Refresh Models' }}
          </button>
        </div>
        <select v-model="settings.openai_model" class="field-input field-select">
          <option v-for="m in getProviderOptions('openai')" :key="m.id" :value="m.id">
            {{ m.label }} ({{ m.id }})
          </option>
        </select>
        <p v-if="modelFetchErrors['openai']" class="field-error-hint">
          {{ modelFetchErrors['openai'] }}
        </p>
        <p class="field-hint">Models discovered from OpenAI. Click Refresh to reload with your API key.</p>
      </div>
      <div class="field">
        <label class="field-label">Reasoning / Thinking Effort</label>
        <select v-model="settings.openai_reasoning_effort" class="field-input field-select">
          <option v-for="opt in reasoningOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <p class="field-hint">Reasoning effort for reasoning models (o1, o3, o4, gpt-5+). Automatically omitted for standard models.</p>
      </div>
      <div class="field">
        <label class="field-label">Base URL</label>
        <input v-model="settings.openai_base_url" class="field-input" placeholder="https://api.openai.com/v1 (default)" />
        <p class="field-hint">Override for OpenAI-compatible APIs (Groq, Together AI, Ollama, etc.). Leave empty for default OpenAI.</p>
      </div>
      <div class="field">
        <label class="field-label">API Key</label>
        <input v-model="settings.openai_api_key" type="password" class="field-input" placeholder="sk-..." />
        <p class="field-hint">OpenAI API key. Overrides <code>.env</code> value if set. Masked after save.</p>
      </div>
    </div>

    <!-- Gemini Web -->
    <div v-if="activeTab === 'gemini-web'" class="tab-content">
      <div class="field">
        <label class="field-label">Browser Cookie (__Secure-1PSID)</label>
        <textarea
          v-model="settings.gemini_web_psid"
          class="field-input field-textarea"
          rows="3"
          placeholder="Paste your __Secure-1PSID cookie value here"
        ></textarea>
        <p class="field-hint">
          To get this cookie: open <code>gemini.google.com</code> in your browser while signed in,
          press F12, go to the Network tab, click any request, find the <code>Cookie</code> header,
          and copy the value after <code>__Secure-1PSID=</code> (ends at the next semicolon).
          This is a long string (~200+ characters). Masked after save.
        </p>
      </div>
      <div class="field">
        <label class="field-label">Model</label>
        <select v-model="settings.gemini_web_model" class="field-input field-select">
          <option v-for="m in getProviderOptions('gemini-web')" :key="m.id" :value="m.id">
            {{ m.label }} ({{ m.id }})
          </option>
        </select>
        <p class="field-hint">Gemini web model name.</p>
      </div>
      <div class="field">
        <label class="field-label">Check Cookie</label>
        <div class="cookie-check-row">
          <button
            class="btn-check"
            :disabled="cookieChecking || !settings.gemini_web_psid"
            @click="checkCookie"
          >
            {{ cookieChecking ? 'Checking...' : 'Test Connection' }}
          </button>
          <span v-if="cookieStatus" :class="cookieStatus.ok ? 'check-ok' : 'check-fail'">
            {{ cookieStatus.message }}
          </span>
        </div>
        <p class="field-hint">
          Sends a quick test request to verify your cookie is still valid.
          Save your cookie first before testing.
        </p>
      </div>
      <div class="field">
        <label class="field-label">About</label>
        <p class="field-hint">
          Gemini Web uses your browser session cookie to access the Gemini web app directly.
          No API key needed — uses your existing Gemini subscription.
          The cookie may expire if you sign out of Google or after several weeks.
          Less reliable than the official Gemini API but free with your subscription.
        </p>
      </div>
    </div>

    <!-- Save -->
    <div class="save-row">
      <button class="btn-save" :disabled="saving" @click="handleSave">
        {{ saving ? 'Saving...' : 'Save Settings' }}
      </button>
      <span v-if="saved" class="save-success">Saved</span>
      <span v-if="error" class="save-error">{{ error }}</span>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 600px;
  margin: 0 auto;
  padding: 24px;
}

.settings-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.settings-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
}

.tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: var(--color-surface-2);
  border-radius: 8px;
  margin-bottom: 24px;
}

.tab {
  flex: 1;
  height: 36px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 150ms ease, color 150ms ease;
}

.tab:hover:not(.tab--active) {
  background: var(--color-surface-3);
}

.tab--active {
  background: var(--color-surface-1);
  color: var(--color-text-primary);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.field-input {
  height: 40px;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--color-text-primary);
  background-color: var(--color-surface-1);
  transition: border-color 150ms ease;
}

.field-textarea {
  height: auto;
  min-height: 72px;
  padding: 8px 12px;
  resize: vertical;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.field-input:focus {
  outline: none;
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15); /* Assuming --color-accent-primary is #3B82F6 */
}

.field-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.field-hint code {
  background: var(--color-surface-2);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}

.save-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 28px;
}

.btn-save {
  height: 40px;
  padding: 0 24px;
  border-radius: 6px;
  background: var(--color-accent-primary);
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 150ms ease, opacity 150ms ease;
}

.btn-save:hover:not(:disabled) {
  background: var(--color-accent-primary-hover);
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.save-success {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-success);
}

.save-error {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-error);
}

.cookie-check-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-check {
  height: 36px;
  padding: 0 16px;
  border-radius: 6px;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.btn-check:hover:not(:disabled) {
  background: var(--color-surface-3);
}

.btn-check:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.check-ok {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-success);
}

.check-fail {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-error);
}

.field-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-refresh-inline {
  background: none;
  border: none;
  color: var(--color-accent-primary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background-color 150ms ease, opacity 150ms ease;
}

.btn-refresh-inline:hover:not(:disabled) {
  background: var(--color-surface-2);
}

.btn-refresh-inline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-select {
  cursor: pointer;
  font-family: inherit;
}

.field-error-hint {
  font-size: 12px;
  color: var(--color-error);
  margin-top: 2px;
}
</style>
