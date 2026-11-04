<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { L } from './lexique'
</script>

<template>
  <header class="border-b p-4">
    <nav class="flex gap-4">
      <RouterLink to="/">{{ L.nav.accueil }}</RouterLink>
      <RouterLink to="/scrutins">{{ L.nav.scrutins }}</RouterLink>
      <RouterLink to="/comparateur">{{ L.nav.comparateur }}</RouterLink>
      <RouterLink to="/methodologie">{{ L.nav.methodologie }}</RouterLink>
    </nav>
  </header>
  <main class="p-4"><RouterView /></main>
</template>
