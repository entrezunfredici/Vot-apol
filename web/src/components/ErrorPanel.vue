<script setup lang="ts">
import { L } from '../lexique'

defineProps<{ titre?: string; aide?: string }>()
defineEmits<{ reessayer: [] }>()
</script>

<template>
  <div
    class="card p-8 text-center"
    role="alert"
  >
    <p class="mb-1 font-bold">{{ titre ?? L.etat.erreurTitre }}</p>
    <p class="mb-4 text-sm text-ink-2">{{ aide ?? L.etat.erreurAide }}</p>
    <button
      type="button"
      class="btn btn-primary"
      @click="$emit('reessayer')"
    >
      {{ L.etat.reessayer }}
    </button>
  </div>
</template>
