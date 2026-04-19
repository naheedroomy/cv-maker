<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useCvStore } from '@/stores/cvStore'
import PdfDropZone from '@/components/PdfDropZone.vue'
import CvEditorSection from '@/components/CvEditorSection.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import type { ExperienceItem, EducationItem, ProjectItem, LanguageItem } from '@/types'
import { apiFetch } from '@/utils/apiFetch'

const store = useCvStore()
const { cv, loading, saving, uploading, uploadProgress, error } = storeToRefs(store)

const downloading = ref(false)

const collapsed = reactive({
  contact: false,
  summary: false,
  experience: false,
  education: false,
  skills: false,
  certifications: false,
  projects: false,
  languages: false,
})

// Section ordering for drag-and-drop
const sectionOrder = ref([
  'contact', 'summary', 'experience', 'education', 'skills', 'certifications', 'projects', 'languages',
])
const draggedSection = ref<string | null>(null)

function onDragStartSection(section: string) {
  draggedSection.value = section
}

function onDropSection(targetSection: string) {
  if (!draggedSection.value || draggedSection.value === targetSection) return
  const fromIdx = sectionOrder.value.indexOf(draggedSection.value)
  const toIdx = sectionOrder.value.indexOf(targetSection)
  if (fromIdx === -1 || toIdx === -1) return
  sectionOrder.value.splice(fromIdx, 1)
  sectionOrder.value.splice(toIdx, 0, draggedSection.value)
  draggedSection.value = null
}

function onDragOverSection(e: DragEvent) {
  e.preventDefault()
}

onMounted(() => {
  store.fetchCv()
})

// ── Upload / Save / Delete ─────────────────────────────────────────────────

function handleUpload(file: File) {
  store.uploadPdf(file)
}

async function handleSave() {
  await store.saveCv()
}

function handleDelete() {
  if (confirm('Remove your CV? This cannot be undone.')) {
    store.deleteCv()
  }
}

