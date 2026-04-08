import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { JobResponse, JobCreate, TailoredCV, GapItem } from '@/types'
import { apiFetch } from '@/utils/apiFetch'

// Re-export types for convenience
export type { JobResponse, JobCreate, TailoredCV, GapItem }

export const useJobStore = defineStore('jobs', () => {
  const jobs = ref<JobResponse[]>([])
  const currentJob = ref<JobResponse | null>(null)
  const error = ref<string | null>(null)

  // SSE and polling references — plain let (not reactive, internal implementation details)
  let _sse: EventSource | null = null
  let _pollInterval: ReturnType<typeof setInterval> | null = null


  // ── Fetch Actions ──────────────────────────────────────────────────────────

  async function fetchJobs(): Promise<void> {
    const res = await apiFetch('/api/jobs')
    if (!res.ok) throw new Error(`GET /api/jobs failed: ${res.status}`)
    const data: JobResponse[] = await res.json()
    // Sort by created_at descending — most recent first
    jobs.value = data.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
  }

  async function fetchJob(jobId: string): Promise<void> {
    const res = await apiFetch(`/api/jobs/${jobId}`)
    if (!res.ok) throw new Error(`GET /api/jobs/${jobId} failed: ${res.status}`)
    currentJob.value = await res.json()
  }

  async function submitJob(payload: JobCreate): Promise<string> {
    const res = await apiFetch('/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error((body as { detail?: string }).detail ?? `POST /api/jobs failed: ${res.status}`)
    }
    const job: JobResponse = await res.json()
    jobs.value = [job, ...jobs.value]
    return job.id
  }

  async function cancelJob(jobId: string): Promise<void> {
    const res = await apiFetch(`/api/jobs/${jobId}`, { method: 'DELETE' })
    if (res.status === 409) throw new Error('Job already completed or cancelled')
    if (!res.ok) throw new Error(`Cancel failed: ${res.status}`)
    // 204 No Content — update store optimistically
    if (currentJob.value?.id === jobId) {
      currentJob.value = { ...currentJob.value, status: 'cancelled' }
    }
    const idx = jobs.value.findIndex((j) => j.id === jobId)
    if (idx !== -1) jobs.value[idx] = { ...jobs.value[idx], status: 'cancelled' } as JobResponse
    closeSSE()
  }

  async function toggleApplied(jobId: string): Promise<void> {
    const res = await apiFetch(`/api/jobs/${jobId}/applied`, { method: 'PATCH' })
    if (!res.ok) throw new Error(`Toggle applied failed: ${res.status}`)
    const updated: JobResponse = await res.json()
    if (currentJob.value?.id === jobId) {
      currentJob.value = updated
    }
    const idx = jobs.value.findIndex((j) => j.id === jobId)
    if (idx !== -1) jobs.value[idx] = updated
  }

  async function deleteJob(jobId: string): Promise<void> {
    const res = await apiFetch(`/api/jobs/${jobId}/remove`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`Delete failed: ${res.status}`)
    jobs.value = jobs.value.filter((j) => j.id !== jobId)
    if (currentJob.value?.id === jobId) {
      currentJob.value = null
    }
    closeSSE()
  }

  async function regenerateJob(job: JobResponse, model?: string, creativityLevel?: number): Promise<string> {
    const res = await apiFetch(`/api/jobs/${job.id}/regenerate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: model ?? null,
        creativity_level: creativityLevel ?? null,
      }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error((body as { detail?: string }).detail ?? `Regenerate failed: ${res.status}`)
    }
    const updated: JobResponse = await res.json()
    // Update store
    if (currentJob.value?.id === job.id) {
      currentJob.value = updated
    }
    const idx = jobs.value.findIndex((j) => j.id === job.id)
    if (idx !== -1) jobs.value[idx] = updated
    return job.id
  }

  async function downloadPdf(jobId: string, companyName: string, version?: number): Promise<void> {
    const url_path = version ? `/api/jobs/${jobId}/pdf/${version}` : `/api/jobs/${jobId}/pdf`
    const res = await apiFetch(url_path)
    if (!res.ok) throw new Error(`PDF not available: ${res.status}`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const suffix = version ? `-V${version}` : ''
    a.download = `${companyName}${suffix}-CV.pdf`
    a.click()
    URL.revokeObjectURL(url) // Free memory immediately after click
  }

  // ── SSE Lifecycle ──────────────────────────────────────────────────────────

  function openSSE(jobId: string): void {
    closeSSE() // Defensive close before new connection — prevents Pitfall 6 (SSE connection leak)

    // Use relative URL — NOT hardcoded localhost (Pitfall 2: CORS)
    _sse = new EventSource(`/api/jobs/${jobId}/events`)

    // Use addEventListener for named events — NOT onmessage (Pitfall 1)
    _sse.addEventListener('status', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as Partial<JobResponse>
      if (currentJob.value?.id === jobId) {
        currentJob.value = { ...currentJob.value, ...data } as JobResponse
      }
      // Also update the jobs list entry
      const idx = jobs.value.findIndex((j) => j.id === jobId)
      if (idx !== -1) jobs.value[idx] = { ...jobs.value[idx], ...data } as JobResponse
    })

    _sse.addEventListener('complete', (e: MessageEvent) => {
      const data = JSON.parse(e.data) as JobResponse
      // Merge with existing job to preserve fields the SSE payload may not include (e.g. created_at)
      if (currentJob.value?.id === jobId) {
        currentJob.value = { ...currentJob.value, ...data, created_at: currentJob.value.created_at }
      } else {
        currentJob.value = data
      }
      const idx = jobs.value.findIndex((j) => j.id === jobId)
      const existing = jobs.value[idx]
      if (idx !== -1 && existing) {
        jobs.value[idx] = { ...existing, ...data, created_at: existing.created_at }
      }
      closeSSE()
    })

    _sse.onerror = () => {
      closeSSE()
      // Fallback: poll GET /api/jobs/:id every 5s on SSE error
      _pollInterval = setInterval(async () => {
        try {
          const res = await apiFetch(`/api/jobs/${jobId}`)
          if (res.ok) {
            const job: JobResponse = await res.json()
            currentJob.value = job
            const idx = jobs.value.findIndex((j) => j.id === jobId)
            if (idx !== -1) jobs.value[idx] = job
            // Stop polling on terminal status
            if (['complete', 'failed', 'cancelled'].includes(job.status)) {
              _stopFallbackPoll()
            }
          }
        } catch {
          // ignore network errors during fallback polling
        }
      }, 5000)
    }
  }

  function closeSSE(): void {
    if (_sse) {
      _sse.close()
      _sse = null
    }
    _stopFallbackPoll()
  }

  function _stopFallbackPoll(): void {
    if (_pollInterval) {
      clearInterval(_pollInterval)
      _pollInterval = null
    }
  }

  // ── Cover Letter Actions ───────────────────────────────────────────────────

  async function generateCoverLetter(
    jobId: string,
    model: string,
    tone: string,
    userNotes: string,
  ): Promise<string> {
    const res = await apiFetch(`/api/jobs/${jobId}/cover-letter`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, tone, user_notes: userNotes }),
    })
    if (!res.ok && res.status !== 202) {
      const body = await res.json().catch(() => ({}))
      throw new Error((body as { detail?: string }).detail ?? `Cover letter generation failed: ${res.status}`)
    }

    // Clear cover letter in local state immediately
    if (currentJob.value?.id === jobId) {
      currentJob.value = { ...currentJob.value, cover_letter_text: '', cover_letter_notes: userNotes }
    }

    // Poll until cover letter appears (background generation)
    const text = await _pollCoverLetter(jobId)
    return text
  }

  async function _pollCoverLetter(jobId: string): Promise<string> {
    for (let i = 0; i < 60; i++) {
      await new Promise(r => setTimeout(r, 3000))
      const res = await apiFetch(`/api/jobs/${jobId}`)
      if (!res.ok) continue
      const job = await res.json() as JobResponse
      if (currentJob.value?.id === jobId) {
        currentJob.value = job
      }
      // null = never generated, '' = generating, non-empty = done
      if (job.cover_letter_text === null) {
        // Generation failed — worker reset to null
        throw new Error('Cover letter generation failed. Check your API key in Settings.')
      }
      if (job.cover_letter_text && job.cover_letter_text.length > 0) {
        return job.cover_letter_text
      }
    }
    throw new Error('Cover letter generation timed out')
  }

  async function saveCoverLetter(
    jobId: string,
    coverLetterText: string,
    userNotes: string,
  ): Promise<void> {
    const res = await apiFetch(`/api/jobs/${jobId}/cover-letter`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cover_letter_text: coverLetterText, cover_letter_notes: userNotes }),
    })
    if (!res.ok) throw new Error(`Save cover letter failed: ${res.status}`)
    if (currentJob.value?.id === jobId) {
      currentJob.value = {
        ...currentJob.value,
        cover_letter_text: coverLetterText,
        cover_letter_notes: userNotes,
      }
    }
  }

  async function downloadCoverLetterPdf(jobId: string, companyName: string): Promise<void> {
    const res = await apiFetch(`/api/jobs/${jobId}/cover-letter/pdf`)
    if (!res.ok) throw new Error(`Cover letter PDF not available: ${res.status}`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${companyName}-Cover-Letter.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    jobs,
    currentJob,
    error,
    fetchJobs,
    fetchJob,
    submitJob,
    cancelJob,
    toggleApplied,
    deleteJob,
    regenerateJob,
    downloadPdf,
    openSSE,
    closeSSE,
    generateCoverLetter,
    saveCoverLetter,
    downloadCoverLetterPdf,
  }
})
