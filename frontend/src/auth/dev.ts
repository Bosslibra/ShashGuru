import { Emitter, type AuthClient, type AuthUser } from './types'

const STORAGE_KEY = 'shashguru.dev-auth'

function load(): AuthUser | null {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    if (raw && typeof raw.id === 'string') return { id: raw.id, email: raw.email ?? null, name: raw.name ?? null }
  } catch {
    /* ignore */
  }
  return null
}

function save(user: AuthUser | null) {
  try {
    if (user) localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

/** Token format understood by the backend's `dev` auth adapter: `dev:<subject>:<email>`. DEVELOPMENT ONLY. */
export function devToken(user: AuthUser): string {
  return `dev:${user.id}:${user.email ?? ''}`
}

export function createDevAuth(): AuthClient {
  const emitter = new Emitter()
  let user: AuthUser | null = null

  function signInWithPrompt() {
    const email = typeof window !== 'undefined' ? window.prompt('Dev sign-in: email', user?.email ?? 'dev@example.com') : null
    if (!email) return
    const id = email.split('@')[0].replace(/[^a-zA-Z0-9_-]/g, '') || 'dev'
    user = { id, email, name: id }
    save(user)
    emitter.emit(user)
  }

  return {
    name: 'dev',
    init: async () => {
      user = load()
    },
    getUser: () => user,
    onChange: (l) => emitter.subscribe(l),
    getToken: async () => (user ? devToken(user) : null),
    signIn: async () => signInWithPrompt(),
    signUp: async () => signInWithPrompt(),
    signOut: async () => {
      user = null
      save(null)
      emitter.emit(null)
    },
  }
}
