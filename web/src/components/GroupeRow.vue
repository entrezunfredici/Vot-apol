<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { DeputeListe, GroupeScrutin, MiseAuPoint, Position, Vote } from '../data'
import { nombre } from '../format'
import { L, libellePositionMajoritaire, libelleRaisonAbsence } from '../lexique'
import VoteBadge from './VoteBadge.vue'

// Une ligne de groupe : effectifs exacts, position majoritaire avec son dénominateur, et (à l'ouverture)
// le vote de chaque député. Aucune couleur propre au groupe (charte de neutralité).
const props = defineProps<{
  groupe: GroupeScrutin
  sigle: string | null
  libelle: string | null
  votes: Vote[]
  misesAuPoint: MiseAuPoint[]
  deputes: Map<string, DeputeListe> | null
}>()
const emit = defineEmits<{ ouvrir: [] }>()

const ouvert = ref(false)
const identifie = computed(() => props.groupe.groupe_id !== null)
const nom = computed(() => props.sigle ?? props.libelle ?? props.groupe.groupe_id ?? L.scrutin.groupeNonIdentifie)
const exprimes = computed(() => props.groupe.pour + props.groupe.contre + props.groupe.abstentions)
const pm = computed(() => props.groupe.position_majoritaire)
const idsMiseAuPoint = computed(() => new Set(props.misesAuPoint.map((m) => m.depute_id)))

const ORDRE: Record<Position, number> = { pour: 0, contre: 1, abstention: 2, non_votant: 3 }

function nomDepute(id: string): { texte: string; resolu: boolean } {
  const d = props.deputes?.get(id)
  if (!d?.nom) return { texte: id, resolu: false }
  return { texte: [d.prenom, d.nom].filter(Boolean).join(' '), resolu: true }
}

const lignesDeputes = computed(() =>
  props.votes
    .map(([id, , position, delegation, cause]) => ({ id, position, delegation: delegation === 1, cause, ...nomDepute(id) }))
    .sort((a, b) => ORDRE[a.position] - ORDRE[b.position] || a.texte.localeCompare(b.texte, 'fr')),
)

function basculer(): void {
  ouvert.value = !ouvert.value
  if (ouvert.value) emit('ouvrir')
}

const idPanneau = `groupe-${props.groupe.rang}`
</script>

<template>
  <div class="border-t border-line">
    <button
      type="button"
      class="flex w-full flex-wrap items-center justify-between gap-x-6 gap-y-2 px-5 py-4 text-left hover:bg-accent-50"
      :aria-expanded="ouvert"
      :aria-controls="idPanneau"
      :aria-label="ouvert ? L.scrutin.fermerGroupe(nom) : L.scrutin.ouvrirGroupe(nom)"
      :disabled="!identifie || votes.length === 0"
      @click="basculer"
    >
      <div class="flex min-w-0 items-center gap-3">
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="shrink-0 text-ink-3 transition-transform"
          :class="ouvert ? 'rotate-90' : ''"
          aria-hidden="true"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
        <span class="w-16 shrink-0 text-sm font-bold">{{ identifie ? sigle ?? '—' : '—' }}</span>
        <div class="min-w-0">
          <div class="text-[13px]">
            <template v-if="!identifie">{{ L.scrutin.groupeNonIdentifie }}</template>
            <template v-else-if="libelle">{{ libelle }}</template>
            <template v-else>
              <span class="text-ink-2">{{ L.scrutin.libelleNonResolu }}</span>
              <span class="ml-1.5 font-mono text-xs text-ink-3">{{ groupe.groupe_id }}</span>
            </template>
          </div>
          <div class="mt-0.5 font-mono text-[11px] text-ink-3">
            {{ L.scrutin.pour }} {{ nombre(groupe.pour) }} · {{ L.scrutin.contre }} {{ nombre(groupe.contre) }} ·
            {{ L.scrutin.abstentions }} {{ nombre(groupe.abstentions) }} · {{ L.scrutin.nonVotants }}
            {{ nombre(groupe.non_votants) }}<template v-if="groupe.sans_vote_enregistre">
              · {{ L.scrutin.sansVoteTitre }} {{ nombre(groupe.sans_vote_enregistre) }}
            </template>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-4.5">
        <div class="text-right">
          <div class="font-mono text-xs">
            {{ L.scrutin.exprimesSur(nombre(exprimes), nombre(groupe.membres)) }}
          </div>
          <div
            v-if="pm && pm.position !== 'aucune'"
            class="mt-0.5 text-[11px] text-ink-3"
          >
            {{ L.scrutin.positionDetail(nombre(pm.m), nombre(pm.exprimes), pm.majorite_absolue) }}
          </div>
          <div
            v-else-if="pm"
            class="mt-0.5 text-[11px] text-ink-3"
          >
            {{ libelleRaisonAbsence(pm.raison_absence) }}
          </div>
          <div
            v-else
            class="mt-0.5 text-[11px] text-ink-3"
          >
            {{ L.scrutin.nonCalculee }}
          </div>
        </div>
        <VoteBadge
          v-if="pm && pm.position !== 'aucune'"
          :type="pm.position"
          :label="libellePositionMajoritaire(pm.position)"
          compact
        />
        <span
          v-else-if="pm"
          class="tag border border-line"
        >{{ L.scrutin.pasDePosition }}</span>
      </div>
    </button>

    <div
      v-if="groupe.correction_mise_au_point"
      class="border-t border-line bg-accent-50 px-5 py-3 text-[13px] text-ink-2"
    >
      <strong class="text-ink">
        {{ groupe.correction_mise_au_point.change_position_majoritaire ? L.scrutin.miseAuPointModifie : L.scrutin.miseAuPointSansChangement }}
      </strong>
      {{
        L.scrutin.miseAuPointChiffres(
          groupe.correction_mise_au_point.pour_corrige,
          groupe.correction_mise_au_point.contre_corrige,
          groupe.correction_mise_au_point.abstentions_corrigees,
        )
      }}
    </div>

    <div
      v-if="ouvert"
      :id="idPanneau"
      class="bg-surface-alt"
    >
      <p class="px-5 pt-3 pb-1 text-xs text-ink-2">{{ L.scrutin.voteDeputes(votes.length) }}</p>
      <ul>
        <li
          v-for="d in lignesDeputes"
          :key="d.id"
          class="flex flex-wrap items-center justify-between gap-2 border-t border-line/70 px-5 py-2 pl-12 text-[13px]"
        >
          <span>
            {{ d.texte }}
            <span
              v-if="!d.resolu"
              class="ml-1.5 text-xs text-ink-3"
            >({{ L.scrutin.deputeNonResolu }})</span>
          </span>
          <span class="flex flex-wrap items-center justify-end gap-2">
            <span
              v-if="d.cause"
              class="tag"
            >{{ L.scrutin.causes[d.cause] ?? d.cause }}</span>
            <span
              v-if="d.delegation"
              class="tag"
            >{{ L.scrutin.delegation }}</span>
            <span
              v-if="idsMiseAuPoint.has(d.id)"
              class="tag border border-accent-100 bg-accent-100 text-accent-600"
            >{{ L.scrutin.miseAuPointSignalee }}</span>
            <VoteBadge
              :type="d.position"
              compact
            />
          </span>
        </li>
      </ul>
      <div class="px-5 py-3 pl-12">
        <RouterLink
          v-if="groupe.groupe_id"
          :to="`/groupes/${groupe.groupe_id}`"
          class="text-xs font-semibold"
        >
          {{ L.scrutin.voirGroupe }}
        </RouterLink>
      </div>
    </div>
  </div>
</template>
