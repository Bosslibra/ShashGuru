/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Lichess broadcast round id shown as "Featured Event" on the LIVE page. */
  readonly VITE_FEATURED_EVENT_ID?: string
  /** Auth adapter: none (default, self-hosted) | dev (development only) | clerk. */
  readonly VITE_AUTH_PROVIDER?: string
  readonly VITE_CLERK_PUBLISHABLE_KEY?: string
}
