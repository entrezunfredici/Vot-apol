<script setup lang="ts">
import { RouterLink } from 'vue-router'
import EmptyPanel from '../components/EmptyPanel.vue'
import { L } from '../lexique'
</script>

<template>
  <div class="mx-auto max-w-[1120px] px-5 pt-10 pb-[72px] md:px-10">
    <EmptyPanel
      :titre="L.etat.introuvableTitre"
      :aide="L.etat.introuvableAide"
    >
      <RouterLink
        to="/"
        class="btn mt-4"
      >{{ L.nav.accueil }}</RouterLink>
    </EmptyPanel>
  </div>
</template>
