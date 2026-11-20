<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import EmptyPanel from '../components/EmptyPanel.vue'
import ErrorPanel from '../components/ErrorPanel.vue'
import GroupeRow from '../components/GroupeRow.vue'
import MisesAuPointTable from '../components/MisesAuPointTable.vue'
import VoteBadge from '../components/VoteBadge.vue'
import VoteBar from '../components/VoteBar.vue'
import { STYLES_VOTE } from '../components/voteStyles'
import { useAsync } from '../composables/useAsync'
import {
  chargerDeputes,
  chargerGroupes,
  chargerScrutin,
  ErreurChargement,
  type DeputeListe,
  type GroupeListe,
  type Vote,
} from '../data'
import { dateLongue, nombre, pourcentage, titreAffiche } from '../format'
import { L, libelleCategorie, libelleResultat } from '../lexique'

const route = useRoute()

// Accepte l'identifiant source (VTANR5L17V489) ou le seul numéro (489).
const identifiant = computed(() => {
  const id = String(route.params.id)
  return /^[1-9]\d*$/.test(id) ? `VTANR5L17V${id}` : id
})

const scrutin = useAsync(() => chargerScrutin(identifiant.value))
watch(identifiant, () => void scrutin.recharger())

// Les noms ne bloquent jamais la page : sans eux, les identifiants s'affichent « libellé non résolu ».
const groupes = shallowRef<Map<string, GroupeListe> | null>(null)
const deputes = shallowRef<Map<string, DeputeListe> | null>(null)
void chargerGroupes().then((g) => (groupes.value = g), () => undefined)
function chargerNomsDeputes(): void {
  if (!deputes.value) void chargerDeputes().then((d) => (deputes.value = d), () => undefined)
}
watch(
  () => scrutin.donnees.value,
  (s) => {
    if (s && (s.mises_au_point.length || s.dysfonctionnements.length)) chargerNomsDeputes()
  },
)

const introuvable = computed(
  () => scrutin.erreur.value instanceof ErreurChargement && scrutin.erreur.value.status === 404,
)

const votesParRang = computed(() => {
  const par = new Map<number, Vote[]>()
  for (const v of scrutin.donnees.value?.votes ?? []) par.set(v[1], [...(par.get(v[1]) ?? []), v])
  return par
})

const t = computed(() => scrutin.donnees.value?.totaux)
const causes = computed(() => {
  // Causes de non-vote (MG, PSE, PAN) relevées dans la liste nominative. Si elles dépassent le
  // nombre officiel de non-votants (écart connu de la source, ex. scrutin n° 1), on ne les affiche
  // pas : la phrase contredirait le chiffre officiel affiché juste au-dessus.
  const n: Record<string, number> = {}
  for (const v of scrutin.donnees.value?.votes ?? []) if (v[2] === 'non_votant' && v[4]) n[v[4]] = (n[v[4]] ?? 0) + 1
  const total = Object.values(n).reduce((a, b) => a + b, 0)
  return t.value && total <= t.value.non_votants ? Object.entries(n).filter(([, c]) => c > 0) : []
})

// Positions exprimées = pour + contre + abstentions (même définition que pour les groupes).
const exprimes = computed(() => (t.value ? t.value.pour + t.value.contre + t.value.abstentions : 0))

const stats = computed(() => {
  if (!t.value) return []
  const e = exprimes.value
  return [
    { type: 'pour' as const, label: L.scrutin.pour, n: t.value.pour, note: pourcentage(t.value.pour, e), sur: true },
    { type: 'contre' as const, label: L.scrutin.contre, n: t.value.contre, note: pourcentage(t.value.contre, e), sur: true },
    { type: 'abstention' as const, label: L.scrutin.abstentions, n: t.value.abstentions, note: pourcentage(t.value.abstentions, e), sur: true },
    { type: 'non_votant' as const, label: L.scrutin.nonVotants, n: t.value.non_votants, note: null, sur: false },
  ]
})

