<script setup lang="ts">
defineProps<{ notes: string[] }>()
</script>

<template>
  <div class="tailoring-notes">
    <h3 class="section-heading">AI Tailoring Notes</h3>
    <p class="notes-intro">Here's what was changed and why:</p>
    <ul class="notes-list">
      <li v-for="(note, i) in notes" :key="i">{{ note }}</li>
    </ul>
  </div>
</template>

<style scoped>
.tailoring-notes {
  background: #fffbeb;
  border: 1px solid #f59e0b;
  border-radius: 6px;
  padding: 24px;
}

.section-heading {
  font-size: 20px;
  font-weight: 600;
  color: #92400e;
  margin-bottom: 8px;
}

.notes-intro {
  font-size: 14px;
  color: #78350f;
  margin-bottom: 16px;
}

.notes-list {
  padding-left: 20px;
}

.notes-list li {
  font-size: 14px;
  line-height: 1.6;
  color: #451a03;
  margin-bottom: 8px;
}

.notes-list li:last-child {
  margin-bottom: 0;
}
</style>
