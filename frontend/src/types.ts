export interface ContactInfo {
  name: string
  email: string
  phone?: string
  linkedin?: string
  location?: string
  github?: string
}

export interface BaseCV {
  contact: ContactInfo
  summary: string
  experience: ExperienceItem[]
  skills: string[]
  education: EducationItem[]
  projects: ProjectItem[]
  certifications: string[]
}

export interface ExperienceItem {
  company: string
  title: string
  location?: string
  start: string
  end: string | null
  bullets: string[]
  technologies: string[]
}

export interface EducationItem {
  institution: string
  degree: string
  field: string | null
  year: number | null
}

export interface ProjectItem {
  name: string
  description: string
  technologies: string[]
  url?: string
}

export interface TailoringNote {
  section: string
  change: string
  reason: string
  action: 'modified' | 'added' | 'removed' | 'reordered' | 'unchanged'
}

export interface TailoredCV {
  contact: ContactInfo
  summary: string
  experience: ExperienceItem[]
  skills: string[]
  education: EducationItem[]
  projects: ProjectItem[]
  certifications: string[]
  highlighted_technologies: string[]
  tailoring_notes: TailoringNote[]
}

export type MatchLevel = 'strong' | 'partial' | 'missing'

export interface GapItem {
  requirement: string
  match_level: MatchLevel
  evidence: string
}

export type JobStatus = 'pending' | 'running' | 'complete' | 'failed' | 'cancelled'

export interface JobResponse {
  id: string
  company_name: string
  job_link: string | null
  job_text: string | null
  model: string
  creativity_level: number
  applied: boolean
  status: JobStatus
  created_at: string
  updated_at: string
  tailored_cv: TailoredCV | null
  gap_diff: GapItem[] | null
  pdf_url: string | null
  cover_letter_text: string | null
  cover_letter_notes: string | null
  cover_letter_model: string | null
  cover_letter_tone: string | null
  cv_history: CvHistoryEntry[] | null
  cl_history: ClHistoryEntry[] | null
}

export interface CvHistoryEntry {
  version: number
  model: string
  creativity_level: number
  pdf_path: string | null
  created_at: string
}

export interface ClHistoryEntry {
  version: number
  text: string
  model: string | null
  tone: string | null
  created_at: string
}

export interface JobCreate {
  company_name: string
  job_link?: string
  job_text: string
  model?: string  // "claude-haiku" (default) or "gemini-flash"
  creativity_level?: number  // 0-5, default 2 (Moderate)
}
