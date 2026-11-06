import { Emitter, type AuthClient, type AuthUser } from './types'

interface ClerkUserLike {
  id: string
  fullName?: string | null
  primaryEmailAddress?: { emailAddress: string } | null
}

/** Clerk adapter (headless, loaded on demand). The only file that knows about Clerk. */
export function createClerkAuth(publishableKey: string | undefined): AuthClient {
  const emitter = new Emitter()
  let user: AuthUser | null = null
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let clerk: any = null

  const toUser = (u: ClerkUserLike | null | undefined): AuthUser | null =>
    u ? { id: u.id, email: u.primaryEmailAddress?.emailAddress ?? null, name: u.fullName ?? null } : null

  return {
    name: 'clerk',
    async init() {
      if (!publishableKey) throw new Error('VITE_CLERK_PUBLISHABLE_KEY is not set')
      const { Clerk } = await import('@clerk/clerk-js')
      clerk = new Clerk(publishableKey)
      await clerk.load()
      user = toUser(clerk.user)
      clerk.addListener(({ user: u }: { user?: ClerkUserLike | null }) => {
        const next = toUser(u)
        if (next?.id === user?.id) return
        user = next
        emitter.emit(user)
      })
    },
    getUser: () => user,
    onChange: (l) => emitter.subscribe(l),
    getToken: async () => (clerk?.session ? ((await clerk.session.getToken()) ?? null) : null),
    signIn: async () => clerk?.openSignIn({}),
    signUp: async () => clerk?.openSignUp({}),
    signOut: async () => clerk?.signOut(),
    openAccount: async () => clerk?.openUserProfile(),
  }
}
