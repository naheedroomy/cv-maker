export interface ContactInfo {
  name: string
  email: string
  phone?: string
  linkedin?: string
  location?: string
  github?: string
  work_authorization?: string
}

export interface LanguageItem {
  language: string
  level: string
}

export interface BaseCV {
  contact: ContactInfo
  summary: string
  experience: ExperienceItem[]
  skills: string[]
  education: EducationItem[]
  projects: ProjectItem[]
  certifications: string[]
  languages: LanguageItem[]
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
  action: 'modified' | 'added' | 'removed' | 'reordered' | 'unchanged' | 'substituted' | 'soft-fabricated'
}

export interface TailoredCV {
  contact: ContactInfo
  summary: string
  experience: ExperienceItem[]
  skills: string[]
  education: EducationItem[]
  projects: ProjectItem[]
  certifications: string[]
  languages: LanguageItem[]
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
  applied_at: string | null
  status: JobStatus
  created_at: string
  updated_at: string
  tailored_cv: TailoredCV | null
  gap_diff: GapItem[] | null
  validation_warnings: string[] | null
  pdf_url: string | null
  cover_letter_text: string | null
  cover_letter_notes: string | null
  cover_letter_model: string | null
  cover_letter_tone: string | null
  cv_history: CvHistoryEntry[] | null
  cl_history: ClHistoryEntry[] | null
  user_notes: string | null
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
  creativity_level?: number  // 0-6, default 2 (Moderate)
  user_notes?: string  // optional guidance for CV tailoring
}