function infosGroupe(id: string | null): { sigle: string | null; libelle: string | null } {
  const g = id ? groupes.value?.get(id) : undefined
  return { sigle: g?.sigle ?? null, libelle: g?.libelle ?? null }
}
</script>

<template>
  <div class="mx-auto max-w-[1120px] px-5 pt-9 pb-[72px] md:px-10">
    <RouterLink
      to="/scrutins"
      class="mb-5 inline-flex items-center gap-1.5 text-[13px] font-semibold text-ink-2"
    >
      ← {{ L.scrutin.retour }}
    </RouterLink>

    <div
      v-if="scrutin.chargement.value"
      class="space-y-4"
      role="status"
    >
      <span class="sr-only">{{ L.etat.chargement }}</span>
      <div class="skeleton h-5 w-64" />
      <div class="skeleton h-8 w-full max-w-2xl" />
      <div class="skeleton h-48 w-full" />
    </div>
    <EmptyPanel
      v-else-if="introuvable"
      :titre="L.scrutin.introuvable"
      :aide="L.scrutin.introuvableAide"
    />
    <ErrorPanel
      v-else-if="scrutin.erreur.value"
      @reessayer="scrutin.recharger"
    />

    <template v-else-if="scrutin.donnees.value && t">
      <header class="mb-2 flex flex-wrap items-start justify-between gap-6">
        <div class="max-w-[720px]">
          <div class="mb-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[13px] text-ink-3">
            <span class="font-mono">{{ L.scrutin.numero }} {{ scrutin.donnees.value.numero }}</span>
            <span aria-hidden="true">·</span>
            <time :datetime="scrutin.donnees.value.date">{{ dateLongue(scrutin.donnees.value.date) }}</time>
            <span class="tag">{{ libelleCategorie(scrutin.donnees.value.categorie.valeur) }}</span>
          </div>
          <h1 class="mb-2.5 text-[26px] leading-snug font-bold">{{ titreAffiche(scrutin.donnees.value.titre) }}</h1>
          <p class="text-[13px] text-ink-3">{{ titreAffiche(scrutin.donnees.value.type_vote.libelle) }}</p>
          <p
            v-if="scrutin.donnees.value.categorie.a_verifier"
            class="mt-1 text-xs text-ink-3"
          >
            {{ L.scrutin.natureADeduire }}
          </p>
        </div>
        <VoteBadge
          type="resultat"
          :label="libelleResultat(scrutin.donnees.value.resultat)"
        />
      </header>

      <section
        class="card mt-6 mb-6 p-7"
        aria-labelledby="titre-repartition"
      >
        <h2
          id="titre-repartition"
          class="mb-4.5 text-base font-bold"
        >
          {{ L.scrutin.repartitionTitre(nombre(exprimes)) }}
        </h2>
        <div class="mb-4">
          <VoteBar
            :pour="t.pour"
            :contre="t.contre"
            :abstentions="t.abstentions"
          />
        </div>
        <dl class="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(160px,100%),1fr))]">
          <div
            v-for="s in stats"
            :key="s.type"
            class="flex flex-col-reverse justify-end"
          >
            <dt class="text-xs text-ink-2">
              {{ s.label }}
              <template v-if="s.sur">
                · {{ L.scrutin.sur(nombre(s.n), nombre(exprimes), s.note) }}
              </template>
              <template v-else>({{ L.scrutin.horsExprimes }})</template>
            </dt>
            <dd
              class="font-mono text-[22px] font-semibold"
              :class="STYLES_VOTE[s.type].texte"
            >
              {{ nombre(s.n) }}
            </dd>
          </div>
        </dl>
        <p class="mt-4 text-xs leading-relaxed text-ink-2">
          {{ L.scrutin.positionsNote }}
          {{ L.scrutin.suffragesOfficiels(nombre(t.suffrages_exprimes)) }}
        </p>
        <p
          v-if="causes.length"
          class="mt-4 text-xs leading-relaxed text-ink-2"
        >
          {{ L.scrutin.parmiNonVotants }}
          <template
            v-for="([code, n], i) in causes"
            :key="code"
          >
            <strong>{{ nombre(n) }}</strong> {{ L.scrutin.causes[code] ?? code }}<template v-if="i < causes.length - 1">, </template>
          </template>.
        </p>
        <p class="mt-3 text-xs leading-relaxed text-ink-2">{{ L.scrutin.nonVotantsNote }}</p>
        <div class="mt-4 border-t border-line pt-3 text-xs text-ink-2">
          <strong class="text-ink">{{ L.scrutin.sansVoteTitre }}</strong> :
          <template v-if="t.sans_vote_enregistre === null">{{ L.scrutin.sansVoteIndisponible }}</template>
          <template v-else-if="t.sans_vote_enregistre === 0">0.</template>
          <template v-else>{{ L.scrutin.sansVote(nombre(t.sans_vote_enregistre)) }}</template>
        </div>
      </section>

      <section
        class="card mb-6 overflow-hidden"
        aria-labelledby="titre-groupes"
      >
        <div class="flex flex-wrap items-center justify-between gap-3 px-6 pt-5 pb-1">
          <h2
            id="titre-groupes"
            class="text-base font-bold"
          >
            {{ L.scrutin.groupesTitre }}
          </h2>
          <span class="text-xs text-ink-3">{{ L.scrutin.groupesNote }}</span>
        </div>
        <p class="px-6 pt-1 pb-3.5 text-xs leading-relaxed text-ink-2">
          {{ L.scrutin.definition }}
          <RouterLink
            to="/methodologie"
            class="font-semibold"
          >{{ L.nav.methodologie }}</RouterLink>
        </p>
        <p
          v-if="scrutin.donnees.value.groupes.some((g) => g.groupe_id === null)"
          class="border-t border-line bg-accent-50 px-6 py-3 text-xs text-ink-2"
        >
          {{ L.scrutin.groupeNonIdentifieNote }}
        </p>
        <GroupeRow
          v-for="g in scrutin.donnees.value.groupes"
          :key="g.rang"
          :groupe="g"
          :sigle="infosGroupe(g.groupe_id).sigle"
          :libelle="infosGroupe(g.groupe_id).libelle"
          :votes="votesParRang.get(g.rang) ?? []"
          :mises-au-point="scrutin.donnees.value.mises_au_point.filter((m) => m.groupe_rang === g.rang)"
          :deputes="deputes"
          @ouvrir="chargerNomsDeputes"
        />
      </section>

      <MisesAuPointTable
        v-if="scrutin.donnees.value.mises_au_point.length"
        :titre="L.scrutin.miseAuPointTitre(scrutin.donnees.value.mises_au_point.length)"
        :intro="L.scrutin.miseAuPointIntro"
        :lignes="scrutin.donnees.value.mises_au_point"
        :deputes="deputes"
        :groupes="groupes"
      />
      <MisesAuPointTable
        v-if="scrutin.donnees.value.dysfonctionnements.length"
        :titre="L.scrutin.dysfonctionnementsTitre(scrutin.donnees.value.dysfonctionnements.length)"
        :intro="L.scrutin.dysfonctionnementsIntro"
        :lignes="scrutin.donnees.value.dysfonctionnements"
        :deputes="deputes"
        :groupes="groupes"
      />

      <section class="card flex flex-wrap items-center justify-between gap-6 px-7 py-6">
        <div class="flex flex-wrap gap-7">
          <a
            :href="scrutin.donnees.value.source.lien_officiel"
            class="inline-flex items-center gap-1.5 text-[13px] font-semibold"
            rel="noopener"
          >
            {{ L.scrutin.sourceOfficielle }} ↗
          </a>
        </div>
        <p class="max-w-md text-xs text-ink-3">{{ L.scrutin.sourceNote }}</p>
        <p class="w-full font-mono text-[11px] break-all text-ink-3">
          {{ L.scrutin.provenance }} : {{ scrutin.donnees.value.source.fichier }} · SHA-256
          {{ scrutin.donnees.value.source.sha256 }}
        </p>
      </section>
    </template>
  </div>
</template>
