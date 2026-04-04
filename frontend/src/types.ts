export interface ContactInfo {
  name: string
  email: string
  phone: string
  linkedin: string
  location: string
}

export interface ExperienceItem {
  company: string
  title: string
  location: string
  start_date: string
  end_date: string
  bullets: string[]
}

export interface EducationItem {
  institution: string
  degree: string
  graduation_date: string
  details: string[]
}

export interface ProjectItem {
  name: string
  description: string
  technologies: string[]
  url: string
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
}

export interface GapItem {
  requirement: string
  present: boolean
  evidence: string
}

export type JobStatus = 'pending' | 'running' | 'complete' | 'failed' | 'cancelled'

export interface JobResponse {
  id: string
  company_name: string
  status: JobStatus
  created_at: string
  updated_at: string
  tailored_cv: TailoredCV | null
  gap_diff: GapItem[] | null
  pdf_url: string | null
}

export interface JobCreate {
  company_name: string
  job_link?: string
  job_text: string
}
