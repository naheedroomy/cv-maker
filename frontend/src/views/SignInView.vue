<template>
  <div class="signin-container">
    <div class="signin-card">
      <h1 class="app-title">CV Maker</h1>
      <p class="app-subtitle">Sign in to get started</p>

      <div ref="googleButtonRef" class="google-button-wrapper"></div>

      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

onMounted(async () => {
  try {
    // Fetch google_client_id from backend config (pre-auth, use plain fetch)
    const configRes = await fetch('/api/config')
    if (!configRes.ok) {
      errorMessage.value = 'Failed to load app configuration.'
      return
    }
    const config = await configRes.json() as { google_client_id?: string }
    const clientId = config.google_client_id
    if (!clientId) {
      errorMessage.value = 'Google Sign-In is not configured.'
      return
    }

    if (!googleButtonRef.value) return

    google.accounts.id.initialize({
      client_id: clientId,
      callback: handleCredentialResponse,
    })
    google.accounts.id.renderButton(googleButtonRef.value, {
      theme: 'outline',
      size: 'large',
      width: 300,
    })
  } catch {
    errorMessage.value = 'Failed to initialize Google Sign-In.'
  }
})
</script>

<style scoped>
.signin-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: var(--color-background);
}

.signin-card {
  background: var(--color-surface-1);
  border-radius: 12px;
  padding: 48px;
  box-shadow: 0 4px 24px var(--color-shadow, rgba(0, 0, 0, 0.08));
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  min-width: 360px;
}

.app-title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  color: var(--color-text-primary);
}

.app-subtitle {
  margin: 0;
  font-size: 1rem;
  color: var(--color-text-secondary);
}

.google-button-wrapper {
  margin-top: 8px;
}

.error-message {
  color: var(--color-error);
  font-size: 0.875rem;
  text-align: center;
  max-width: 300px;
}
</style>
