import { createRouter, createWebHistory } from 'vue-router'
import JobFormView from '@/views/JobFormView.vue'
import JobDetailView from '@/views/JobDetailView.vue'

const CvConverterView = () => import('@/views/CvConverterView.vue')
const BaseCvView = () => import('@/views/BaseCvView.vue')
const SettingsView = () => import('@/views/SettingsView.vue')
const SignInView = () => import('@/views/SignInView.vue')

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/signin', component: SignInView, meta: { public: true } },
    { path: '/', component: JobFormView },
    { path: '/jobs/:id', component: JobDetailView },
    { path: '/convert', component: CvConverterView },
    { path: '/base-cv', component: BaseCvView },
    { path: '/settings', component: SettingsView },
  ],
})

router.beforeEach(async (to) => {
  // Dynamic import to avoid circular dependency — Pinia must be created first
  const { useAuthStore } = await import('@/stores/authStore')
  const authStore = useAuthStore()

  // Allow public routes without auth
  if (to.meta.public) return true

  // Redirect unauthenticated users to sign-in
  if (!authStore.isAuthenticated) {
    return { path: '/signin' }
  }

  return true
})
