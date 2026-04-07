import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export interface AuthUser {
  id: number
  email: string
  name: string
  picture: string
}

export const useAuthStore = defineStore('auth', () => {
  const jwt = ref<string | null>(null)
  const user = ref<AuthUser | null>(null)
  const isAuthenticated = computed(() => !!jwt.value)

  // On store creation, restore from localStorage — but validate JWT expiry
  const savedJwt = localStorage.getItem('jwt')
  if (savedJwt) {
    try {
      const payload = JSON.parse(atob(savedJwt.split('.')[1]!)) as { exp?: number }
      if (payload.exp && payload.exp * 1000 > Date.now()) {
        jwt.value = savedJwt
        const savedUser = localStorage.getItem('auth_user')
        if (savedUser) user.value = JSON.parse(savedUser) as AuthUser
      } else {
        // Expired — clean up
        localStorage.removeItem('jwt')
        localStorage.removeItem('auth_user')
      }
    } catch {
      // Corrupt JWT — clean up
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
