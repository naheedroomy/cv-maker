import { createRouter, createWebHistory } from 'vue-router'
import JobFormView from '@/views/JobFormView.vue'
import JobDetailView from '@/views/JobDetailView.vue'

const CvConverterView = () => import('@/views/CvConverterView.vue')

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: JobFormView },
    { path: '/jobs/:id', component: JobDetailView },
    { path: '/convert', component: CvConverterView },
  ],
})
