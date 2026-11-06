/**
 * Auth is a port: the app only knows this interface. Each provider (Clerk, dev, none, ...)
 * is an adapter in this folder; no other module may import a vendor SDK.
 */
export interface AuthUser {
  /** Opaque subject, as the backend sees it in the token. */
  id: string
  email: string | null
  name?: string | null
}

export type AuthProviderName = 'none' | 'dev' | 'clerk'

export interface AuthClient {
  readonly name: AuthProviderName
  /** Load the provider and restore a previous session. Must be safe to call once. */
  init(): Promise<void>
  getUser(): AuthUser | null
  /** Subscribe to sign-in / sign-out. Returns an unsubscribe function. */
  onChange(listener: (user: AuthUser | null) => void): () => void
  /** A bearer token for the backend, or null when signed out. */
  getToken(): Promise<string | null>
  signIn(): Promise<void>
  signUp(): Promise<void>
  signOut(): Promise<void>
  /** Provider-hosted account page, when there is one. */
  openAccount?(): Promise<void>
}

/** Small helper shared by adapters. */
export class Emitter {
  private listeners = new Set<(user: AuthUser | null) => void>()
  subscribe(listener: (user: AuthUser | null) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }
  emit(user: AuthUser | null) {
    this.listeners.forEach((l) => l(user))
  }
}
