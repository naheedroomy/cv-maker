<template>
  <div class="signin-container">
    <div class="signin-layout">
      <div class="story-panel">
        <div class="story-top"><span class="story-mark" aria-hidden="true">✳</span><span>CV MAKER / YOUR WORK, BETTER TOLD.</span></div>
        <div class="story-body"><span class="story-index">01 / BEGIN</span><h1>Make your next move <em>count.</em></h1><p>Bring your experience. Bring the job. Leave with a CV you can stand behind.</p></div>
        <div class="story-bottom"><span>THE NEXT CHAPTER STARTS HERE.</span><span aria-hidden="true">↗</span></div>
      </div>
      <div class="signin-card">
        <span class="signin-kicker">WELCOME BACK / 01</span>
        <h2 class="app-title">Your workspace awaits.</h2>
        <p class="app-subtitle">Sign in to create, review and manage your applications.</p>
        <div ref="googleButtonRef" class="google-button-wrapper" aria-label="Google sign-in" :aria-busy="initializing"></div>
        <p v-if="initializing" class="signin-note" role="status">Loading Google Sign-In…</p>
        <div v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</div>
        <button v-if="initializationFailed" type="button" class="signin-retry" @click="initializeGoogleSignIn">Try again</button>
        <p class="signin-note">Your CV stays yours to review and edit.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'

// Declare the Google Identity Services global
declare const google: {
  accounts: {
    id: {
      initialize: (config: {
        client_id: string
        callback: (response: { credential: string }) => void
      }) => void
      renderButton: (
        element: HTMLElement,
        config: { theme: string; size: string; width?: number },
      ) => void
    }
  }
}

const router = useRouter()
const authStore = useAuthStore()
const googleButtonRef = ref<HTMLElement | null>(null)
const errorMessage = ref<string | null>(null)
const initializing = ref(true)
const initializationFailed = ref(false)
let unmounted = false

function loadGoogleScript(): Promise<void> {
  if (typeof google !== 'undefined') return Promise.resolve()
  return new Promise((resolve, reject) => {
    const script = document.querySelector<HTMLScriptElement>('#google-signin-sdk')
      ?? document.createElement('script')
    if (!script.isConnected) {
      script.id = 'google-signin-sdk'
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
    }
    const timeout = setTimeout(() => finish(new Error(
      'Google Sign-In is taking too long to load. Please try again.',
    )), 15000)
    function finish(error?: Error) {
      clearTimeout(timeout)
      script.removeEventListener('load', onLoad)
      script.removeEventListener('error', onError)
      if (error) {
        script.remove()
        reject(error)
      } else resolve()
    }
    function onLoad() {
      if (typeof google === 'undefined') onError()
      else finish()
    }
    function onError() {
      finish(new Error('Google Sign-In could not load. Check your connection and try again.'))
    }
    script.addEventListener('load', onLoad, { once: true })
    script.addEventListener('error', onError, { once: true })
    if (!script.isConnected) document.head.appendChild(script)
  })
}

async function handleCredentialResponse(response: { credential: string }): Promise<void> {
  errorMessage.value = null
  try {
    const res = await fetch('/api/auth', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: response.credential }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(
        (body as { detail?: string }).detail ?? `Sign-in failed: ${res.status}`,
      )
    }
    const data = await res.json() as { jwt: string; user: { id: number; email: string; name: string; picture: string } }
    authStore.login(data.jwt, data.user)
    await router.push('/')
  } catch (err) {
    errorMessage.value = err instanceof Error ? err.message : 'Sign-in failed. Please try again.'
  }
}

