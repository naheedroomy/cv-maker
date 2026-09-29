<script setup lang="ts">
import { reactive, ref, computed, watch } from 'vue'
import CvEditorSection from '@/components/CvEditorSection.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import type { BaseCV, TailoredCV, ExperienceItem, EducationItem, ProjectItem, LanguageItem } from '@/types'

const props = withDefaults(
  defineProps<{
    modelValue: BaseCV | TailoredCV
    title?: string
    saveLabel?: string
    saving?: boolean
    showCancel?: boolean
    showDownload?: boolean
    downloading?: boolean
  }>(),
  {
    title: 'CV Editor',
    saveLabel: 'Save CV',
    saving: false,
    showCancel: false,
    showDownload: false,
    downloading: false,
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: BaseCV | TailoredCV): void
  (e: 'save'): void
  (e: 'cancel'): void
  (e: 'download'): void
}>()

// Directive for auto-growing textareas without internal scrollbars
const vAutoGrow = {
  mounted(el: HTMLElement) {
    const textarea = el instanceof HTMLTextAreaElement ? el : el.querySelector('textarea')
    if (!textarea) return
    textarea.style.boxSizing = 'border-box'
    const adjust = () => {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.max(textarea.scrollHeight, 44)}px`
    }
    textarea.addEventListener('input', adjust)
    requestAnimationFrame(adjust)
  },
  updated(el: HTMLElement) {
    const textarea = el instanceof HTMLTextAreaElement ? el : el.querySelector('textarea')
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.max(textarea.scrollHeight, 44)}px`
  },
}

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
  'summary',
  'experience',
  'skills',
  'education',
  'certifications',
  'projects',
  'languages',
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

// ── Item Helpers ─────────────────────────────────────────────────────────────

function moveItemUp<T>(arr: T[], index: number) {
  if (index <= 0) return
  const item = arr[index]
  if (item === undefined) return
  arr.splice(index, 1)
  arr.splice(index - 1, 0, item)
}

function moveItemDown<T>(arr: T[], index: number) {
  if (index >= arr.length - 1) return
  const item = arr[index]
  if (item === undefined) return
  arr.splice(index, 1)
  arr.splice(index + 1, 0, item)
}

// ── Experience ───────────────────────────────────────────────────────────────

function addExperience() {
  if (!props.modelValue.experience) props.modelValue.experience = []
  props.modelValue.experience.push({
    company: '',
    title: '',
    location: '',
    start: '',
    end: null,
    bullets: [''],
    technologies: [],
  } as ExperienceItem)
}

function removeExperience(index: number) {
  props.modelValue.experience.splice(index, 1)
}

function addBullet(expIndex: number) {
  const exp = props.modelValue.experience[expIndex]
  if (!exp) return
  if (!exp.bullets) exp.bullets = []
  exp.bullets.push('')
}

function removeBullet(expIndex: number, bulletIndex: number) {
  const exp = props.modelValue.experience[expIndex]
  if (!exp) return
  exp.bullets.splice(bulletIndex, 1)
}

function addTechnology(expIndex: number) {
  const exp = props.modelValue.experience[expIndex]
  if (!exp) return
  if (!exp.technologies) exp.technologies = []
  exp.technologies.push('')
}

function removeTechnology(expIndex: number, techIndex: number) {
  const exp = props.modelValue.experience[expIndex]
  if (!exp) return
  exp.technologies.splice(techIndex, 1)
}

// ── Education ────────────────────────────────────────────────────────────────

function addEducation() {
  if (!props.modelValue.education) props.modelValue.education = []
  props.modelValue.education.push({
    institution: '',
    degree: '',
    field: null,
    year: null,
  } as EducationItem)
}

function removeEducation(index: number) {
  props.modelValue.education.splice(index, 1)
}

// ── Skills ───────────────────────────────────────────────────────────────────

interface SkillCategoryGroup {
  category: string
  skills: string[]
}

