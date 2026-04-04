import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { JobResponse, JobCreate, TailoredCV, GapItem } from '@/types'

// Re-export types for convenience
export type { JobResponse, JobCreate, TailoredCV, GapItem }

export const useJobStore = defineStore('jobs', () => {
  const jobs = ref<JobResponse[]>([])
  const currentJob = ref<JobResponse | null>(null)
  const error = ref<string | null>(null)

  // SSE and polling references — plain let (not reactive, internal implementation details)
  let _sse: EventSource | null = null
  let _pollInterval: ReturnType<typeof setInterval> | null = null
  let _sidebarInterval: ReturnType<typeof setInterval> | null = null

  // ── Fetch Actions ──────────────────────────────────────────────────────────

  async function fetchJobs(): Promise<void> {
    const res = await fetch('/api/jobs')
    if (!res.ok) throw new Error(`GET /api/jobs failed: ${res.status}`)
    const data: JobResponse[] = await res.json()
    // Sort by created_at descending — most recent first
    jobs.value = data.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    )
  }

  async function fetchJob(jobId: string): Promise<void> {
    const res = await fetch(`/api/jobs/${jobId}`)
    if (!res.ok) throw new Error(`GET /api/jobs/${jobId} failed: ${res.status}`)
    currentJob.value = await res.json()
  }

  async function submitJob(payload: JobCreate): Promise<string> {
    const res = await fetch('/api/jobs', {
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
    const res = await fetch(`/api/jobs/${jobId}`, { method: 'DELETE' })
    if (res.status === 409) throw new Error('Job already completed or cancelled')
    if (!res.ok) throw new Error(`Cancel failed: ${res.status}`)
    // 204 No Content — update store optimistically
    if (currentJob.value?.id === jobId) {
      currentJob.value = { ...currentJob.value, status: 'cancelled' }
    }
    const idx = jobs.value.findIndex((j) => j.id === jobId)
    if (idx !== -1) jobs.value[idx] = { ...jobs.value[idx], status: 'cancelled' }
    closeSSE()
  }

  async function downloadPdf(jobId: string, companyName: string): Promise<void> {
    const res = await fetch(`/api/jobs/${jobId}/pdf`)
    if (!res.ok) throw new Error(`PDF not available: ${res.status}`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${companyName}-CV.pdf`
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
      currentJob.value = data
      const idx = jobs.value.findIndex((j) => j.id === jobId)
      if (idx !== -1) jobs.value[idx] = data
      closeSSE()
    })

    _sse.onerror = () => {
      closeSSE()
      // Fallback: poll GET /api/jobs/:id every 5s on SSE error
      _pollInterval = setInterval(async () => {
        try {
          const res = await fetch(`/api/jobs/${jobId}`)
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

  // ── Sidebar Polling ────────────────────────────────────────────────────────

  function startSidebarPolling(): void {
    stopSidebarPolling()
    _sidebarInterval = setInterval(() => {
      fetchJobs().catch(() => {})
    }, 30_000)
  }

  function stopSidebarPolling(): void {
    if (_sidebarInterval) {
      clearInterval(_sidebarInterval)
      _sidebarInterval = null
    }
  }

  return {
    jobs,
    currentJob,
    error,
    fetchJobs,
    fetchJob,
    submitJob,
    cancelJob,
    downloadPdf,
    openSSE,
    closeSSE,
    startSidebarPolling,
    stopSidebarPolling,
  }
})
