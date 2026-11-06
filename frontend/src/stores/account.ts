import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import * as backend from '@/api/backend'
import { isApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import type { AppConfig, Balance, KeyOut, Me, ModelCatalog, NewKey, Offer, UsagePage } from '@/types/api'

/** Server-side state of the signed-in user: config, balance, API keys, offers. */
export const useAccountStore = defineStore('account', () => {
  const auth = useAuthStore()

  const config = ref<AppConfig | null>(null)
  const me = ref<Me | null>(null)
  const models = ref<ModelCatalog | null>(null)
  const keys = ref<KeyOut[]>([])
  const offers = ref<Offer[]>([])
  const usage = ref<UsagePage>({ items: [], total: 0 })
  const loading = ref(false)

  /** True only on a hosted deployment that also has a login provider: otherwise the UI behaves as self-hosted. */
  const saas = computed(() => config.value?.deployment_mode === 'saas' && auth.enabled)
  const billingEnabled = computed(() => saas.value && !!config.value?.billing_enabled)
  const byokEnabled = computed(() => saas.value && !!config.value?.byok_enabled)
  const balance = computed<Balance | null>(() => me.value?.balance ?? null)

  let initPromise: Promise<void> | null = null
  /** Sign-in changes are handled by the watcher only once the first load is done (init loads everything itself). */
  let initialised = false

  async function loadConfig() {
    try {
      config.value = await backend.getConfig()
    } catch {
      // Old or local backend without /config: behave as self-hosted.
      config.value = { deployment_mode: 'selfhosted', billing_enabled: false, byok_enabled: false, engine_anon_max_depth: 0 }
    }
  }

  /** Load the public configuration once, then (if signed in) the account data. */
  function init(): Promise<void> {
    initPromise ??= (async () => {
      await Promise.all([loadConfig(), auth.init()])
      if (saas.value && auth.signedIn) await refreshAll()
      initialised = true
    })()
    return initPromise
  }

  async function refreshMe() {
    try {
      me.value = await backend.getMe()
    } catch (e) {
      if (isApiError(e, 401)) me.value = null
      else console.error('Could not load the account:', e)
    }
  }

  async function loadModels() {
    try {
      models.value = await backend.getModels()
    } catch (e) {
      console.error('Could not load the models:', e)
    }
  }

  async function loadKeys() {
    try {
      keys.value = await backend.getKeys()
    } catch (e) {
      console.error('Could not load the API keys:', e)
    }
  }

  async function loadOffers() {
    try {
      offers.value = await backend.getOffers()
    } catch (e) {
      console.error('Could not load the offers:', e)
    }
  }

  /** Load a page of the usage history; with `offset > 0` the page is appended to what is already loaded. */
  async function loadUsage(limit = 20, offset = 0) {
    const page = await backend.getUsage(limit, offset)
    usage.value = offset > 0 ? { total: page.total, items: [...usage.value.items, ...page.items] } : page
  }

  async function refreshAll() {
    loading.value = true
    try {
      await Promise.all([refreshMe(), loadModels(), loadKeys(), config.value?.billing_enabled ? loadOffers() : undefined])
    } finally {
      loading.value = false
    }
  }

  /** Apply the balance sent with a `usage` stream event without another request. */
  function applyBalance(next: Balance | null | undefined) {
    if (next && me.value) me.value = { ...me.value, balance: next }
  }

  async function addKey(key: NewKey): Promise<KeyOut> {
    const created = await backend.createKey(key)
    keys.value = [...keys.value, created]
    return created
  }

  async function removeKey(id: number) {
    await backend.deleteKey(id)
    keys.value = keys.value.filter((k) => k.id !== id)
  }

  const testKey = (id: number) => backend.testKey(id)

  /** Hosted checkout: we never embed a payment SDK, the backend returns the provider's URL. */
  async function checkout(offerId: string) {
    const { url } = await backend.createCheckout(offerId)
    window.location.assign(url)
  }

  async function openPortal() {
    const { url } = await backend.createPortal()
    window.location.assign(url)
  }

  async function deleteAccount() {
    await backend.deleteAccount()
    clear()
    await auth.signOut()
  }

  function clear() {
    me.value = null
    keys.value = []
    usage.value = { items: [], total: 0 }
  }

  // Follow sign-in / sign-out.
  watch(
    () => auth.user?.id,
    async (id) => {
      if (!initialised) return
      if (id && saas.value) await refreshAll()
      else clear()
    },
  )

  return {
    config, me, models, keys, offers, usage, loading,
    saas, billingEnabled, byokEnabled, balance,
    init, loadConfig, refreshMe, loadModels, loadKeys, loadOffers, loadUsage, refreshAll,
    applyBalance, addKey, removeKey, testKey, checkout, openPortal, deleteAccount, clear,
  }
})
