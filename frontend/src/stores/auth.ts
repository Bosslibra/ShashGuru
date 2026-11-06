import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import { createAuthClient, type AuthClient, type AuthUser } from '@/auth'

/** Thin reactive wrapper around the configured AuthClient. Knows nothing about the provider. */
export const useAuthStore = defineStore('auth', () => {
  const client = shallowRef<AuthClient>(createAuthClient())
  const user = ref<AuthUser | null>(null)
  const ready = ref(false)
  const error = ref<string | null>(null)

  /** False when no auth provider is configured (self-hosted): the UI shows no login at all. */
  const enabled = computed(() => client.value.name !== 'none')
  const signedIn = computed(() => user.value !== null)

  let initPromise: Promise<void> | null = null

  function init(): Promise<void> {
    initPromise ??= (async () => {
      try {
        await client.value.init()
        user.value = client.value.getUser()
        client.value.onChange((u) => (user.value = u))
      } catch (e) {
        console.error('Auth initialisation failed:', e)
        error.value = e instanceof Error ? e.message : String(e)
      } finally {
        ready.value = true
      }
    })()
    return initPromise
  }

  /** Replace the adapter (used by tests). */
  function useClient(next: AuthClient) {
    client.value = next
    initPromise = null
    ready.value = false
    user.value = null
  }

  const getToken = () => client.value.getToken().catch(() => null)

  return {
    user,
    ready,
    error,
    enabled,
    signedIn,
    provider: computed(() => client.value.name),
    canOpenAccount: computed(() => typeof client.value.openAccount === 'function'),
    init,
    useClient,
    getToken,
    signIn: () => client.value.signIn(),
    signUp: () => client.value.signUp(),
    signOut: () => client.value.signOut(),
    openAccount: () => client.value.openAccount?.() ?? Promise.resolve(),
  }
})
