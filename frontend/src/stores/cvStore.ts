import { ref, watch } from 'vue'
import { defineStore } from 'pinia'
import type {
  BaseCV,
  BaseCvDetail,
  BaseCvMeta,
  EducationItem,
  ExperienceItem,
  LanguageItem,
  ProjectItem,
} from '@/types'
import { apiFetch } from '@/utils/apiFetch'

export const useCvStore = defineStore('cv', () => {
  const baseCvs = ref<BaseCvMeta[]>([])
  const activeCvId = ref<string | null>(null)
  const activeCv = ref<BaseCV | null>(null)
  const activeCvName = ref<string>('')
  const activeCvIsDefault = ref<boolean>(false)
  const cv = ref<BaseCV | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const uploading = ref(false)
  const error = ref('')
  const uploadProgress = ref('')

  // Keep cv and activeCv in sync for backward compatibility
  watch(activeCv, (val) => {
    if (cv.value !== val) {
      cv.value = val
    }
  })
  watch(cv, (val) => {
    if (activeCv.value !== val) {
      activeCv.value = val
    }
  })

  // ── Select Base CV ─────────────────────────────────────────────────────────

  async function selectBaseCv(id: string): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const res = await apiFetch(`/api/cv/${id}`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        error.value = (body as { detail?: string }).detail ?? `Failed to load Base CV: ${res.status}`
        return
      }
      const data = (await res.json()) as BaseCvDetail
      activeCvId.value = data.id
      activeCv.value = data.cv
      activeCvName.value = data.name
      activeCvIsDefault.value = data.is_default
      cv.value = data.cv
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load Base CV'
    } finally {
      loading.value = false
    }
  }

  // ── Fetch Base CVs ─────────────────────────────────────────────────────────

  async function fetchBaseCvs(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const res = await apiFetch('/api/cv/list')
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        error.value = (body as { detail?: string }).detail ?? `Failed to load Base CVs: ${res.status}`
        return
      }
      const data = (await res.json()) as BaseCvMeta[]
      baseCvs.value = data
      if (data.length === 0) {
        activeCvId.value = null
        activeCv.value = null
        activeCvName.value = ''
        activeCvIsDefault.value = false
        cv.value = null
        return
      }
      const exists = activeCvId.value ? data.some((c) => c.id === activeCvId.value) : false
      if (!exists) {
        const target = data.find((c) => c.is_default) || data[0]
        if (target) {
          await selectBaseCv(target.id)
        }
      } else {
        const currentMeta = data.find((c) => c.id === activeCvId.value)
        if (currentMeta) {
          activeCvName.value = currentMeta.name
          activeCvIsDefault.value = currentMeta.is_default
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load Base CVs'
    } finally {
      loading.value = false
    }
  }

  // ── Create Base CV ─────────────────────────────────────────────────────────

  async function createBaseCv(
    name: string,
    options?: {
      sourceId?: string
      cv?: BaseCV
      file?: File
      provider?: string
      model?: string
    },
  ): Promise<void> {
    error.value = ''
    if (options?.file) {
      uploading.value = true
      uploadProgress.value = 'Parsing PDF CV with AI...'
      try {
        const formData = new FormData()
        formData.append('file', options.file)
        formData.append('name', name)
        if (options.provider) formData.append('provider', options.provider)
        if (options.model) formData.append('model', options.model)

        const res = await apiFetch('/api/cv/upload', {
          method: 'POST',
          body: formData,
        })
        const data = (await res.json()) as {
          success: boolean
          message: string
          cv?: BaseCV | null
          base_cv_id?: string | null
          name?: string | null
        }
        if (!res.ok || !data.success) {
          error.value = data.message || `Upload failed: ${res.status}`
          return
        }
        await fetchBaseCvs()
        if (data.base_cv_id) {
          await selectBaseCv(data.base_cv_id)
        }
      } catch (err) {
        error.value = err instanceof Error ? err.message : 'Upload failed'
      } finally {
        uploading.value = false
        uploadProgress.value = ''
      }
    } else {
      saving.value = true
      try {
        const payload: Record<string, unknown> = { name }
        if (options?.sourceId) payload.source_id = options.sourceId
        if (options?.cv) payload.cv = options.cv

        const res = await apiFetch('/api/cv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          error.value = (body as { detail?: string }).detail ?? `Create Base CV failed: ${res.status}`
          return
        }
        const created = (await res.json()) as BaseCvDetail
        activeCvId.value = created.id
        activeCv.value = created.cv
        activeCvName.value = created.name
        activeCvIsDefault.value = created.is_default
        cv.value = created.cv
        await fetchBaseCvs()
      } catch (err) {
        error.value = err instanceof Error ? err.message : 'Create Base CV failed'
      } finally {
        saving.value = false
      }
    }
  }

  // ── Save Active CV ─────────────────────────────────────────────────────────

  async function saveActiveCv(): Promise<void> {
    const targetCv = activeCv.value ?? cv.value
    if (!activeCvId.value || !targetCv) return
    saving.value = true
    error.value = ''
    try {
      const res = await apiFetch(`/api/cv/${activeCvId.value}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: activeCvName.value,
          cv: targetCv,
        }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        error.value = (body as { detail?: string }).detail ?? `Save failed: ${res.status}`
        return
      }
      const updated = (await res.json()) as BaseCvDetail
      activeCvName.value = updated.name
      activeCv.value = updated.cv
      cv.value = updated.cv
      const idx = baseCvs.value.findIndex((c) => c.id === activeCvId.value)
      const existing = idx !== -1 ? baseCvs.value[idx] : undefined
      if (existing) {
        baseCvs.value[idx] = {
          ...existing,
          name: updated.name,
          updated_at: updated.updated_at,
        }
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to save CV'
    } finally {
      saving.value = false
    }
  }

  // ── Set Default Base CV ───────────────────────────────────────────────────

  async function setDefaultBaseCv(id: string): Promise<void> {
    error.value = ''
    try {
      const res = await apiFetch(`/api/cv/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_default: true }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        error.value = (body as { detail?: string }).detail ?? `Set default failed: ${res.status}`
        return
      }
      baseCvs.value = baseCvs.value.map((c) => ({
        ...c,
        is_default: c.id === id,
      }))
      activeCvIsDefault.value = activeCvId.value === id
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Set default failed'
    }
  }

  // ── Rename Base CV ─────────────────────────────────────────────────────────

  async function renameBaseCv(id: string, newName: string): Promise<void> {
    error.value = ''
    try {
      const res = await apiFetch(`/api/cv/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newName }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        error.value = (body as { detail?: string }).detail ?? `Rename failed: ${res.status}`
        return
      }
      const idx = baseCvs.value.findIndex((c) => c.id === id)
      const existing = idx !== -1 ? baseCvs.value[idx] : undefined
      if (existing) {
        baseCvs.value[idx] = {
          ...existing,
          name: newName,
        }
      }
      if (activeCvId.value === id) {
        activeCvName.value = newName
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Rename failed'
    }
  }

  // ── Delete Base CV ─────────────────────────────────────────────────────────

  async function deleteBaseCv(id: string): Promise<void> {
    error.value = ''
    try {
      const res = await apiFetch(`/api/cv/${id}`, { method: 'DELETE' })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        error.value = (body as { detail?: string }).detail ?? `Delete failed: ${res.status}`
        return
      }
      if (activeCvId.value === id) {
        activeCvId.value = null
        activeCv.value = null
        activeCvName.value = ''
        activeCvIsDefault.value = false
        cv.value = null
      }
      await fetchBaseCvs()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Delete failed'
    }
  }

  // ── Download Base CV PDF ───────────────────────────────────────────────────

  async function downloadBaseCvPdf(id?: string): Promise<void> {
    const targetId = id ?? activeCvId.value
    if (!targetId) return
    error.value = ''
    try {
      const cacheBuster = `t=${Date.now()}`
      const targetCv = activeCv.value ?? cv.value
      const res = await apiFetch(`/api/cv/${targetId}/pdf?${cacheBuster}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: targetCv ? JSON.stringify(targetCv) : undefined,
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as { detail?: string }).detail ?? `PDF generation failed: ${res.status}`)
      }
      const blob = await res.blob()
      const contentDisposition = res.headers.get('content-disposition')
      let filename = 'Base-CV.pdf'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^";]+)"?/)
        if (match && match[1]) {
          filename = match[1]
        }
      } else if (activeCvName.value) {
        filename = `${activeCvName.value.replace(/\s+/g, '-')}.pdf`
      }
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Download failed'
    }
  }

  // ── Backward Compatibility Actions ─────────────────────────────────────────

  async function fetchCv(): Promise<void> {
    await fetchBaseCvs()
  }

  async function saveCv(): Promise<void> {
    if (activeCvId.value) {
      await saveActiveCv()
    } else if (cv.value) {
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
  }

  async function deleteCv(): Promise<void> {
    if (activeCvId.value && baseCvs.value.length > 1) {
      await deleteBaseCv(activeCvId.value)
    } else {
      error.value = ''
      try {
        const res = await apiFetch('/api/cv/me', { method: 'DELETE' })
        if (!res.ok) {
          error.value = `Delete failed: ${res.status}`
          return
        }
        cv.value = null
        activeCv.value = null
        activeCvId.value = null
        activeCvName.value = ''
        activeCvIsDefault.value = false
      } catch (err) {
        error.value = err instanceof Error ? err.message : 'Failed to delete CV'
      }
    }
  }

  async function uploadPdf(file: File): Promise<void> {
    await createBaseCv('Uploaded Base CV', { file })
  }

  function createEmptyCv(): void {
    const empty: BaseCV = {
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
      languages: [] as LanguageItem[],
    }
    cv.value = empty
    activeCv.value = empty
  }

  return {
    // State
    baseCvs,
    activeCvId,
    activeCv,
    activeCvName,
    activeCvIsDefault,
    cv,
    loading,
    saving,
    uploading,
    error,
    uploadProgress,
    // Actions
    fetchBaseCvs,
    selectBaseCv,
    createBaseCv,
    saveActiveCv,
    setDefaultBaseCv,
    renameBaseCv,
    deleteBaseCv,
    downloadBaseCvPdf,
    // Backward compatibility
    fetchCv,
    saveCv,
    deleteCv,
    uploadPdf,
    createEmptyCv,
  }
})
