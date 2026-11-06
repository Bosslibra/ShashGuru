import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/about', name: 'about', component: () => import('../views/AboutView.vue') },
    { path: '/live', name: 'live', component: () => import('../views/LiveView.vue') },
    { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
  ],
})

export default router
