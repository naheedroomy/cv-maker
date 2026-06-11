<script setup lang="ts">
defineProps<{
  title: string
  collapsed?: boolean
  draggableHint?: boolean
}>()

defineEmits<{
  toggle: []
}>()
</script>

<template>
  <div class="editor-section">
    <button
      type="button"
      class="section-header"
      @click="$emit('toggle')"
      :aria-expanded="!collapsed"
    >
      <span class="section-title">
        <span v-if="draggableHint" class="drag-handle" title="Drag to reorder">&#x2630;</span>
        {{ title }}
      </span>
      <svg
        class="chevron"
        :class="{ 'chevron--collapsed': collapsed }"
        viewBox="0 0 20 20"
        fill="currentColor"
        width="16"
        height="16"
      >
        <path
          fill-rule="evenodd"
          d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
          clip-rule="evenodd"
        />
      </svg>
    </button>
    <div v-show="!collapsed" class="section-body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.editor-section {
  background: var(--color-surface-1);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 14px 16px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background-color 0.1s;
}

.section-header:hover {
  background-color: var(--color-surface-2);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.drag-handle {
  color: var(--color-text-tertiary);
  font-size: 14px;
  cursor: grab;
}

.chevron {
  color: var(--color-text-secondary);
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.chevron--collapsed {
  transform: rotate(-90deg);
}

.section-body {
  padding: 16px;
  border-top: 1px solid var(--color-border);
}
</style>