async function handleDownload() {
  if (!cv.value) return
  downloading.value = true
  try {
    const res = await apiFetch('/api/cv/me/pdf', {
      method: 'POST',
      body: JSON.stringify(cv.value),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error((body as { detail?: string }).detail ?? `PDF generation failed: ${res.status}`)
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'Base-CV.pdf'
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    store.error = err instanceof Error ? err.message : 'Download failed'
  } finally {
    downloading.value = false
  }
}

function handleCreateEmpty() {
  store.createEmptyCv()
}

// ── Work Experience ────────────────────────────────────────────────────────

function addExperience() {
  cv.value?.experience.push({
    company: '',
    title: '',
    location: '',
    start: '',
    end: null,
    bullets: [],
    technologies: [],
  } as ExperienceItem)
}

function removeExperience(index: number) {
  cv.value?.experience.splice(index, 1)
}

function addBullet(expIndex: number) {
  const exp = cv.value?.experience[expIndex]
  if (!exp) return
  exp.bullets.push('')
}

function removeBullet(expIndex: number, bulletIndex: number) {
  const exp = cv.value?.experience[expIndex]
  if (!exp) return
  exp.bullets.splice(bulletIndex, 1)
}

function addTechnology(expIndex: number) {
  const exp = cv.value?.experience[expIndex]
  if (!exp) return
  exp.technologies.push('')
}

function removeTechnology(expIndex: number, techIndex: number) {
  const exp = cv.value?.experience[expIndex]
  if (!exp) return
  exp.technologies.splice(techIndex, 1)
}

// ── Education ──────────────────────────────────────────────────────────────

function addEducation() {
  cv.value?.education.push({
    institution: '',
    degree: '',
    field: null,
    year: null,
  } as EducationItem)
}

function removeEducation(index: number) {
  cv.value?.education.splice(index, 1)
}

// ── Skills ─────────────────────────────────────────────────────────────────

function addSkill() {
  cv.value?.skills.push('')
}

function removeSkill(index: number) {
  cv.value?.skills.splice(index, 1)
}

// ── Certifications ─────────────────────────────────────────────────────────

function addCertification() {
  cv.value?.certifications.push('')
}

function removeCertification(index: number) {
  cv.value?.certifications.splice(index, 1)
}

// ── Projects ───────────────────────────────────────────────────────────────

function addProject() {
  cv.value?.projects.push({
    name: '',
    description: '',
    technologies: [],
    url: '',
  } as ProjectItem)
}

function removeProject(index: number) {
  cv.value?.projects.splice(index, 1)
}

function addProjectTech(projectIndex: number) {
  const proj = cv.value?.projects[projectIndex]
  if (!proj) return
  proj.technologies.push('')
}

function removeProjectTech(projectIndex: number, techIndex: number) {
  const proj = cv.value?.projects[projectIndex]
  if (!proj) return
  proj.technologies.splice(techIndex, 1)
}

// ── Languages ─────────────────────────────────────────────────────────────

function addLanguage() {
  if (!cv.value) return
  if (!cv.value.languages) cv.value.languages = []
  cv.value.languages.push({ language: '', level: '' } as LanguageItem)
}

function removeLanguage(index: number) {
  cv.value?.languages?.splice(index, 1)
}
</script>

<template>
  <div class="cv-editor">
    <div class="editor-header">
      <h2 class="editor-title">My CV</h2>
      <div v-if="cv" class="header-actions">
        <button
          type="button"
          class="btn-primary"
          :disabled="saving"
          @click="handleSave"
        >
          {{ saving ? 'Saving...' : 'Save CV' }}
        </button>
        <button
          type="button"
          class="btn-secondary"
          :disabled="downloading"
          @click="handleDownload"
        >
          {{ downloading ? 'Rendering...' : 'Download PDF' }}
        </button>
        <button
          type="button"
          class="btn-danger"
          @click="handleDelete"
        >
          Remove CV
        </button>
      </div>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>

    <div v-if="loading" class="loading-state">
      <LoadingSpinner />
      <span class="loading-text">Loading...</span>
    </div>

    <!-- No CV yet — upload zone + create from scratch -->
    <div v-else-if="!cv" class="empty-state">
      <PdfDropZone
        :uploading="uploading"
        :upload-progress="uploadProgress"
        @upload="handleUpload"
      />
      <p class="or-divider"><span>or</span></p>
      <div class="create-empty-row">
        <button type="button" class="btn-secondary" @click="handleCreateEmpty">
          Create CV from scratch
        </button>
      </div>
    </div>

    <!-- CV loaded — editor sections -->
    <template v-else>
      <!-- Re-upload zone (compact) at top -->
      <PdfDropZone
        :uploading="uploading"
        :upload-progress="uploadProgress"
        @upload="handleUpload"
      />

      <!-- Contact Section -->
      <CvEditorSection
        title="Contact"
        :collapsed="collapsed.contact"
        @toggle="collapsed.contact = !collapsed.contact"
      >
        <div class="form-grid">
          <div class="form-field">
            <label>Name</label>
            <input v-model="cv.contact.name" type="text" placeholder="Full Name" />
          </div>
          <div class="form-field">
            <label>Email</label>
            <input v-model="cv.contact.email" type="email" placeholder="you@example.com" />
          </div>
          <div class="form-field">
            <label>Phone</label>
            <input v-model="cv.contact.phone" type="text" placeholder="+1 555 000 0000" />
          </div>
          <div class="form-field">
            <label>Location</label>
            <input v-model="cv.contact.location" type="text" placeholder="City, Country" />
          </div>
          <div class="form-field">
            <label>LinkedIn</label>
            <input v-model="cv.contact.linkedin" type="url" placeholder="https://linkedin.com/in/you" />
          </div>
          <div class="form-field">
            <label>GitHub</label>
            <input v-model="cv.contact.github" type="url" placeholder="https://github.com/you" />
          </div>
          <div class="form-field form-field--full">
            <label>Work Authorization</label>
            <input v-model="cv.contact.work_authorization" type="text" placeholder="e.g. Possess a valid work permit in Germany (National Visa Type D)" />
          </div>
        </div>
      </CvEditorSection>

      <div
        v-for="section in sectionOrder"
        :key="section"
        class="draggable-section"
        draggable="true"
        @dragstart="onDragStartSection(section)"
        @dragover="onDragOverSection"
        @drop="onDropSection(section)"
      >
        <!-- Summary -->
        <CvEditorSection v-if="section === 'summary'" title="Summary" :collapsed="collapsed.summary" @toggle="collapsed.summary = !collapsed.summary" draggable-hint>
          <textarea v-model="cv.summary" rows="4" class="full-width" placeholder="Brief professional summary..." />
        </CvEditorSection>

        <!-- Work Experience -->
        <CvEditorSection v-else-if="section === 'experience'" title="Work Experience" :collapsed="collapsed.experience" @toggle="collapsed.experience = !collapsed.experience" draggable-hint>
          <div v-for="(exp, i) in cv.experience" :key="i" class="entry-card">
            <div class="entry-header">
              <span class="entry-label">{{ exp.company || 'New Position' }}</span>
              <button type="button" class="btn-icon-danger" @click="removeExperience(i)">Remove</button>
            </div>
            <div class="form-grid">
              <div class="form-field"><label>Company</label><input v-model="exp.company" type="text" placeholder="Acme Corp" /></div>
              <div class="form-field"><label>Title</label><input v-model="exp.title" type="text" placeholder="Senior Engineer" /></div>
              <div class="form-field"><label>Location</label><input v-model="exp.location" type="text" placeholder="Remote / City" /></div>
              <div class="form-field"><label>Start</label><input v-model="exp.start" type="text" placeholder="YYYY-MM" /></div>
              <div class="form-field"><label>End</label><input :value="exp.end ?? ''" @input="exp.end = ($event.target as HTMLInputElement).value || null" type="text" placeholder="YYYY-MM or blank for current" /></div>
            </div>
            <div class="list-editor">
              <label class="list-label">Bullets</label>
              <div v-for="(_, bi) in exp.bullets" :key="bi" class="list-item">
                <textarea v-model="exp.bullets[bi]" rows="2" class="list-input" placeholder="Describe your achievement..." />
                <button type="button" class="btn-icon-danger btn-icon-small" @click="removeBullet(i, bi)">x</button>
              </div>
              <button type="button" class="btn-text" @click="addBullet(i)">+ Add bullet</button>
            </div>
            <div class="list-editor">
              <label class="list-label">Technologies</label>
              <div class="tag-editor">
                <div v-for="(_, ti) in exp.technologies" :key="ti" class="tag-item">
                  <input v-model="exp.technologies[ti]" class="tag-input" placeholder="React" />
                  <button type="button" class="btn-icon-danger btn-icon-small" @click="removeTechnology(i, ti)">x</button>
                </div>
                <button type="button" class="btn-text" @click="addTechnology(i)">+ Add tech</button>
              </div>
            </div>
          </div>
          <button type="button" class="btn-secondary" @click="addExperience">+ Add Position</button>
        </CvEditorSection>

        <!-- Education -->
        <CvEditorSection v-else-if="section === 'education'" title="Education" :collapsed="collapsed.education" @toggle="collapsed.education = !collapsed.education" draggable-hint>
          <div v-for="(edu, i) in cv.education" :key="i" class="entry-card">
            <div class="entry-header">
              <span class="entry-label">{{ edu.institution || 'New Institution' }}</span>
              <button type="button" class="btn-icon-danger" @click="removeEducation(i)">Remove</button>
            </div>
            <div class="form-grid">
              <div class="form-field"><label>Institution</label><input v-model="edu.institution" type="text" placeholder="University of..." /></div>
              <div class="form-field"><label>Degree</label><input v-model="edu.degree" type="text" placeholder="Bachelor of Science" /></div>
              <div class="form-field"><label>Field</label><input :value="edu.field ?? ''" @input="edu.field = ($event.target as HTMLInputElement).value || null" type="text" placeholder="Computer Science" /></div>
              <div class="form-field"><label>Year</label><input :value="edu.year ?? ''" @input="edu.year = Number(($event.target as HTMLInputElement).value) || null" type="number" placeholder="2020" /></div>
            </div>
          </div>
          <button type="button" class="btn-secondary" @click="addEducation">+ Add Education</button>
        </CvEditorSection>

        <!-- Skills -->
        <CvEditorSection v-else-if="section === 'skills'" title="Skills" :collapsed="collapsed.skills" @toggle="collapsed.skills = !collapsed.skills" draggable-hint>
          <div class="tag-editor">
            <div v-for="(_, i) in cv.skills" :key="i" class="tag-item">
              <input v-model="cv.skills[i]" class="tag-input" placeholder="Python" />
              <button type="button" class="btn-icon-danger btn-icon-small" @click="removeSkill(i)">x</button>
            </div>
            <button type="button" class="btn-text" @click="addSkill">+ Add skill</button>
          </div>
        </CvEditorSection>

        <!-- Certifications -->
        <CvEditorSection v-else-if="section === 'certifications'" title="Certifications" :collapsed="collapsed.certifications" @toggle="collapsed.certifications = !collapsed.certifications" draggable-hint>
          <div class="list-editor">
            <div v-for="(_, i) in cv.certifications" :key="i" class="list-item list-item--inline">
              <input v-model="cv.certifications[i]" type="text" class="list-input" placeholder="AWS Solutions Architect" />
              <button type="button" class="btn-icon-danger btn-icon-small" @click="removeCertification(i)">x</button>
            </div>
            <button type="button" class="btn-text" @click="addCertification">+ Add certification</button>
          </div>
        </CvEditorSection>

        <!-- Projects -->
        <CvEditorSection v-else-if="section === 'projects'" title="Projects" :collapsed="collapsed.projects" @toggle="collapsed.projects = !collapsed.projects" draggable-hint>
          <div v-for="(proj, i) in cv.projects" :key="i" class="entry-card">
            <div class="entry-header">
              <span class="entry-label">{{ proj.name || 'New Project' }}</span>
              <button type="button" class="btn-icon-danger" @click="removeProject(i)">Remove</button>
            </div>
            <div class="form-grid">
              <div class="form-field"><label>Name</label><input v-model="proj.name" type="text" placeholder="My Project" /></div>
              <div class="form-field"><label>URL</label><input :value="proj.url ?? ''" @input="proj.url = ($event.target as HTMLInputElement).value || undefined" type="url" placeholder="https://github.com/..." /></div>
              <div class="form-field form-field--full"><label>Description</label><textarea v-model="proj.description" rows="2" class="full-width" placeholder="What did you build?" /></div>
            </div>
            <div class="list-editor">
              <label class="list-label">Technologies</label>
              <div class="tag-editor">
                <div v-for="(_, ti) in proj.technologies" :key="ti" class="tag-item">
                  <input v-model="proj.technologies[ti]" class="tag-input" placeholder="Vue" />
                  <button type="button" class="btn-icon-danger btn-icon-small" @click="removeProjectTech(i, ti)">x</button>
                </div>
                <button type="button" class="btn-text" @click="addProjectTech(i)">+ Add tech</button>
              </div>
            </div>
          </div>
          <button type="button" class="btn-secondary" @click="addProject">+ Add Project</button>
        </CvEditorSection>

        <!-- Languages -->
        <CvEditorSection v-else-if="section === 'languages'" title="Languages" :collapsed="collapsed.languages" @toggle="collapsed.languages = !collapsed.languages" draggable-hint>
          <div class="list-editor">
            <div v-for="(lang, i) in cv.languages" :key="i" class="list-item list-item--inline">
              <input v-model="lang.language" type="text" class="list-input" style="flex: 1" placeholder="English" />
              <input v-model="lang.level" type="text" class="list-input" style="flex: 0.5" placeholder="C2 / Native" />
              <button type="button" class="btn-icon-danger btn-icon-small" @click="removeLanguage(i)">x</button>
            </div>
            <button type="button" class="btn-text" @click="addLanguage">+ Add language</button>
          </div>
        </CvEditorSection>
      </div>
    </template>
  </div>
</template>

<style scoped>
.cv-editor {
  max-width: 800px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Header */
.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.editor-title {
  font-size: 22px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* Error */
.error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 14px;
}

/* Loading */
.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 48px 0;
  justify-content: center;
}

.loading-text {
  font-size: 14px;
  color: #6b7280;
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.or-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  color: #9ca3af;
  font-size: 13px;
}

.or-divider::before,
.or-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e2e8f0;
}

.create-empty-row {
  text-align: center;
}

/* Buttons */
.btn-primary {
  background: #2563eb;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  height: 36px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #ffffff;
  color: #374151;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  height: 36px;
  padding: 0 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-secondary:hover {
  background: #f9fafb;
}

.btn-danger {
  background: none;
  color: #dc2626;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  height: 36px;
  padding: 0 16px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.btn-danger:hover {
  background: #fef2f2;
}

.btn-text {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 0;
  text-decoration: none;
  display: inline-block;
}

.btn-text:hover {
  text-decoration: underline;
}

.btn-icon-danger {
  background: none;
  border: none;
  color: #dc2626;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background-color 0.1s;
}

.btn-icon-danger:hover {
  background: #fef2f2;
}

.btn-icon-small {
  font-size: 11px;
  padding: 1px 5px;
}

/* Form grid */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}

@media (max-width: 600px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-field--full {
  grid-column: 1 / -1;
}

.form-field label,
.list-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.form-field input,
.form-field textarea,
.full-width {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
  font-family: inherit;
  color: #111827;
  background: #ffffff;
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.form-field input:focus,
.form-field textarea:focus,
.full-width:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

/* Draggable sections */
.draggable-section {
  cursor: grab;
}

.draggable-section:active {
  cursor: grabbing;
}

/* Entry cards */
.entry-card {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 16px;
  margin-bottom: 12px;
}

.entry-card:last-of-type {
  margin-bottom: 0;
}

.entry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.entry-label {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

/* List editors */
.list-editor {
  margin-top: 12px;
}

.list-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 6px;
}

.list-item--inline {
  align-items: center;
}

.list-input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
  font-family: inherit;
  color: #111827;
  background: #ffffff;
  resize: vertical;
  box-sizing: border-box;
}

.list-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

/* Tag editors */
.tag-editor {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.tag-item {
  display: flex;
  align-items: center;
  gap: 2px;
  background: #f3f4f6;
  border-radius: 4px;
  padding: 2px 4px 2px 6px;
}

.tag-input {
  width: 100px;
  background: transparent;
  border: none;
  font-size: 13px;
  color: #374151;
  padding: 2px 0;
}

.tag-input:focus {
  outline: none;
}
</style>
