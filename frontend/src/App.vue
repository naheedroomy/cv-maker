<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()
const route = useRoute()
const sidebarOpen = ref(false)

watch(() => route.fullPath, () => { sidebarOpen.value = false })

function closeOnEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') sidebarOpen.value = false
}
onMounted(() => {
  document.documentElement.dataset.theme = localStorage.getItem('theme') === 'dark' ? 'dark' : 'light'
  document.addEventListener('keydown', closeOnEscape)
})
onUnmounted(() => document.removeEventListener('keydown', closeOnEscape))
</script>

<template>
  <a class="skip-link" href="#main-content">Skip to content</a>
  <div v-if="!authStore.isAuthenticated" id="main-content" class="signin-layout">
    <RouterView />
  </div>
  <div v-else class="app-shell">
    <div
      class="sidebar-overlay"
      :class="{ 'sidebar-overlay--visible': sidebarOpen }"
      aria-hidden="true"
      @click="sidebarOpen = false"
    />
    <AppSidebar
      :class="{ 'sidebar--open': sidebarOpen }"
      @close="sidebarOpen = false"
    />
    <main id="main-content" class="main-content">
      <button
        class="sidebar-toggle"
        type="button"
        :aria-expanded="sidebarOpen"
        aria-controls="app-sidebar"
        :aria-label="sidebarOpen ? 'Close navigation' : 'Open navigation'"
        @click="sidebarOpen = !sidebarOpen"
      >
        <svg v-if="!sidebarOpen" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
        </svg>
        <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <line x1="6" y1="6" x2="18" y2="18" /><line x1="6" y1="18" x2="18" y2="6" />
        </svg>
      </button>
      <ThemeToggle />
      <RouterView />
    </main>
  </div>
</template>

<style>
@font-face {
  font-family: Archivo;
  src: url('./assets/fonts/archivo-latin.woff2') format('woff2');
  font-weight: 400 800;
  font-display: swap;
}
@font-face {
  font-family: Archivo;
  src: url('./assets/fonts/archivo-latin-ext.woff2') format('woff2');
  font-weight: 400 800;
  font-display: swap;
  unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF;
}
:root {
  color-scheme: light;
  --font-sans: Archivo, 'Arial', sans-serif;
  --color-background: #f8f9fa;
  --color-surface-1: #ffffff;
  --color-surface-2: #f3f4f6;
  --color-surface-3: #e5e7eb;
  --color-border: #e2e8f0;
  --color-text-primary: #111827;
  --color-text-secondary: #374151;
  --color-text-tertiary: #6b7280;
  --color-text-inverted: #fff;
  --color-accent-primary: #2563eb;
  --color-accent-primary-rgb: 37, 99, 235;
  --color-accent-primary-hover: #1d4ed8;
  --color-accent-secondary: #eff6ff;
  --color-highlight: #dbeafe;
  --color-highlight-hover: #bfdbfe;
  --color-highlight-text: #1e3a8a;
  --color-success-primary: #176b49;
  --color-success-secondary: #e2f4e8;
  --color-warning-bg: #fff2d5;
  --color-warning-text: #714415;
  --color-error: #ae342d;
  --color-error-bg: #fff0ec;
  --color-error-text: #962820;
  --color-error-border: #da8177;
  --color-shadow: rgba(0, 0, 0, 0.08);
  --shadow-sm: 0 1px 2px var(--color-shadow);
  --shadow-md: 0 10px 28px var(--color-shadow);
}
[data-theme='dark'] {
  color-scheme: dark;
  --color-background: #111827;
  --color-surface-1: #1f2937;
  --color-surface-2: #374151;
  --color-surface-3: #4b5563;
  --color-border: #374151;
  --color-text-primary: #f9fafb;
  --color-text-secondary: #d1d5db;
  --color-text-tertiary: #9ca3af;
  --color-text-inverted: #111827;
  --color-accent-primary: #93c5fd;
  --color-accent-primary-rgb: 147, 197, 253;
  --color-accent-primary-hover: #bfdbfe;
  --color-accent-secondary: #1e293b;
  --color-highlight: #334155;
  --color-highlight-hover: #475569;
  --color-highlight-text: #f1f5f9;
  --color-success-primary: #a7e3b0;
  --color-success-secondary: #244c38;
  --color-warning-bg: #4b371e;
  --color-warning-text: #ffe2a9;
  --color-error: #ffa69b;
  --color-error-bg: #512c2c;
  --color-error-text: #ffe0dc;
  --color-error-border: #af706b;
  --color-shadow: rgba(0, 0, 0, 0.25);
}
html { font-family: var(--font-sans); font-size: 15px; color: var(--color-text-primary); background: var(--color-background); }
* { box-sizing: border-box; }
body, h1, h2, h3, p { margin: 0; }
button, input, textarea, select { font: inherit; }
button { cursor: pointer; }
button:disabled { cursor: not-allowed; }
a { color: var(--color-accent-primary); }
:focus-visible { outline: 3px solid var(--color-accent-primary); outline-offset: 3px; }
::selection { background: var(--color-highlight); color: var(--color-highlight-text); }
.skip-link { position: absolute; left: 12px; top: -80px; z-index: 1200; padding: 12px 18px; background: var(--color-highlight); color: var(--color-highlight-text); }
.skip-link:focus { top: 12px; }
.app-shell { display: grid; grid-template-columns: 248px minmax(0, 1fr); min-height: 100vh; background: var(--color-background); }
.main-content { min-width: 0; width: min(100%, 1500px); padding: clamp(28px, 4vw, 68px) clamp(20px, 4vw, 72px) 96px; margin-inline: auto; }
.sidebar-toggle, .sidebar-overlay { display: none; }
.signin-layout { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--color-background); }
@media (max-width: 900px) {
  .app-shell { grid-template-columns: minmax(0, 1fr); }
  .sidebar-overlay { display: block; position: fixed; inset: 0; z-index: 99; background: #102620a6; opacity: 0; pointer-events: none; transition: opacity .2s ease; }
  .sidebar-overlay--visible { opacity: 1; pointer-events: auto; }
  .sidebar-toggle { display: flex; align-items: center; justify-content: center; position: absolute; top: 17px; left: 18px; z-index: 101; width: 44px; height: 44px; background: var(--color-surface-1); color: var(--color-text-primary); border: 1px solid var(--color-border); border-radius: 6px; }
  .main-content { padding: 88px 20px 80px; }
}
@media (max-width: 600px) { .main-content { padding-inline: 18px; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto !important; animation-duration: .01ms !important; transition-duration: .01ms !important; } }
</style>
