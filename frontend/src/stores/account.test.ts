import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ApiError } from '@/api/http'
import type { AuthClient } from '@/auth'
import type { Me } from '@/types/api'

vi.mock('@/api/backend', () => ({
  getConfig: vi.fn(),
  getMe: vi.fn(),
  getModels: vi.fn(),
  getKeys: vi.fn(),
  getOffers: vi.fn(),
  getUsage: vi.fn(),
  createKey: vi.fn(),
  deleteKey: vi.fn(),
  testKey: vi.fn(),
  createCheckout: vi.fn(),
  createPortal: vi.fn(),
  deleteAccount: vi.fn(),
}))

import * as backend from '@/api/backend'
import { useAccountStore } from './account'
import { useAuthStore } from './auth'

const ME: Me = {
  id: 1,
  email: 'a@b.c',
  is_admin: false,
  plan: null,
  subscription: null,
  balance: { subscription: 10, purchased: 5, total: 15 },
  usage_month: { requests: 0, input_tokens: 0, output_tokens: 0, credits: 0 },
}

function fakeAuth(signedIn: boolean): AuthClient {
  const user = signedIn ? { id: 'u1', email: 'a@b.c' } : null
  return {
    name: 'dev',
    init: async () => {},
    getUser: () => user,
    onChange: () => () => {},
    getToken: async () => (user ? 'tok' : null),
    signIn: async () => {},
    signUp: async () => {},
    signOut: async () => {},
  }
}

const SAAS = { deployment_mode: 'saas', billing_enabled: true, byok_enabled: true, engine_anon_max_depth: 12 } as const

beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
  vi.mocked(backend.getModels).mockResolvedValue({ managed: [], byok_suggestions: { openai: [], anthropic: [], openrouter: [], custom: [] }, default_managed: null })
  vi.mocked(backend.getKeys).mockResolvedValue([])
  vi.mocked(backend.getOffers).mockResolvedValue([])
})

describe('account store', () => {
  it('is saas only with a hosted config and an auth provider', async () => {
    vi.mocked(backend.getConfig).mockResolvedValue({ ...SAAS })
    const auth = useAuthStore()
    auth.useClient(fakeAuth(false))
    const account = useAccountStore()
    await account.init()
    expect(account.saas).toBe(true)
    expect(backend.getMe).not.toHaveBeenCalled() // signed out: no account data
  })

  it('behaves as self-hosted when the config is unavailable', async () => {
    vi.mocked(backend.getConfig).mockRejectedValue(new ApiError(404, 'not found'))
    const auth = useAuthStore()
    auth.useClient(fakeAuth(true))
    const account = useAccountStore()
    await account.init()
    expect(account.saas).toBe(false)
    expect(backend.getMe).not.toHaveBeenCalled()
  })

  it('behaves as self-hosted when no auth provider is configured', async () => {
    vi.mocked(backend.getConfig).mockResolvedValue({ ...SAAS })
    const auth = useAuthStore() // default adapter: none
    const account = useAccountStore()
    await account.init()
    expect(auth.enabled).toBe(false)
    expect(account.saas).toBe(false)
  })

  it('loads the account data for a signed-in user', async () => {
    vi.mocked(backend.getConfig).mockResolvedValue({ ...SAAS })
    vi.mocked(backend.getMe).mockResolvedValue(ME)
    const auth = useAuthStore()
    auth.useClient(fakeAuth(true))
    const account = useAccountStore()
    await account.init()
    expect(account.me?.balance.total).toBe(15)
    expect(backend.getOffers).toHaveBeenCalled()
  })

  it('applies the balance of a usage event without another request', async () => {
    vi.mocked(backend.getConfig).mockResolvedValue({ ...SAAS })
    vi.mocked(backend.getMe).mockResolvedValue(ME)
    const auth = useAuthStore()
    auth.useClient(fakeAuth(true))
    const account = useAccountStore()
    await account.init()
    account.applyBalance({ subscription: 8, purchased: 5, total: 13 })
    expect(account.balance?.total).toBe(13)
    expect(backend.getMe).toHaveBeenCalledTimes(1)
  })

  it('adds and removes keys locally after the API succeeds', async () => {
    const key = { id: 7, provider: 'openai', label: '', hint: 'abcd', base_url: null, created_at: '', last_used_at: null } as const
    vi.mocked(backend.createKey).mockResolvedValue({ ...key })
    vi.mocked(backend.deleteKey).mockResolvedValue()
    const account = useAccountStore()
    await account.addKey({ provider: 'openai', api_key: 'sk-x' })
    expect(account.keys.map((k) => k.id)).toEqual([7])
    await account.removeKey(7)
    expect(account.keys).toEqual([])
  })

  it('appends usage pages when an offset is given', async () => {
    const item = (id: number) => ({ id, created_at: '', source: 'managed' as const, provider: 'p', model: 'm', input_tokens: 1, output_tokens: 1, credits_charged: 1, status: 'ok' })
    vi.mocked(backend.getUsage).mockResolvedValueOnce({ items: [item(1)], total: 2 })
    vi.mocked(backend.getUsage).mockResolvedValueOnce({ items: [item(2)], total: 2 })
    const account = useAccountStore()
    await account.loadUsage(1, 0)
    await account.loadUsage(1, 1)
    expect(account.usage.items.map((i) => i.id)).toEqual([1, 2])
  })
})
