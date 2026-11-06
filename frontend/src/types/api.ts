// DTOs mirroring backend/app/schemas.py

export interface Score {
  /** Centipawns, from the point of view of the side to move. */
  cp: number | null
  /** Moves to mate, from the point of view of the side to move (negative = being mated). */
  mate: number | null
}

export interface Wdl {
  w: number
  d: number
  l: number
}

export interface EngineLine {
  rank: number
  move: string
  /** Principal variation in UCI notation. */
  pv: string[]
  score: Score
  wdl: Wdl | null
  /** Win probability 0-100 for the side to move. */
  winprob: number | null
  depth: number
}

export type PositionStatus = 'ok' | 'checkmate' | 'stalemate' | 'draw'
export type Side = 'white' | 'black'

export interface Evaluation {
  fen: string
  sideToMove: Side
  status: PositionStatus
  depth: number
  lines: EngineLine[]
}

export interface StyleInfo {
  value: string
  label: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface Balance {
  subscription: number
  purchased: number
  total: number
}

export type StreamEvent =
  /** `analysis_id` identifies the analysis server-side; `prompt` is only sent by legacy backends. */
  | { type: 'context'; analysis_id?: string; prompt?: string }
  | { type: 'token'; text: string }
  | { type: 'usage'; input_tokens: number; output_tokens: number; credits: number; balance: Balance | null }
  | { type: 'done' }
  | { type: 'error'; message: string }

// ----- SaaS: config, account, billing, keys -------------------------------------------------

export interface AppConfig {
  deployment_mode: 'saas' | 'selfhosted'
  billing_enabled: boolean
  byok_enabled: boolean
  engine_anon_max_depth: number
}

export interface SubscriptionInfo {
  status: string
  current_period_end: string | null
  offer_id: string | null
}

export interface UsageMonth {
  requests: number
  input_tokens: number
  output_tokens: number
  credits: number
}

export interface Me {
  id: number
  email: string | null
  is_admin: boolean
  plan: string | null
  subscription: SubscriptionInfo | null
  balance: Balance
  usage_month: UsageMonth
}

export interface UsageItem {
  id: number
  created_at: string
  source: 'managed' | 'byok'
  provider: string
  model: string
  input_tokens: number
  output_tokens: number
  credits_charged: number
  status: string
}

export interface UsagePage {
  items: UsageItem[]
  total: number
}

export type Provider = 'openai' | 'anthropic' | 'openrouter' | 'custom'
export const PROVIDERS: Provider[] = ['openai', 'anthropic', 'openrouter', 'custom']

export interface ManagedModel {
  id: string
  label: string
  provider: string
  est_credits: number
}

export interface ModelCatalog {
  managed: ManagedModel[]
  byok_suggestions: Record<Provider, string[]>
  default_managed: string | null
}

export interface KeyOut {
  id: number
  provider: Provider
  label: string
  hint: string
  base_url: string | null
  created_at: string
  last_used_at: string | null
}

export interface NewKey {
  provider: Provider
  api_key: string
  label?: string
  base_url?: string
}

export interface Offer {
  id: string
  kind: 'subscription' | 'topup'
  name: string
  credits: number
  price: number
  currency: string
}

export type LlmSource = 'managed' | 'byok'

export interface LlmChoice {
  source?: LlmSource
  key_id?: number
  model?: string
}
