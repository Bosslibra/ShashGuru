import { createClerkAuth } from './clerk'
import { createDevAuth } from './dev'
import { createNoneAuth } from './none'
import type { AuthClient, AuthProviderName } from './types'

export type { AuthClient, AuthUser, AuthProviderName } from './types'

export function configuredProvider(): AuthProviderName {
  const value = import.meta.env.VITE_AUTH_PROVIDER
  return value === 'clerk' || value === 'dev' ? value : 'none'
}

export function createAuthClient(provider: AuthProviderName = configuredProvider()): AuthClient {
  switch (provider) {
    case 'clerk':
      return createClerkAuth(import.meta.env.VITE_CLERK_PUBLISHABLE_KEY)
    case 'dev':
      return createDevAuth()
    default:
      return createNoneAuth()
  }
}
