import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export interface AuthUser {
  id: number
  email: string
  name: string
  picture: string
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const part = token.split('.')[1]
    if (!part) return null
    // Handle URL-safe base64 (PyJWT uses - and _ instead of + and /)
    const base64 = part.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64)) as Record<string, unknown>
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const jwt = ref<string | null>(null)
  const user = ref<AuthUser | null>(null)
  const isAuthenticated = computed(() => !!jwt.value)

  // On store creation, restore from localStorage — but validate JWT expiry
  const savedJwt = localStorage.getItem('jwt')
  if (savedJwt) {
    const payload = decodeJwtPayload(savedJwt)
    const exp = payload?.exp as number | undefined
    if (payload && exp && exp * 1000 > Date.now()) {
      jwt.value = savedJwt
      try {
        const savedUser = localStorage.getItem('auth_user')
        if (savedUser) user.value = JSON.parse(savedUser) as AuthUser
      } catch { /* ignore corrupt user data */ }
    } else {
      localStorage.removeItem('jwt')
      localStorage.removeItem('auth_user')
    }
  }

  function login(token: string, userData: AuthUser): void {
    jwt.value = token
    user.value = userData
    localStorage.setItem('jwt', token)
    localStorage.setItem('auth_user', JSON.stringify(userData))
  }

  function logout(): void {
    jwt.value = null
    user.value = null
    localStorage.removeItem('jwt')
    localStorage.removeItem('auth_user')
  }

  return { jwt, user, isAuthenticated, login, logout }
})
