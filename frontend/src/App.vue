<script setup lang="ts">
import AppSidebar from './components/AppSidebar.vue'
import { useAuthStore } from '@/stores/authStore'

const authStore = useAuthStore()
</script>

<template>
  <div v-if="!authStore.isAuthenticated" class="signin-layout">
    <RouterView />
  </div>
  <div v-else class="app-shell">
    <AppSidebar />
    <main class="main-content">
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
  min-width: 640px;
}

.main-content {
  max-width: 800px;
  width: 100%;
  padding: 32px 24px;
  margin: 0 auto;
  overflow-y: auto;
}

.signin-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
}
</style>