function parseSkillsToGroups(rawSkills?: string[]): SkillCategoryGroup[] {
  if (!rawSkills || rawSkills.length === 0) {
    return [{ category: '', skills: [] }]
  }
  const groups: SkillCategoryGroup[] = []
  let currentFlatGroup: SkillCategoryGroup | null = null

  for (const item of rawSkills) {
    if (item.includes(':')) {
      if (currentFlatGroup && currentFlatGroup.skills.length > 0) {
        groups.push(currentFlatGroup)
        currentFlatGroup = null
      }
      const parts = item.split(':')
      const cat = parts[0] ?? ''
      const itemsStr = parts.slice(1).join(':')
      const skillList = itemsStr
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
      groups.push({
        category: cat.trim(),
        skills: skillList.length > 0 ? skillList : [''],
      })
    } else {
      if (!currentFlatGroup) {
        currentFlatGroup = { category: '', skills: [] }
      }
      if (item.trim()) {
        currentFlatGroup.skills.push(item.trim())
      }
    }
  }

  if (currentFlatGroup && currentFlatGroup.skills.length > 0) {
    groups.push(currentFlatGroup)
  }

  return groups.length > 0 ? groups : [{ category: '', skills: [] }]
}

function serializeGroups(groups: SkillCategoryGroup[]): string[] {
  const result: string[] = []
  for (const group of groups) {
    const validSkills = group.skills.map((s) => s.trim()).filter(Boolean)
    if (group.category.trim()) {
      if (validSkills.length > 0) {
        result.push(`${group.category.trim()}: ${validSkills.join(', ')}`)
      }
    } else {
      result.push(...validSkills)
    }
  }
  return result
}

const categoryGroups = ref<SkillCategoryGroup[]>(parseSkillsToGroups(props.modelValue.skills))
let isInternalSync = false

function syncGroupsToModel() {
  isInternalSync = true
  props.modelValue.skills = serializeGroups(categoryGroups.value)
  emit('update:modelValue', props.modelValue)
  setTimeout(() => {
    isInternalSync = false
  }, 0)
}

function handleSaveClick() {
  syncGroupsToModel()
  emit('update:modelValue', props.modelValue)
  emit('save')
}

const totalSkillsCount = computed(() => {
  return categoryGroups.value.reduce(
    (acc, g) => acc + g.skills.filter((s) => s.trim()).length,
    0
  )
})

function addSkillCategory() {
  if (categoryGroups.value.length >= 10) return
  categoryGroups.value.push({ category: '', skills: [''] })
  syncGroupsToModel()
}

function removeSkillCategory(index: number) {
  categoryGroups.value.splice(index, 1)
  syncGroupsToModel()
}

function addSkillToCategory(catIndex: number) {
  if (totalSkillsCount.value >= 25) return
  const group = categoryGroups.value[catIndex]
  if (!group) return
  group.skills.push('')
  syncGroupsToModel()
}

function removeSkillFromCategory(catIndex: number, skillIndex: number) {
  const group = categoryGroups.value[catIndex]
  if (!group) return
  group.skills.splice(skillIndex, 1)
  syncGroupsToModel()
}

watch(
  () => props.modelValue.skills,
  (newSkills) => {
    if (isInternalSync) return
    const current = (newSkills || []).join('||')
    const internal = serializeGroups(categoryGroups.value).join('||')
    if (current !== internal) {
      categoryGroups.value = parseSkillsToGroups(newSkills)
    }
  },
  { deep: true }
)

// ── Certifications ───────────────────────────────────────────────────────────

function addCertification() {
  if (!props.modelValue.certifications) props.modelValue.certifications = []
  props.modelValue.certifications.push('')
}

function removeCertification(index: number) {
  props.modelValue.certifications.splice(index, 1)
}

// ── Projects ─────────────────────────────────────────────────────────────────

function addProject() {
  if (!props.modelValue.projects) props.modelValue.projects = []
  props.modelValue.projects.push({
    name: '',
    description: '',
    technologies: [],
    url: '',
  } as ProjectItem)
}

