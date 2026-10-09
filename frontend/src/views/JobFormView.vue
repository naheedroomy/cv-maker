<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useJobStore } from '@/stores/jobStore'
import { useCvStore } from '@/stores/cvStore'
import ErrorBanner from '@/components/ErrorBanner.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import ModelSelector from '@/components/ModelSelector.vue'
import CreativitySlider from '@/components/CreativitySlider.vue'
import { apiFetch } from '@/utils/apiFetch'

const router = useRouter()
const store = useJobStore()
const cvStore = useCvStore()
const companyName = ref('')
const jobLink = ref('')
const jobText = ref('')
const userNotes = ref('')
const selectedBaseCvId = ref('')
const submitting = ref(false)
const errorMessage = ref<string | null>(null)
const selectedModel = ref('gemini-flash')
const selectedModelId = ref('')
const selectedReasoningEffort = ref('auto')
const selectedCreativity = ref(2)
const claudeApiAvailable = ref(false)
const geminiAvailable = ref(false)
const openaiAvailable = ref(false)
const geminiWebAvailable = ref(false)
const configLoaded = ref(false)
const configError = ref(false)
const hasProvider = computed(() => claudeApiAvailable.value || geminiAvailable.value || openaiAvailable.value || geminiWebAvailable.value)
const canSubmit = computed(() => companyName.value.trim() !== '' && jobText.value.trim() !== '' && !submitting.value && hasProvider.value)

watch(() => cvStore.baseCvs, (cvs) => {
  if (cvs.length > 0 && (!selectedBaseCvId.value || !cvs.some((c) => c.id === selectedBaseCvId.value))) {
    const def = cvs.find((c) => c.is_default) || cvs[0]
    if (def) selectedBaseCvId.value = def.id
  }
}, { immediate: true })

onMounted(async () => {
  cvStore.fetchBaseCvs()
  try {
    const res = await apiFetch('/api/config')
    if (!res.ok) throw new Error('Configuration unavailable')
    const data = await res.json()
    claudeApiAvailable.value = data.claude_api_available === true
    geminiAvailable.value = data.gemini_available === true
    openaiAvailable.value = data.openai_available === true
    geminiWebAvailable.value = data.gemini_web_available === true
    if (!geminiAvailable.value && selectedModel.value === 'gemini-flash') {
      if (claudeApiAvailable.value) selectedModel.value = 'claude-api'
      else if (openaiAvailable.value) selectedModel.value = 'openai'
      else if (geminiWebAvailable.value) selectedModel.value = 'gemini-web'
    }
  } catch { configError.value = true }
  finally { configLoaded.value = true }
})

async function handleSubmit(): Promise<void> {
  if (!canSubmit.value) return
  submitting.value = true
  errorMessage.value = null
  try {
    const id = await store.submitJob({
      company_name: companyName.value.trim(), job_link: jobLink.value.trim(),
      job_text: jobText.value.trim(), model: selectedModel.value,
      model_id: selectedModelId.value || undefined,
      reasoning_effort: selectedReasoningEffort.value || undefined,
      creativity_level: selectedCreativity.value,
      user_notes: userNotes.value.trim(), base_cv_id: selectedBaseCvId.value || undefined,
    })
    await router.push('/jobs/' + id)
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'An unexpected error occurred.'
  } finally { submitting.value = false }
}
function handleRetry(): void { errorMessage.value = null }
</script>

