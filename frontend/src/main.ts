import './assets/main.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import I18NextVue from 'i18next-vue'
import i18next from './i18n'
import { setAuthTokenProvider } from './api/http'
import { useAccountStore } from './stores/account'
import { useAuthStore } from './stores/auth'

async function bootstrap() {
  // DEV only: apply the chosen visual direction before the first paint of the app
  if (import.meta.env.DEV) (await import('./dev/direction')).initDirection()

  const pinia = createPinia()
  const app = createApp(App).use(pinia).use(I18NextVue, { i18next })

  // Requests to our backend carry the bearer token of whichever auth adapter is configured.
  const auth = useAuthStore(pinia)
  setAuthTokenProvider(() => auth.getToken())
  // Public config + account data load in the background; the UI reacts when they arrive.
  void useAccountStore(pinia).init()

  app.use(router).mount('#app')
}

bootstrap()
