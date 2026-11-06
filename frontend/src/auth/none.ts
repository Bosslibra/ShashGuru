import { Emitter, type AuthClient } from './types'

/** No authentication (self-hosted deployments). */
export function createNoneAuth(): AuthClient {
  const emitter = new Emitter()
  return {
    name: 'none',
    init: async () => {},
    getUser: () => null,
    onChange: (l) => emitter.subscribe(l),
    getToken: async () => null,
    signIn: async () => {},
    signUp: async () => {},
    signOut: async () => {},
  }
}