function removeProject(index: number) {
  props.modelValue.projects.splice(index, 1)
}

function addProjectTech(projectIndex: number) {
  const proj = props.modelValue.projects[projectIndex]
  if (!proj) return
  if (!proj.technologies) proj.technologies = []
  proj.technologies.push('')
}

function removeProjectTech(projectIndex: number, techIndex: number) {
  const proj = props.modelValue.projects[projectIndex]
  if (!proj) return
  proj.technologies.splice(techIndex, 1)
}

// ── Languages ────────────────────────────────────────────────────────────────

function addLanguage() {
  if (!props.modelValue.languages) props.modelValue.languages = []
  props.modelValue.languages.push({ language: '', level: '' } as LanguageItem)
}

function removeLanguage(index: number) {
  props.modelValue.languages?.splice(index, 1)
}
</script>

<template>
  <div class="cv-form-editor">
    <!-- Header -->
    <div class="editor-header">
      <h2 class="editor-title">{{ title }}</h2>
      <div class="header-actions">
        <button
          v-if="showCancel"
          type="button"
          class="btn-secondary"
          :disabled="saving"
          @click="$emit('cancel')"
        >
          Cancel
        </button>
        <button
          v-if="showDownload"
          type="button"
          class="btn-secondary"
          :disabled="downloading || saving"
          @click="$emit('download')"
        >
          <LoadingSpinner v-if="downloading" class="btn-spinner" />
          {{ downloading ? 'Downloading...' : 'Download PDF' }}
        </button>
        <button
          type="button"
          class="btn-primary"
          :disabled="saving"
          @click="handleSaveClick"
        >
          <LoadingSpinner v-if="saving" class="btn-spinner" />
          {{ saving ? 'Saving & Compiling...' : saveLabel }}
        </button>
      </div>
    </div>

    <!-- Contact Info (Always at the top) -->
    <CvEditorSection
      title="Contact Information"
      :collapsed="collapsed.contact"
      @toggle="collapsed.contact = !collapsed.contact"
    >
      <div class="form-grid">
        <div class="form-field">
          <label>Name</label>
          <input v-model="modelValue.contact.name" type="text" placeholder="Full Name" />
        </div>
        <div class="form-field">
          <label>Email</label>
          <input v-model="modelValue.contact.email" type="email" placeholder="you@example.com" />
        </div>
        <div class="form-field">
          <label>Phone</label>
          <input v-model="modelValue.contact.phone" type="text" placeholder="+1 555 000 0000" />
        </div>
        <div class="form-field">
          <label>Location</label>
          <input v-model="modelValue.contact.location" type="text" placeholder="City, Country" />
        </div>
        <div class="form-field">
          <label>LinkedIn</label>
          <input v-model="modelValue.contact.linkedin" type="url" placeholder="https://linkedin.com/in/you" />
        </div>
        <div class="form-field">
          <label>GitHub</label>
          <input v-model="modelValue.contact.github" type="url" placeholder="https://github.com/you" />
        </div>
        <div class="form-field form-field--full">
          <label>Work Authorization</label>
          <input
            v-model="modelValue.contact.work_authorization"
            type="text"
            placeholder="e.g. Valid work permit, German citizen, US Green Card..."
          />
        </div>
      </div>
    </CvEditorSection>

    <!-- Draggable Sections -->
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
      <CvEditorSection
        v-if="section === 'summary'"
        title="Summary"
        :collapsed="collapsed.summary"
        @toggle="collapsed.summary = !collapsed.summary"
        draggable-hint
      >
        <textarea
          v-model="modelValue.summary"
          v-auto-grow
          class="full-width auto-expand"
          placeholder="Brief professional summary..."
        />
      </CvEditorSection>

      <!-- Work Experience -->
      <CvEditorSection
        v-else-if="section === 'experience'"
        title="Work Experience"
        :collapsed="collapsed.experience"
        @toggle="collapsed.experience = !collapsed.experience"
        draggable-hint
      >
        <div v-for="(exp, i) in modelValue.experience" :key="i" class="entry-card">
          <div class="entry-header">
            <span class="entry-label">{{ exp.company || exp.title || 'Position' }}</span>
            <div class="entry-actions">
              <button
                type="button"
                class="btn-icon"
                :disabled="i === 0"
                title="Move Up"
                @click="moveItemUp(modelValue.experience, i)"
              >
                ↑
              </button>
              <button
                type="button"
                class="btn-icon"
                :disabled="i === modelValue.experience.length - 1"
                title="Move Down"
                @click="moveItemDown(modelValue.experience, i)"
              >
                ↓
              </button>
              <button
                type="button"
                class="btn-icon-danger"
                @click="removeExperience(i)"
              >
                Remove
              </button>
            </div>
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label>Company</label>
              <input v-model="exp.company" type="text" placeholder="Company Name" />
            </div>
            <div class="form-field">
              <label>Title</label>
              <input v-model="exp.title" type="text" placeholder="Job Title" />
            </div>
            <div class="form-field">
              <label>Location</label>
              <input v-model="exp.location" type="text" placeholder="Remote / City" />
            </div>
            <div class="form-field">
              <label>Start</label>
              <input v-model="exp.start" type="text" placeholder="YYYY-MM" />
            </div>
            <div class="form-field">
              <label>End</label>
              <input
                :value="exp.end ?? ''"
                type="text"
                placeholder="YYYY-MM or blank for Present"
                @input="exp.end = ($event.target as HTMLInputElement).value || null"
              />
            </div>
          </div>

          <!-- Bullets with Auto-Expand -->
          <div class="list-editor">
            <div class="list-editor-header">
              <label class="list-label">Achievement Bullets</label>
              <span class="list-hint">Expands automatically to fit text</span>
            </div>
            <div v-for="(_, bi) in exp.bullets" :key="bi" class="list-item">
              <span class="bullet-dot" aria-hidden="true">•</span>
              <textarea
                v-model="exp.bullets[bi]"
                v-auto-grow
                class="list-input auto-expand"
                placeholder="Describe your measurable impact or key accomplishment..."
              />
              <button
                type="button"
                class="btn-icon-danger btn-icon-small"
                title="Remove bullet"
                @click="removeBullet(i, bi)"
              >
                ✕
              </button>
            </div>
            <button type="button" class="btn-text" @click="addBullet(i)">
              + Add bullet point
            </button>
          </div>

          <!-- Technologies -->
          <div class="list-editor">
            <label class="list-label">Technologies Used in This Role</label>
            <div class="tag-editor">
              <div v-for="(_, ti) in exp.technologies" :key="ti" class="tag-item">
                <input v-model="exp.technologies[ti]" class="tag-input" placeholder="Tech" />
                <button
                  type="button"
                  class="btn-icon-danger btn-icon-small"
                  title="Remove tag"
                  @click="removeTechnology(i, ti)"
                >
                  ✕
                </button>
              </div>
              <button type="button" class="btn-text" @click="addTechnology(i)">
                + Add tech
              </button>
            </div>
          </div>
        </div>

        <button type="button" class="btn-secondary add-entry-btn" @click="addExperience">
          + Add Work Experience Position
        </button>
      </CvEditorSection>

      <!-- Skills -->
      <CvEditorSection
        v-else-if="section === 'skills'"
        :title="`Skills & Technologies (${totalSkillsCount} skills${totalSkillsCount > 15 ? ' · recommended ≤ 15' : ''})`"
        :collapsed="collapsed.skills"
        @toggle="collapsed.skills = !collapsed.skills"
        draggable-hint
      >
        <div class="skills-category-list">
          <div
            v-for="(group, ci) in categoryGroups"
            :key="ci"
            class="skill-category-block"
          >
            <div class="skill-category-header">
              <input
                v-model="group.category"
                class="category-name-input"
                placeholder="Category Name (e.g. Platforms & Cloud, DevOps & IaC)"
                @input="syncGroupsToModel"
              />
              <button
                type="button"
                class="btn-icon-danger btn-icon-small"
                title="Remove category"
                @click="removeSkillCategory(ci)"
              >
                ✕
              </button>
            </div>
            <div class="tag-editor">
              <div v-for="(_, si) in group.skills" :key="si" class="tag-item">
                <input
                  v-model="group.skills[si]"
                  class="tag-input"
                  placeholder="Skill name"
                  @input="syncGroupsToModel"
                />
                <button
                  type="button"
                  class="btn-icon-danger btn-icon-small"
                  title="Remove skill"
                  @click="removeSkillFromCategory(ci, si)"
                >
                  ✕
                </button>
              </div>
              <button
                type="button"
                class="btn-text"
                :disabled="totalSkillsCount >= 25"
                @click="addSkillToCategory(ci)"
              >
                + Add skill
              </button>
            </div>
          </div>
          <div class="skills-footer">
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="addSkillCategory"
            >
              + Add Category
            </button>
            <span class="skills-hint">
              Curate into 3–4 clean categories. Recommended max 15 skills across categories to keep high signal and avoid keyword stuffing.
            </span>
          </div>
        </div>
      </CvEditorSection>

      <!-- Education -->
      <CvEditorSection
        v-else-if="section === 'education'"
        title="Education"
        :collapsed="collapsed.education"
        @toggle="collapsed.education = !collapsed.education"
        draggable-hint
      >
        <div v-for="(edu, i) in modelValue.education" :key="i" class="entry-card">
          <div class="entry-header">
            <span class="entry-label">{{ edu.institution || 'New Institution' }}</span>
            <div class="entry-actions">
              <button
                type="button"
                class="btn-icon"
                :disabled="i === 0"
                title="Move Up"
                @click="moveItemUp(modelValue.education, i)"
              >
                ↑
              </button>
              <button
                type="button"
                class="btn-icon"
                :disabled="i === modelValue.education.length - 1"
                title="Move Down"
                @click="moveItemDown(modelValue.education, i)"
              >
                ↓
              </button>
              <button
                type="button"
                class="btn-icon-danger"
                @click="removeEducation(i)"
              >
                Remove
              </button>
            </div>
          </div>
          <div class="form-grid">
            <div class="form-field">
              <label>Institution</label>
              <input v-model="edu.institution" type="text" placeholder="University of..." />
            </div>
            <div class="form-field">
              <label>Degree</label>
              <input v-model="edu.degree" type="text" placeholder="Bachelor of Science" />
            </div>
            <div class="form-field">
              <label>Field of Study</label>
              <input
                :value="edu.field ?? ''"
                type="text"
                placeholder="Computer Science"
                @input="edu.field = ($event.target as HTMLInputElement).value || null"
              />
            </div>
            <div class="form-field">
              <label>Year</label>
              <input
                :value="edu.year ?? ''"
                type="number"
                placeholder="2022"
                @input="edu.year = Number(($event.target as HTMLInputElement).value) || null"
              />
            </div>
          </div>
        </div>
        <button type="button" class="btn-secondary add-entry-btn" @click="addEducation">
          + Add Education
        </button>
      </CvEditorSection>

      <!-- Certifications -->
      <CvEditorSection
        v-else-if="section === 'certifications'"
        title="Certifications"
        :collapsed="collapsed.certifications"
        @toggle="collapsed.certifications = !collapsed.certifications"
        draggable-hint
      >
        <div class="list-editor">
          <div v-for="(_, i) in modelValue.certifications" :key="i" class="list-item list-item--inline">
            <input
              v-model="modelValue.certifications[i]"
              type="text"
              class="list-input"
              placeholder="e.g. AWS Certified Solutions Architect"
            />
            <button
              type="button"
              class="btn-icon-danger btn-icon-small"
              title="Remove certification"
              @click="removeCertification(i)"
            >
              ✕
            </button>
          </div>
          <button type="button" class="btn-text" @click="addCertification">
            + Add certification
          </button>
        </div>
      </CvEditorSection>

      <!-- Projects -->
      <CvEditorSection
        v-else-if="section === 'projects'"
        title="Projects"
        :collapsed="collapsed.projects"
        @toggle="collapsed.projects = !collapsed.projects"
        draggable-hint
      >
        <div v-for="(proj, i) in modelValue.projects" :key="i" class="entry-card">
          <div class="entry-header">
            <span class="entry-label">{{ proj.name || 'New Project' }}</span>
            <div class="entry-actions">
              <button
                type="button"
                class="btn-icon"
                :disabled="i === 0"
                title="Move Up"
                @click="moveItemUp(modelValue.projects, i)"
              >
                ↑
              </button>
              <button
                type="button"
                class="btn-icon"
                :disabled="i === modelValue.projects.length - 1"
                title="Move Down"
                @click="moveItemDown(modelValue.projects, i)"
              >
                ↓
              </button>
              <button
                type="button"
                class="btn-icon-danger"
                @click="removeProject(i)"
              >
                Remove
              </button>
            </div>
          </div>
          <div class="form-grid">
            <div class="form-field">
              <label>Project Name</label>
              <input v-model="proj.name" type="text" placeholder="Project Name" />
            </div>
            <div class="form-field">
              <label>URL (optional)</label>
              <input
                :value="proj.url ?? ''"
                type="url"
                placeholder="https://github.com/..."
                @input="proj.url = ($event.target as HTMLInputElement).value || undefined"
              />
            </div>
            <div class="form-field form-field--full">
              <label>Description</label>
              <textarea
                v-model="proj.description"
                v-auto-grow
                class="full-width auto-expand"
                placeholder="What does this project do and what was your role?"
              />
            </div>
          </div>
          <div class="list-editor">
            <label class="list-label">Technologies</label>
            <div class="tag-editor">
              <div v-for="(_, ti) in proj.technologies" :key="ti" class="tag-item">
                <input v-model="proj.technologies[ti]" class="tag-input" placeholder="Tech" />
                <button
                  type="button"
                  class="btn-icon-danger btn-icon-small"
                  title="Remove tag"
                  @click="removeProjectTech(i, ti)"
                >
                  ✕
                </button>
              </div>
              <button type="button" class="btn-text" @click="addProjectTech(i)">
                + Add tech
              </button>
            </div>
          </div>
        </div>
        <button type="button" class="btn-secondary add-entry-btn" @click="addProject">
          + Add Project
        </button>
      </CvEditorSection>

      <!-- Languages -->
      <CvEditorSection
        v-else-if="section === 'languages'"
        title="Languages"
        :collapsed="collapsed.languages"
        @toggle="collapsed.languages = !collapsed.languages"
        draggable-hint
      >
        <div class="form-grid">
          <div
            v-for="(lang, i) in modelValue.languages"
            :key="i"
            class="lang-row"
          >
            <input
              v-model="lang.language"
              type="text"
              class="lang-input"
              placeholder="Language (e.g. English)"
            />
            <input
              v-model="lang.level"
              type="text"
              class="lang-input"
              placeholder="Proficiency (e.g. Native, C1)"
            />
            <button
              type="button"
              class="btn-icon-danger btn-icon-small"
              title="Remove language"
              @click="removeLanguage(i)"
            >
              ✕
            </button>
          </div>
        </div>
        <button type="button" class="btn-text" @click="addLanguage">
          + Add language
        </button>
      </CvEditorSection>
    </div>
  </div>
