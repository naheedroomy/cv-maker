import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export interface AuthUser {
  id: number
  email: string
  name: string
  picture: string
}

export const useAuthStore = defineStore('auth', () => {
  const jwt = ref<string | null>(localStorage.getItem('jwt'))
  const user = ref<AuthUser | null>(null)
  const isAuthenticated = computed(() => !!jwt.value)

  // On store creation, restore user from localStorage if JWT exists
  const savedUser = localStorage.getItem('auth_user')
  if (savedUser) {
    try {
      user.value = JSON.parse(savedUser) as AuthUser
    } catch {
      /* ignore corrupt data */
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
