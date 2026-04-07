import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { BaseCV, ExperienceItem, EducationItem, ProjectItem } from '@/types'
import { apiFetch } from '@/utils/apiFetch'

export const useCvStore = defineStore('cv', () => {
  const cv = ref<BaseCV | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const uploading = ref(false)
  const error = ref('')
  const uploadProgress = ref('')

  // ── Fetch ──────────────────────────────────────────────────────────────────

  async function fetchCv(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const res = await apiFetch('/api/cv/me')
      if (!res.ok) {
        error.value = `Failed to load CV: ${res.status}`
        return
      }
      const data = await res.json() as { has_cv: boolean; cv: BaseCV | null }
      cv.value = data.has_cv ? data.cv : null
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load CV'
    } finally {
      loading.value = false
    }
  }

  // ── Save ───────────────────────────────────────────────────────────────────

  async function saveCv(): Promise<void> {
    if (!cv.value) return
    saving.value = true
    error.value = ''
    try {
      const res = await apiFetch('/api/cv/me', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cv.value),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        error.value = (body as { detail?: string }).detail ?? `Save failed: ${res.status}`
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to save CV'
    } finally {
      saving.value = false
    }
  }

  // ── Delete ─────────────────────────────────────────────────────────────────

  async function deleteCv(): Promise<void> {
    error.value = ''
    try {
      const res = await apiFetch('/api/cv/me', { method: 'DELETE' })
      if (!res.ok) {
        error.value = `Delete failed: ${res.status}`
        return
      }
      cv.value = null
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete CV'
    }
  }

  // ── Upload PDF ─────────────────────────────────────────────────────────────

  async function uploadPdf(file: File): Promise<void> {
    uploading.value = true
    uploadProgress.value = 'Uploading PDF...'
    error.value = ''
    try {
      const formData = new FormData()
      formData.append('file', file)
      // Do NOT set Content-Type — browser sets multipart boundary automatically
      const res = await apiFetch('/api/cv/upload', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json() as { success: boolean; message: string; cv: BaseCV | null }
      if (data.success && data.cv) {
        cv.value = data.cv
      } else {
        error.value = data.message ?? 'Upload failed'
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Upload failed'
    } finally {
      uploading.value = false
      uploadProgress.value = ''
    }
  }

  // ── Create Empty ───────────────────────────────────────────────────────────

  function createEmptyCv(): void {
    cv.value = {
      contact: {
        name: '',
        email: '',
        phone: '',
        linkedin: '',
        location: '',
        github: '',
      },
      summary: '',
      experience: [] as ExperienceItem[],
      skills: [] as string[],
      education: [] as EducationItem[],
      projects: [] as ProjectItem[],
      certifications: [] as string[],
    }
  }

  return {
    cv,
    loading,
    saving,
    uploading,
    error,
    uploadProgress,
    fetchCv,
    saveCv,
    deleteCv,
    uploadPdf,
    createEmptyCv,
  }
})