</template>

<style scoped>
.cv-form-editor {
  width: 100%;
  max-width: 1040px;
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
  gap: 12px;
  margin-bottom: 4px;
}

.editor-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* Buttons */
.btn-primary {
  background: var(--color-accent-primary);
  color: #ffffff;
  border: none;
  border-radius: 6px;
  height: 38px;
  padding: 0 18px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: background-color 0.15s, opacity 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-primary-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--color-surface-1);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  height: 38px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: background-color 0.15s;
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-surface-2);
  color: var(--color-text-primary);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-spinner {
  width: 14px;
  height: 14px;
}

.btn-text {
  background: none;
  border: none;
  color: var(--color-accent-primary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  padding: 6px 0;
  text-decoration: none;
  display: inline-block;
}

.btn-text:hover {
  text-decoration: underline;
}

.btn-icon {
  background: var(--color-surface-1);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 13px;
  padding: 3px 8px;
  border-radius: 4px;
  transition: all 0.15s;
}

.btn-icon:hover:not(:disabled) {
  background: var(--color-surface-2);
  color: var(--color-text-primary);
}

.btn-icon:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.btn-icon-danger {
  background: none;
  border: 1px solid transparent;
  color: var(--color-error);
  cursor: pointer;
  font-size: 12px;
  padding: 3px 8px;
  border-radius: 4px;
  transition: background-color 0.15s;
}

.btn-icon-danger:hover {
  background: var(--color-error-bg);
  border-color: var(--color-error-border);
}

.btn-icon-small {
  font-size: 11px;
  padding: 4px 6px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.add-entry-btn {
  margin-top: 14px;
  width: 100%;
  justify-content: center;
}

/* Form Grid */
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  margin-bottom: 12px;
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-field--full {
  grid-column: 1 / -1;
}

.form-field label,
.list-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.list-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.list-hint {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.form-field input,
.form-field textarea,
.full-width {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary);
  background: var(--color-surface-1);
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.form-field input:focus,
.form-field textarea:focus,
.full-width:focus {
  outline: none;
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 2px rgba(var(--color-accent-primary-rgb), 0.15);
}

/* Draggable Sections */
.draggable-section {
  cursor: grab;
}

.draggable-section:active {
  cursor: grabbing;
}

/* Entry Cards */
.entry-card {
  border: 1px solid var(--color-border);
  background: var(--color-surface-1);
  border-radius: 8px;
  padding: 16px 18px;
  margin-bottom: 14px;
  transition: border-color 0.15s;
}

.entry-card:hover {
  border-color: var(--color-border-hover, var(--color-border));
}

.entry-card:last-of-type {
  margin-bottom: 0;
}

.entry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

.entry-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.entry-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

/* List / Bullet Editor */
.list-editor {
  margin-top: 14px;
}

.list-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
}

.list-item--inline {
  align-items: center;
}

.bullet-dot {
  color: var(--color-text-tertiary);
  font-size: 16px;
  line-height: 38px;
  user-select: none;
}

/* Auto-expanding textareas */
.auto-expand {
  field-sizing: content;
  min-height: 44px;
  line-height: 1.5;
  overflow-y: hidden;
  resize: vertical;
}

.list-input {
  flex: 1;
  padding: 9px 12px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary);
  background: var(--color-surface-1);
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.list-input:focus {
  outline: none;
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 2px rgba(var(--color-accent-primary-rgb), 0.15);
}

/* Tag Editor */
.tag-editor {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 6px;
}

.tag-item {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  padding: 3px 6px 3px 8px;
}

.tag-input {
  min-width: 90px;
  max-width: 160px;
  background: transparent;
  border: none;
  font-size: 13px;
  color: var(--color-text-primary);
  padding: 2px 0;
}

.tag-input:focus {
  outline: none;
}

/* Languages */
.lang-row {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  padding: 6px 10px;
}

.lang-input {
  flex: 1;
  background: transparent;
  border: none;
  font-size: 13px;
  color: var(--color-text-primary);
}

.lang-input:focus {
  outline: none;
}

/* Categorized Skills Editor */
.skills-category-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skill-category-block {
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 10px 12px;
}

.skill-category-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.category-name-input {
  flex: 1;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-primary);
  background: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 5px 8px;
}

.category-name-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.skills-footer {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.skills-hint {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}
</style>
