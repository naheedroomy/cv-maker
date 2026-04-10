<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from './components/AppSidebar.vue'
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
      <RouterView />
    </main>
  </div>
</template>

<style>
:root {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  color: #111827;
  background: #f8f9fa;
  margin: 0;
  padding: 0;
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
  background: #f8f9fa;
}

@media (max-width: 768px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.4);
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
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    cursor: pointer;
    color: #374151;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .sidebar-toggle:hover {
    background: #f3f4f6;
  }

  .main-content {
    padding: 24px 16px;
    padding-top: 64px;
  }
}
</style>
