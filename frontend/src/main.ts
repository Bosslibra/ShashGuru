import './assets/main.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import I18NextVue from 'i18next-vue'
import i18next from './i18n'

async function bootstrap() {
  // DEV only: apply the chosen visual direction before the first paint of the app
  if (import.meta.env.DEV) (await import('./dev/direction')).initDirection()

  createApp(App).use(createPinia()).use(router).use(I18NextVue, { i18next }).mount('#app')
}

bootstrap()