<template>
  <div class="job-form-view">
    <header class="page-heading">
      <h1 class="page-title">Create a CV</h1>
    </header>

    <ErrorBanner v-if="errorMessage" :message="errorMessage" @retry="handleRetry" />

    <form class="job-form" @submit.prevent="handleSubmit" novalidate>
      <section class="author-panel" aria-labelledby="brief-heading">
        <div class="panel-topline"><span>01 — THE BRIEF</span><span class="panel-topline-end">SOURCE / JOB LISTING</span></div>
        <div class="author-content">
          <div class="section-heading">
            <div><h2 id="brief-heading">Tell us about the role.</h2><p>Start with the listing you’re applying to.</p></div>
            <span class="section-mark" aria-hidden="true">↘</span>
          </div>
          <div class="field-row">
            <div class="field">
              <label for="company-name" class="field-label">Company name <span class="required-star" aria-hidden="true">*</span></label>
              <input id="company-name" v-model="companyName" type="text" class="field-input" placeholder="e.g. Acme Corp" aria-required="true" autocomplete="organization" :disabled="submitting" />
            </div>
            <div class="field">
              <label for="job-link" class="field-label">Job link <span class="optional">OPTIONAL</span></label>
              <input id="job-link" v-model="jobLink" type="url" class="field-input" placeholder="https://…" :disabled="submitting" />
            </div>
          </div>
          <div class="field field--description">
            <div class="field-line"><label for="job-text" class="field-label">Job description <span class="required-star" aria-hidden="true">*</span></label><span class="field-counter">{{ jobText.length ? `${jobText.length.toLocaleString()} characters` : 'PASTE OR TYPE' }}</span></div>
            <textarea id="job-text" v-model="jobText" class="field-textarea" placeholder="Paste the full job listing here — the responsibilities, requirements and everything in between." aria-required="true" :disabled="submitting"></textarea>
            <p class="field-footnote">Your listing is used to tailor this application. You can revisit it in the result.</p>
          </div>
          <div class="field field--notes">
            <label for="user-notes" class="field-label">Anything to keep in mind? <span class="optional">OPTIONAL</span></label>
            <textarea id="user-notes" v-model="userNotes" class="field-textarea field-textarea--small" placeholder="E.g. emphasize platform work or keep this under two pages." :disabled="submitting"></textarea>
          </div>
        </div>
        <div class="panel-bottomline"><span>YOUR SOURCE MATERIAL</span><span>↗ CV MAKER</span></div>
      </section>

      <aside class="options-panel" aria-labelledby="setup-heading">
        <div class="panel-topline"><span>02 — THE SETUP</span><span>↗</span></div>
        <div class="options-content">
          <h2 id="setup-heading">Ready when you are.</h2>
          <p class="options-intro">Choose your source CV and how to tailor it. Then create your draft.</p>
          <button type="submit" class="submit-btn" :disabled="!canSubmit" :aria-describedby="!hasProvider && configLoaded ? 'provider-notice' : undefined">
            <LoadingSpinner v-if="submitting" class="btn-spinner" />
            <span>{{ submitting ? 'Starting your draft…' : 'Generate my CV' }}</span><span v-if="!submitting" aria-hidden="true">↗</span>
          </button>
          <p v-if="configLoaded && !hasProvider" id="provider-notice" class="provider-notice" role="status">
            {{ configError ? 'Could not check your provider settings.' : 'Connect an AI provider to generate a CV.' }}
            <RouterLink to="/settings">Open settings →</RouterLink>
          </p>
          <p v-else class="submit-help">You can inspect and edit your draft before downloading.</p>
          <div class="setup-divider"><span>SOURCE &amp; PREFERENCES</span><span>↓</span></div>
          <div v-if="cvStore.baseCvs.length" class="field">
            <label for="base-cv-select" class="field-label">Base CV</label>
            <select id="base-cv-select" v-model="selectedBaseCvId" class="field-select" :disabled="submitting">
              <option v-for="cv in cvStore.baseCvs" :key="cv.id" :value="cv.id">{{ cv.name }} {{ cv.is_default ? '(Default)' : '' }}</option>
            </select>
          </div>
          <div v-else class="base-cv-note"><p>No base CV found.</p><RouterLink to="/base-cv">Add or edit your CV →</RouterLink></div>
          <ModelSelector v-model="selectedModel" v-model:model-id="selectedModelId" v-model:reasoning-effort="selectedReasoningEffort" :claude-api-available="claudeApiAvailable" :gemini-available="geminiAvailable" :openai-available="openaiAvailable" :gemini-web-available="geminiWebAvailable" :disabled="submitting" :show-model-details="true" />
          <CreativitySlider v-model="selectedCreativity" :disabled="submitting" />
        </div>
        <div class="options-footer">GOOD WORK STARTS WITH A GOOD BRIEF. <span aria-hidden="true">✳</span></div>
      </aside>
    </form>
    <p class="below-note"><span aria-hidden="true">✳</span> Your experience stays yours. Every draft is yours to inspect, revise and download.</p>
  </div>
</template>

