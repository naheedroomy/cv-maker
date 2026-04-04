<script setup lang="ts">
import type { TailoredCV } from '@/types'
defineProps<{ cv: TailoredCV }>()
</script>

<template>
  <div class="cv-preview">
    <!-- Summary -->
    <section v-if="cv.summary" class="cv-section">
      <h3 class="section-heading">Summary</h3>
      <p class="body-text">{{ cv.summary }}</p>
    </section>

    <!-- Experience -->
    <section v-if="cv.experience && cv.experience.length > 0" class="cv-section">
      <h3 class="section-heading">Experience</h3>
      <div v-for="(item, i) in cv.experience" :key="i" class="experience-item">
        <div class="experience-header">
          <span class="company-name">{{ item.company }}</span>
          <span class="experience-meta">
            {{ item.title }}
            <template v-if="item.location"> &middot; {{ item.location }}</template>
            <template v-if="item.start_date">
              &middot; {{ item.start_date }} &ndash; {{ item.end_date || 'Present' }}
            </template>
          </span>
        </div>
        <ul v-if="item.bullets && item.bullets.length > 0" class="bullet-list">
          <li v-for="(bullet, j) in item.bullets" :key="j">{{ bullet }}</li>
        </ul>
      </div>
    </section>

    <!-- Skills -->
    <section v-if="cv.skills && cv.skills.length > 0" class="cv-section">
      <h3 class="section-heading">Skills</h3>
      <p class="body-text">{{ cv.skills.join(', ') }}</p>
    </section>

    <!-- Education -->
    <section v-if="cv.education && cv.education.length > 0" class="cv-section">
      <h3 class="section-heading">Education</h3>
      <div v-for="(item, i) in cv.education" :key="i" class="education-item">
        <div class="education-header">
          <span class="institution-name">{{ item.institution }}</span>
          <span class="education-meta">
            {{ item.degree }}
            <template v-if="item.graduation_date"> &middot; {{ item.graduation_date }}</template>
          </span>
        </div>
        <ul v-if="item.details && item.details.length > 0" class="bullet-list">
          <li v-for="(detail, j) in item.details" :key="j">{{ detail }}</li>
        </ul>
      </div>
    </section>

    <!-- Projects (optional) -->
    <section v-if="cv.projects && cv.projects.length > 0" class="cv-section">
      <h3 class="section-heading">Projects</h3>
      <div v-for="(project, i) in cv.projects" :key="i" class="project-item">
        <div class="project-header">
          <span class="project-name">{{ project.name }}</span>
          <a
            v-if="project.url"
            :href="project.url"
            target="_blank"
            rel="noopener noreferrer"
            class="project-url"
          >{{ project.url }}</a>
        </div>
        <p v-if="project.description" class="body-text">{{ project.description }}</p>
        <p v-if="project.technologies && project.technologies.length > 0" class="project-tech">
          {{ project.technologies.join(', ') }}
        </p>
      </div>
    </section>

    <!-- Certifications (optional) -->
    <section v-if="cv.certifications && cv.certifications.length > 0" class="cv-section">
      <h3 class="section-heading">Certifications</h3>
      <ul class="bullet-list">
        <li v-for="(cert, i) in cv.certifications" :key="i">{{ cert }}</li>
      </ul>
    </section>

    <!-- Highlighted Technologies (optional) -->
    <section v-if="cv.highlighted_technologies && cv.highlighted_technologies.length > 0" class="cv-section">
      <h3 class="section-heading">Technologies</h3>
      <p class="body-text">{{ cv.highlighted_technologies.join(', ') }}</p>
    </section>
  </div>
</template>

<style scoped>
.cv-preview {
  display: flex;
  flex-direction: column;
  gap: 48px;
}

.cv-section {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 24px;
}

.section-heading {
  font-size: 20px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 16px;
}

.body-text {
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  color: #111827;
}

/* Experience */
.experience-item {
  margin-bottom: 24px;
}
.experience-item:last-child {
  margin-bottom: 0;
}
.experience-header {
  display: flex;
  flex-direction: column;
  margin-bottom: 8px;
}
.company-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}
.experience-meta {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

/* Education */
.education-item {
  margin-bottom: 16px;
}
.education-item:last-child {
  margin-bottom: 0;
}
.education-header {
  display: flex;
  flex-direction: column;
  margin-bottom: 8px;
}
.institution-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}
.education-meta {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

/* Projects */
.project-item {
  margin-bottom: 16px;
}
.project-item:last-child {
  margin-bottom: 0;
}
.project-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}
.project-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}
.project-url {
  font-size: 12px;
  color: #2563eb;
}
.project-tech {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

/* Bullets */
.bullet-list {
  padding-left: 20px;
  margin-top: 8px;
}
.bullet-list li {
  font-size: 14px;
  line-height: 1.5;
  color: #111827;
  margin-bottom: 4px;
}
.bullet-list li:last-child {
  margin-bottom: 0;
}
</style>
