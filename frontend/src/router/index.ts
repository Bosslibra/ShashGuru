import { createRouter, createWebHistory } from 'vue-router'
import { useAccountStore } from '@/stores/account'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    /** Only reachable on a hosted (SaaS) deployment: otherwise redirected home. */
    saasOnly?: boolean
    /** Needs a signed-in user. */
    requiresAuth?: boolean
    /** Legal document key (see LegalView). */
    doc?: 'terms' | 'privacy'
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
    { path: '/about', name: 'about', component: () => import('../views/AboutView.vue') },
    { path: '/live', name: 'live', component: () => import('../views/LiveView.vue') },
    { path: '/pricing', name: 'pricing', component: () => import('../views/PricingView.vue'), meta: { saasOnly: true } },
    {
      path: '/account',
      name: 'account',
      component: () => import('../views/AccountView.vue'),
      meta: { saasOnly: true, requiresAuth: true },
    },
    { path: '/legal/terms', name: 'terms', component: () => import('../views/LegalView.vue'), meta: { doc: 'terms' } },
    { path: '/legal/privacy', name: 'privacy', component: () => import('../views/LegalView.vue'), meta: { doc: 'privacy' } },
    { path: '/:pathMatch(.*)*', redirect: { name: 'home' } },
  ],
})

router.beforeEach(async (to) => {
  if (!to.meta.saasOnly && !to.meta.requiresAuth) return true
  const account = useAccountStore()
  const auth = useAuthStore()
  await account.init()
  if (to.meta.saasOnly && !account.saas) return { name: 'home' }
  if (to.meta.requiresAuth && !auth.signedIn) {
    void auth.signIn()
    return { name: 'home' }
  }
  return true
})

export default router
