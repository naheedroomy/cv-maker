import { useAuthStore } from '@/stores/authStore'

/**
 * Fetch wrapper that auto-adds Authorization: Bearer header.
 * On 401 response, clears JWT and redirects to /signin.
 * Drop-in replacement for native fetch() for all /api/* calls.
 */
export async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const authStore = useAuthStore()

  const headers = new Headers(init?.headers)
  if (authStore.jwt) {
    headers.set('Authorization', `Bearer ${authStore.jwt}`)
  }
  if (!headers.has('Content-Type') && init?.body && typeof init.body === 'string') {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(input, { ...init, headers })

  if (res.status === 401) {
    authStore.logout()
    // Use window.location for hard redirect to ensure full state reset
    window.location.href = '/signin'
  }

  return res
}
