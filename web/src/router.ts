import { createRouter, createWebHistory } from 'vue-router'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('./pages/AccueilPage.vue') },
    { path: '/scrutins', component: () => import('./pages/ScrutinsPage.vue') },
    { path: '/scrutins/:id', component: () => import('./pages/ScrutinDetailPage.vue') },
    { path: '/comparateur', component: () => import('./pages/ComparateurPage.vue') },
    { path: '/methodologie', component: () => import('./pages/MethodologiePage.vue') },
  ],
})
