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
  --color-background: #e8ebe5;
  --color-surface-1: #fcfcf8;
  --color-surface-2: #f0f2eb;
  --color-surface-3: #e3e9df;
  --color-border: #cbd5ca;
  --color-text-primary: #183535;
  --color-text-secondary: #3e5a56;
  --color-text-tertiary: #57716a;
  --color-text-inverted: #fff;
  --color-accent-primary: #183535;
  --color-accent-primary-rgb: 24, 53, 53;
  --color-accent-primary-hover: #29534e;
  --color-accent-secondary: #e5eee9;
  --color-highlight: #d8f050;
  --color-highlight-hover: #c7e43a;
  --color-highlight-text: #183535;
  --color-success-primary: #176b49;
  --color-success-secondary: #e2f4e8;
  --color-warning-bg: #fff2d5;
  --color-warning-text: #714415;
  --color-error: #ae342d;
  --color-error-bg: #fff0ec;
  --color-error-text: #962820;
  --color-error-border: #da8177;
  --color-shadow: rgba(24, 53, 53, 0.13);
  --shadow-sm: 0 1px 2px var(--color-shadow);
  --shadow-md: 0 10px 28px var(--color-shadow);
}
[data-theme='dark'] {
  color-scheme: dark;
  --color-background: #122826;
  --color-surface-1: #1b3430;
  --color-surface-2: #28423d;
  --color-surface-3: #35514b;
  --color-border: #45635a;
  --color-text-primary: #f4f7f0;
  --color-text-secondary: #d1e0d5;
  --color-text-tertiary: #b0c9ba;
  --color-text-inverted: #183535;
  --color-accent-primary: #d8f050;
  --color-accent-primary-rgb: 216, 240, 80;
  --color-accent-primary-hover: #efffa2;
  --color-accent-secondary: #2c443a;
  --color-highlight: #d8f050;
  --color-highlight-hover: #efffa2;
  --color-highlight-text: #183535;
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
::selection { background: var(--color-highlight); color: #183535; }
.skip-link { position: absolute; left: 12px; top: -80px; z-index: 1200; padding: 12px 18px; background: var(--color-highlight); color: #183535; }
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
