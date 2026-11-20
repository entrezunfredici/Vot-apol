<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { L } from '../lexique'
import EmptyPanel from './EmptyPanel.vue'

// Page dont le contenu n'est pas encore construit : elle le dit, au lieu de laisser croire à une
// fonctionnalité opérationnelle (CONVENTIONS, règles front).
defineProps<{ titre: string }>()
</script>

<template>
  <div class="mx-auto max-w-[1120px] px-5 pt-10 pb-[72px] md:px-10">
    <h1 class="mb-6 text-[28px] font-bold">{{ titre }}</h1>
    <EmptyPanel
      :titre="L.etat.prevueTitre"
      :aide="L.etat.prevueAide"
    >
      <RouterLink
        to="/scrutins"
        class="btn mt-4"
      >{{ L.nav.scrutins }}</RouterLink>
    </EmptyPanel>
  </div>
</template>
