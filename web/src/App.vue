<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppFooter from './components/AppFooter.vue'
import AppHeader from './components/AppHeader.vue'
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <AppHeader />
    <main
      id="contenu"
      class="flex-1"
    >
      <RouterView />
    </main>
    <AppFooter />
  </div>
</template>