async function initializeGoogleSignIn(): Promise<void> {
  initializing.value = true
  initializationFailed.value = false
  errorMessage.value = null
  try {
    // Fetch google_client_id from backend config (pre-auth, use plain fetch)
    const configRes = await fetch('/api/config')
    if (!configRes.ok) {
      throw new Error('Failed to load app configuration. Please try again.')
    }
    const config = await configRes.json() as { google_client_id?: string }
    const clientId = config.google_client_id
    if (!clientId) {
      throw new Error('Google Sign-In is not configured.')
    }

    await loadGoogleScript()
    if (unmounted || !googleButtonRef.value) return

    googleButtonRef.value.replaceChildren()
    google.accounts.id.initialize({
      client_id: clientId,
      callback: handleCredentialResponse,
    })
    google.accounts.id.renderButton(googleButtonRef.value, {
      theme: 'outline',
      size: 'large',
      width: 300,
    })
  } catch (err) {
    if (!unmounted) {
      initializationFailed.value = true
      errorMessage.value = err instanceof Error ? err.message : 'Failed to initialize Google Sign-In.'
    }
  } finally {
    if (!unmounted) initializing.value = false
  }
}

onMounted(initializeGoogleSignIn)
onUnmounted(() => { unmounted = true })
</script>

<style scoped>
.signin-container { display: grid; place-items: center; min-height: 100svh; padding: clamp(18px, 5vw, 70px); background: var(--color-background); }
.signin-layout { width: min(1030px, 100%); min-height: 610px; display: grid; grid-template-columns: 1fr 1fr; background: var(--color-surface-1); border: 1px solid var(--color-border); box-shadow: 0 20px 65px rgba(24,53,53,.08); }
.story-panel { display: flex; flex-direction: column; justify-content: space-between; min-width: 0; padding: clamp(25px, 3.5vw, 46px); background: #1f2937; color: #f9fafb; --color-highlight: #bfdbfe; --color-highlight-text: #1e3a8a; }
.story-top, .story-bottom { display: flex; align-items: center; gap: 15px; font-size: 10px; font-weight: 800; letter-spacing: .1em; }
.story-top .story-mark { display: grid; place-items: center; width: 35px; height: 35px; background: var(--color-highlight); color: var(--color-highlight-text); font-size: 23px; border-radius: 3px; }
.story-body { padding: 60px 0; }
.story-index { font-size: 11px; font-weight: 800; letter-spacing: .14em; color: var(--color-highlight); }
.story-body h1 { max-width: 410px; margin: 18px 0 22px; font-size: clamp(42px, 5vw, 69px); font-weight: 800; line-height: 1.06; letter-spacing: -.06em; }
.story-body h1 em { color: var(--color-highlight); font-style: normal; }
.story-body p { max-width: 340px; font-size: 15px; line-height: 1.6; color: #d1d5db; }
.story-bottom { justify-content: space-between; opacity: .85; }
.story-bottom span:last-child { font-size: 23px; }
.signin-card { align-self: center; min-width: 0; padding: clamp(25px, 4vw, 60px); }
.signin-kicker { color: var(--color-text-secondary); font-size: 10px; font-weight: 800; letter-spacing: .13em; }
.app-title { max-width: 400px; margin: 16px 0 10px; font-size: clamp(29px, 3vw, 42px); font-weight: 800; line-height: 1.13; letter-spacing: -.055em; }
.app-subtitle { max-width: 330px; color: var(--color-text-secondary); font-size: 14px; line-height: 1.6; }
.google-button-wrapper { margin: 31px 0 0; max-width: 100%; }
.error-message { margin-top: 16px; max-width: 320px; color: var(--color-error-text); font-size: 13px; line-height: 1.5; }
.signin-retry { margin-top: 12px; min-height: 44px; padding: 0 16px; border: 1px solid var(--color-border); border-radius: 4px; background: var(--color-surface-2); color: var(--color-text-primary); font-weight: 600; }
.signin-note { margin-top: 26px; padding-top: 18px; border-top: 1px solid var(--color-border); color: var(--color-text-secondary); font-size: 11px; }
@media (max-width: 700px) { .signin-container { padding: 16px; } .signin-layout { grid-template-columns: 1fr; min-height: 0; } .story-panel { min-height: 225px; padding: 22px 25px; } .story-body { padding: 16px 0 8px; } .story-body h1 { margin: 8px 0; font-size: 37px; } .story-body p { margin: 0; font-size: 13px; } .story-bottom { display: none; } .signin-card { padding: 30px 25px 35px; } }
</style>
