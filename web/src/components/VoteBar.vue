<script setup lang="ts">
import { computed } from 'vue'
import { L } from '../lexique'
import { nombre } from '../format'
import { STYLES_VOTE } from './voteStyles'

// Barre de répartition des suffrages exprimés : les largeurs sont proportionnelles aux effectifs
// (axe honnête, de 0 à 100 % des exprimés) ; les effectifs exacts sont dans le texte alternatif et
// dans la légende de l'appelant.
const props = defineProps<{ pour: number; contre: number; abstentions: number }>()

const exprimes = computed(() => props.pour + props.contre + props.abstentions)
const segments = computed(() =>
  (
    [
      ['pour', props.pour],
      ['contre', props.contre],
      ['abstention', props.abstentions],
    ] as const
  ).map(([type, n]) => ({ type, n, largeur: exprimes.value ? (n / exprimes.value) * 100 : 0 })),
)
const alternatif = computed(
  () =>
    `${L.scrutin.pour} : ${nombre(props.pour)} · ${L.scrutin.contre} : ${nombre(props.contre)} · ` +
    `${L.scrutin.abstentions} : ${nombre(props.abstentions)} (${nombre(exprimes.value)} exprimés)`,
)
</script>

<template>
  <div
    v-if="exprimes > 0"
    class="flex h-7 overflow-hidden rounded-lg bg-surface-alt"
    role="img"
    :aria-label="alternatif"
  >
    <div
      v-for="s in segments"
      v-show="s.n > 0"
      :key="s.type"
      :class="STYLES_VOTE[s.type].segment"
      :style="{ width: `${s.largeur}%` }"
    />
  </div>
</template>