<style scoped>
.job-form-view { width: 100%; }
.page-heading { margin: 0 0 20px; }
.page-title { color: var(--color-text-primary); font-size: 26px; font-weight: 800; line-height: 1.2; letter-spacing: -.03em; }
.job-form { display: grid; grid-template-columns: minmax(0, 1.62fr) minmax(290px, 1fr); gap: 17px; align-items: start; }
.author-panel, .options-panel { background: var(--color-surface-1); border: 1px solid var(--color-border); border-radius: 5px; box-shadow: 0 10px 32px rgba(24,53,53,.04); min-width: 0; overflow: hidden; }
.panel-topline, .panel-bottomline { display: flex; justify-content: space-between; align-items: center; padding: 15px 25px; font-size: 10px; font-weight: 800; letter-spacing: .09em; color: var(--color-text-secondary); }
.panel-topline { border-bottom: 1px solid var(--color-border); }
.panel-bottomline { border-top: 1px solid var(--color-border); background: var(--color-surface-2); font-size: 9px; }
.author-content { padding: 28px 30px 30px; }
.section-heading { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 28px; }
.section-heading h2, .options-content h2 { font-size: clamp(20px, 2vw, 27px); line-height: 1.2; font-weight: 800; letter-spacing: -.045em; }
.section-heading p, .options-intro { margin-top: 7px; color: var(--color-text-secondary); font-size: 13px; line-height: 1.5; }
.section-mark { color: var(--color-text-tertiary); font-size: 24px; line-height: 1; }
.field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.field { margin-bottom: 21px; min-width: 0; }
.field-label { display: block; font-size: 12px; font-weight: 800; margin-bottom: 8px; color: var(--color-text-primary); }
.optional, .field-counter { color: var(--color-text-tertiary); font-size: 9px; font-weight: 800; letter-spacing: .08em; }
.optional { margin-left: 3px; }
.required-star { color: var(--color-error); }
.field-line { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.field-input, .field-select, .field-textarea { display: block; width: 100%; padding: 12px 14px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface-1); color: var(--color-text-primary); font-size: 13px; outline: none; }
.field-input, .field-select { min-height: 44px; }
.field-input::placeholder, .field-textarea::placeholder { color: var(--color-text-tertiary); opacity: .86; }
.field-input:focus, .field-select:focus, .field-textarea:focus { border-color: var(--color-accent-primary); box-shadow: 0 0 0 2px var(--color-accent-secondary); }
.field-input:disabled, .field-select:disabled, .field-textarea:disabled { background: var(--color-surface-2); cursor: not-allowed; }
.field-textarea { min-height: 225px; resize: vertical; line-height: 1.6; }
.field-textarea--small { min-height: 78px; }
.field-footnote { margin-top: 8px; color: var(--color-text-tertiary); font-size: 11px; line-height: 1.5; }
.field--notes { margin-bottom: 0; }
.options-panel { position: sticky; top: 24px; }
.options-content { padding: 28px 25px 8px; }
.options-intro { max-width: 290px; }
.submit-btn { width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 13px 16px; margin-top: 22px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-accent-primary); color: var(--color-text-inverted); text-align: left; font-size: 14px; font-weight: 800; min-height: 48px; transition: background .15s ease, transform .15s ease; }
.submit-btn:not(:disabled):hover { background: var(--color-accent-primary-hover); transform: translateY(-2px); }
.submit-btn:disabled { background: var(--color-surface-3); color: var(--color-text-secondary); opacity: 1; }
.submit-help, .provider-notice { min-height: 35px; margin: 10px 0 0; font-size: 11px; line-height: 1.5; color: var(--color-text-secondary); }
.provider-notice { color: var(--color-error-text); }
.provider-notice a { display: inline-block; font-weight: 800; }
.setup-divider { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--color-border); padding: 18px 0 20px; font-size: 10px; font-weight: 800; letter-spacing: .08em; color: var(--color-text-tertiary); }
.setup-divider span:last-child { font-size: 17px; font-weight: 400; }
.base-cv-note { margin-bottom: 20px; font-size: 12px; color: var(--color-text-secondary); }
.base-cv-note a { display: inline-block; margin-top: 5px; font-weight: 700; }
.options-footer { border-top: 1px solid var(--color-border); padding: 16px 25px; display: flex; align-items: center; justify-content: space-between; gap: 10px; font-size: 9px; font-weight: 800; letter-spacing: .06em; color: var(--color-text-tertiary); }
.options-footer span { color: var(--color-text-primary); font-size: 16px; }
.below-note { margin-top: 20px; color: var(--color-text-secondary); font-size: 12px; line-height: 1.5; }
.below-note span { color: var(--color-text-primary); margin-right: 6px; }
@media (max-width: 1200px) { .job-form { grid-template-columns: minmax(0, 1.3fr) minmax(265px, 1fr); } .field-row { grid-template-columns: 1fr; gap: 0; } }
@media (max-width: 1040px) { .job-form { grid-template-columns: 1fr; } .options-panel { position: static; } .field-row { grid-template-columns: 1fr 1fr; gap: 14px; } }
@media (max-width: 600px) { .page-heading { margin-bottom: 18px; } .page-title { font-size: 24px; } .author-content, .options-content { padding: 23px 20px 12px; } .field-row { grid-template-columns: 1fr; gap: 0; } .panel-topline, .panel-bottomline { padding-inline: 20px; } .panel-topline-end { display: none; } .section-heading { margin-bottom: 22px; } .field-textarea { min-height: 210px; } }
</style>
