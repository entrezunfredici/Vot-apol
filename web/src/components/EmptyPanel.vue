<script setup lang="ts">
defineProps<{ titre: string; aide?: string }>()
</script>

<template>
  <div class="card p-8 text-center">
    <p class="mb-1 font-bold">{{ titre }}</p>
    <p
      v-if="aide"
      class="text-sm text-ink-2"
    >
      {{ aide }}
    </p>
    <slot />
  </div>
</template>
