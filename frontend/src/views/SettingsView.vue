<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiFetch } from '@/utils/apiFetch'

interface Settings {
  claude_cli_model: string
  claude_api_model: string
  gemini_model: string
  openai_model: string
  openai_base_url: string
  cv_filename: string
  anthropic_api_key: string
  gemini_api_key: string
  openai_api_key: string
  gemini_web_psid: string
  gemini_web_model: string
}

const activeTab = ref<'general' | 'claude-cli' | 'claude-api' | 'gemini' | 'openai' | 'gemini-web'>('general')
const settings = ref<Settings>({
  claude_cli_model: 'haiku',
  claude_api_model: 'claude-haiku-4-5',
  gemini_model: 'gemini-2.5-flash',
  openai_model: 'gpt-4o-mini',
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

onMounted(async () => {
  try {
    const res = await apiFetch('/api/settings')
    if (res.ok) {
      settings.value = await res.json()
    }
  } catch {
    error.value = 'Failed to load settings'
  }
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
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Save failed'
  } finally {
    saving.value = false
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
        @click="activeTab = tab.key"
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
        <input v-model="settings.claude_cli_model" class="field-input" placeholder="haiku" />
        <p class="field-hint">Passed to <code>claude -p --model &lt;value&gt;</code>. Examples: haiku, sonnet, opus</p>
      </div>
      <div class="field">
        <label class="field-label">Authentication</label>
        <p class="field-hint">Uses your Claude Code CLI subscription. No API key needed.</p>
      </div>
    </div>

    <!-- Claude API -->
    <div v-if="activeTab === 'claude-api'" class="tab-content">
      <div class="field">
        <label class="field-label">Model</label>
        <input v-model="settings.claude_api_model" class="field-input" placeholder="claude-haiku-4-5" />
        <p class="field-hint">Anthropic model ID. Examples: claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-6</p>
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
        <label class="field-label">Model</label>
        <input v-model="settings.gemini_model" class="field-input" placeholder="gemini-2.5-flash" />
        <p class="field-hint">Google model ID. Examples: gemini-2.5-flash, gemini-2.5-pro, gemini-2.0-flash</p>
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
        <label class="field-label">Model</label>
        <input v-model="settings.openai_model" class="field-input" placeholder="gpt-4o-mini" />
        <p class="field-hint">OpenAI model ID. Examples: gpt-4o-mini, gpt-4o, gpt-4.1-mini</p>
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
        <input v-model="settings.gemini_web_model" class="field-input" placeholder="gemini-3-pro" />
        <p class="field-hint">Gemini web model name. Examples: gemini-3-pro, gemini-3-flash</p>
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
  color: #111827;
  margin-bottom: 4px;
}

.settings-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 24px;
}

.tabs {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 8px;
  margin-bottom: 24px;
}

.tab {
  flex: 1;
  height: 36px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 150ms ease, color 150ms ease;
}

.tab:hover:not(.tab--active) {
  background: #e5e7eb;
}

.tab--active {
  background: #ffffff;
  color: #111827;
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
  color: #111827;
}

.field-input {
  height: 40px;
  padding: 0 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: #111827;
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
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.field-hint {
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}

.field-hint code {
  background: #f3f4f6;
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
  background: #2563eb;
  border: none;
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 150ms ease;
}

.btn-save:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-save:disabled {
  background: #93c5fd;
  cursor: not-allowed;
}

.save-success {
  font-size: 13px;
  font-weight: 600;
  color: #16a34a;
}

.save-error {
  font-size: 13px;
  font-weight: 600;
  color: #dc2626;
}
</style>
