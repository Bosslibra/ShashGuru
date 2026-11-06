import type {
  AppConfig,
  ChatMessage,
  Evaluation,
  KeyOut,
  LlmChoice,
  Me,
  ModelCatalog,
  NewKey,
  Offer,
  StreamEvent,
  StyleInfo,
  UsagePage,
} from '@/types/api'
import { LOCAL_BASE, REMOTE_BASE, deleteRequest, postJson, request } from '@/api/http'
import { readNdjson } from '@/api/ndjson'

const V1 = '/api/v1'

/** Only the defined LLM-selection fields (the self-hosted backend ignores them anyway). */
function llmChoice({ source, key_id, model }: LlmChoice): LlmChoice {
  const choice: LlmChoice = {}
  if (source) choice.source = source
  if (key_id !== undefined) choice.key_id = key_id
  if (model) choice.model = model
  return choice
}

export interface EvaluateParams {
  fen: string
  depth: number
  lines: number
  signal?: AbortSignal
}

export async function evaluate({ fen, depth, lines, signal }: EvaluateParams): Promise<Evaluation> {
  const response = await postJson(`${REMOTE_BASE}${V1}/evaluations`, { fen, depth, lines }, signal)
  return response.json()
}

export async function getStyles(base: string = REMOTE_BASE): Promise<StyleInfo[]> {
  const response = await request(`${base}${V1}/styles`)
  return response.json()
}

/** Is a ShashGuru backend (with the LLM endpoints) reachable on this machine? */
export async function isLocalBackendAvailable(timeoutMs = 500): Promise<boolean> {
  try {
    const response = await fetch(`${LOCAL_BASE}/health`, { signal: AbortSignal.timeout(timeoutMs) })
    return response.ok
  } catch {
    return false
  }
}

export interface AnalyzeParams extends LlmChoice {
  fen: string
  depth: number
  style: string
  base?: string
  signal?: AbortSignal
}

/** Engine analysis explained by the LLM. Yields `context`, `token`*, `usage`, then `done` or `error`. */
export async function* streamAnalysis(p: AnalyzeParams): AsyncGenerator<StreamEvent> {
  const response = await postJson(
    `${p.base ?? REMOTE_BASE}${V1}/analyses`,
    { fen: p.fen, depth: p.depth, style: p.style, ...llmChoice(p) },
    p.signal,
  )
  yield* readNdjson<StreamEvent>(response)
}

export interface ChatParams extends LlmChoice {
  /** Server-side analysis the conversation refers to (the context is no longer sent by the client). */
  analysisId?: string
  messages: ChatMessage[]
  style: string
  base?: string
  signal?: AbortSignal
}

/** Follow-up question. The last message must be the user's question. */
export async function* streamChat(p: ChatParams): AsyncGenerator<StreamEvent> {
  const response = await postJson(
    `${p.base ?? REMOTE_BASE}${V1}/chat`,
    { analysis_id: p.analysisId, messages: p.messages, style: p.style, ...llmChoice(p) },
    p.signal,
  )
  yield* readNdjson<StreamEvent>(response)
}

// ----- SaaS endpoints (remote backend only) -------------------------------------------------

const api = (path: string) => `${REMOTE_BASE}${V1}${path}`
const getJson = async <T>(path: string): Promise<T> => (await request(api(path))).json()
const postBody = async <T>(path: string, body: unknown = {}): Promise<T> => (await postJson(api(path), body)).json()

export const getConfig = () => getJson<AppConfig>('/config')
export const getMe = () => getJson<Me>('/me')
export const getUsage = (limit = 20, offset = 0) => getJson<UsagePage>(`/me/usage?limit=${limit}&offset=${offset}`)
export const deleteAccount = async (): Promise<void> => void (await deleteRequest(api('/me')))
export async function exportData(): Promise<Blob> {
  return (await request(api('/me/export'))).blob()
}
export const getModels = () => getJson<ModelCatalog>('/models')
export const getOffers = () => getJson<Offer[]>('/offers')
export const getKeys = () => getJson<KeyOut[]>('/keys')
export const createKey = (key: NewKey) => postBody<KeyOut>('/keys', key)
export const deleteKey = async (id: number): Promise<void> => void (await deleteRequest(api(`/keys/${id}`)))
export const testKey = (id: number) => postBody<{ ok: boolean; message?: string }>(`/keys/${id}/test`)
export const createCheckout = (offerId: string) => postBody<{ url: string }>('/billing/checkout', { offer_id: offerId })
export const createPortal = () => postBody<{ url: string }>('/billing/portal')
