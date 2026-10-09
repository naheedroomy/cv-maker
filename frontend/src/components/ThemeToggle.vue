<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'

const theme = ref<'light' | 'dark'>('light')

onMounted(() => {
  theme.value = localStorage.getItem('theme') === 'dark' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', theme.value)
})

watch(theme, (newTheme) => {
  localStorage.setItem('theme', newTheme)
  document.documentElement.setAttribute('data-theme', newTheme)
})

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
}
</script>

<template>
  <button
    type="button"
    class="theme-toggle"
    :class="{ 'theme-toggle--dark': theme === 'dark' }"
    role="switch"
    aria-label="Dark mode"
    :aria-checked="theme === 'dark'"
    :title="`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`"
    @click="toggleTheme"
  >
    <span class="theme-thumb" aria-hidden="true"></span>
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5" />
    </svg>
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8Z" />
    </svg>
  </button>
</template>

<style scoped>
.theme-toggle {
  position: fixed;
  top: 16px;
  right: 18px;
  z-index: 1000;
  width: 84px;
  height: 44px;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: space-around;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background: var(--color-surface-2);
  color: var(--color-text-secondary);
  box-shadow: var(--shadow-sm);
}
.theme-thumb {
  position: absolute;
  left: 4px;
  top: 4px;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--color-surface-1);
  box-shadow: var(--shadow-sm);
  transition: transform 180ms ease;
}
.theme-toggle--dark .theme-thumb { transform: translateX(40px); }
.theme-toggle svg { position: relative; pointer-events: none; }
.theme-toggle:not(.theme-toggle--dark) svg:first-of-type,
.theme-toggle--dark svg:last-of-type { color: var(--color-accent-primary); }
.theme-toggle:hover { border-color: var(--color-accent-primary); }
</style>
