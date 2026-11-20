import { createRouter, createWebHistory } from 'vue-router'
import { L } from './lexique'

// Les pages sont chargées à la demande : le premier chargement reste léger sur mobile.
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('./pages/AccueilPage.vue'), meta: { titre: L.nav.accueil } },
    { path: '/scrutins', component: () => import('./pages/ScrutinsPage.vue'), meta: { titre: L.nav.scrutins } },
    { path: '/scrutins/:id', component: () => import('./pages/ScrutinDetailPage.vue'), meta: { titre: L.nav.scrutins } },
    { path: '/groupes', component: () => import('./pages/GroupesPage.vue'), meta: { titre: L.nav.groupes } },
    { path: '/groupes/:id', component: () => import('./pages/GroupeDetailPage.vue'), meta: { titre: L.nav.groupes } },
    { path: '/comparateur', component: () => import('./pages/ComparateurPage.vue'), meta: { titre: L.nav.comparateur } },
    { path: '/statistiques', component: () => import('./pages/StatistiquesPage.vue'), meta: { titre: L.nav.statistiques } },
    { path: '/methodologie', component: () => import('./pages/MethodologiePage.vue'), meta: { titre: L.nav.methodologie } },
    { path: '/qualite', component: () => import('./pages/QualitePage.vue'), meta: { titre: L.nav.qualite } },
    { path: '/:autre(.*)*', component: () => import('./pages/IntrouvablePage.vue'), meta: { titre: L.etat.introuvableTitre } },
  ],
  scrollBehavior: (to, from, saved) => saved ?? (to.path === from.path ? false : { top: 0 }),
})

router.afterEach((to) => {
  const titre = typeof to.meta.titre === 'string' ? to.meta.titre : ''
  document.title = titre ? `${titre} — ${L.marque}` : L.marque
})
