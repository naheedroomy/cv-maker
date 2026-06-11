<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()
const route = useRoute()
const sidebarOpen = ref(false)

watch(() => route.fullPath, () => {
  sidebarOpen.value = false
})
</script>

<template>
  <div v-if="!authStore.isAuthenticated" class="signin-layout">
    <RouterView />
  </div>
  <div v-else class="app-shell">
    <div
      class="sidebar-overlay"
      :class="{ 'sidebar-overlay--visible': sidebarOpen }"
      @click="sidebarOpen = false"
    />
    <AppSidebar
      :class="{ 'sidebar--open': sidebarOpen }"
      @close="sidebarOpen = false"
    />
    <main class="main-content">
      <button class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen" aria-label="Toggle sidebar">
        <svg v-if="!sidebarOpen" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
        </svg>
        <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="6" y1="6" x2="18" y2="18" /><line x1="6" y1="18" x2="18" y2="6" />
        </svg>
      </button>
      <ThemeToggle />
      <RouterView />
    </main>
  </div>
</template>

<style>
:root {
  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

  /* Default Theme: Dark */
  --color-background: #111827; /* Slate 900 */
  --color-surface-1: #1f2937; /* Slate 800 */
  --color-surface-2: #374151; /* Slate 700 */
  --color-surface-3: #4b5563; /* Slate 600 */
  --color-border: #374151; /* Slate 700 */

  --color-text-primary: #f9fafb; /* Slate 50 */
  --color-text-secondary: #d1d5db; /* Slate 300 */
  --color-text-tertiary: #9ca3af; /* Slate 400 */
  --color-text-inverted: #111827;

  --color-accent-primary: #3b82f6; /* Blue 500 */
  --color-accent-primary-rgb: 59, 130, 246;
  --color-accent-primary-hover: #60a5fa; /* Blue 400 */
  --color-accent-secondary: #1e293b; /* Slate 800 */

  --color-success-primary: #22c55e; /* Green 500 */
  --color-success-secondary: #14532d; /* Green 900 */
  --color-warning-bg: #451a03;
  --color-warning-text: #fbbf24;
  --color-error: #f87171;
  --color-error-bg: #450a0a;
  --color-error-text: #fecaca;
  --color-error-border: #991b1b;
  --color-shadow: rgba(0, 0, 0, 0.35);
  
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}

[data-theme='light'] {
  --color-background: #f8f9fa;
  --color-surface-1: #ffffff;
  --color-surface-2: #f3f4f6;
  --color-surface-3: #e5e7eb;
  --color-border: #e2e8f0;

  --color-text-primary: #111827;
  --color-text-secondary: #374151;
  --color-text-tertiary: #6b7280;
  --color-text-inverted: #ffffff;

  --color-accent-primary: #2563eb;
  --color-accent-primary-rgb: 37, 99, 235;
  --color-accent-primary-hover: #1d4ed8;
  --color-accent-secondary: #eff6ff;

  --color-success-primary: #16a34a;
  --color-success-secondary: #f0fdf4;
  --color-warning-bg: #fffbeb;
  --color-warning-text: #92400e;
  --color-error: #dc2626;
  --color-error-bg: #fef2f2;
  --color-error-text: #991b1b;
  --color-error-border: #fecaca;
  --color-shadow: rgba(0, 0, 0, 0.08);
}

html {
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--color-text-primary);
  background: var(--color-background);
  margin: 0;
  padding: 0;
  transition: background-color 200ms ease, color 200ms ease;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.app-shell {
  display: grid;
  grid-template-columns: 260px 1fr;
  min-height: 100vh;
  background-color: var(--color-background);
}

.main-content {
  max-width: 800px;
  width: 100%;
  padding: 32px 24px;
  margin: 0 auto;
  overflow-y: auto;
}

.sidebar-toggle {
  display: none;
}

.sidebar-overlay {
  display: none;
}

.signin-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-background);
}

@media (max-width: 768px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 99;
    opacity: 0;
    pointer-events: none;
    transition: opacity 200ms ease;
  }

  .sidebar-overlay--visible {
    opacity: 1;
    pointer-events: auto;
  }

  .sidebar-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    top: 12px;
    left: 12px;
    z-index: 98;
    width: 40px;
    height: 40px;
    background: var(--color-surface-1);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    cursor: pointer;
    color: var(--color-text-secondary);
    box-shadow: var(--shadow-md);
  }

  .sidebar-toggle:hover {
    background: var(--color-surface-2);
  }

  .main-content {
    padding: 24px 16px;
    padding-top: 64px;
  }
}
</style>
