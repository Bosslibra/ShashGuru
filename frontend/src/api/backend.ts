import type { ChatMessage, Evaluation, StreamEvent, StyleInfo } from '@/types/api'
import { LOCAL_BASE, REMOTE_BASE, postJson, request } from '@/api/http'
import { readNdjson } from '@/api/ndjson'

const V1 = '/api/v1'

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

export interface AnalyzeParams {
  fen: string
  depth: number
  style: string
  base?: string
  signal?: AbortSignal
}

/** Engine analysis explained by the LLM. Yields `context`, `token`*, then `done` or `error`. */
export async function* streamAnalysis(p: AnalyzeParams): AsyncGenerator<StreamEvent> {
  const response = await postJson(
    `${p.base ?? REMOTE_BASE}${V1}/analyses`,
    { fen: p.fen, depth: p.depth, style: p.style },
    p.signal,
  )
  yield* readNdjson<StreamEvent>(response)
}

export interface ChatParams {
  messages: ChatMessage[]
  style: string
  base?: string
  signal?: AbortSignal
}

/** Follow-up question. The last message must be the user's question. */
export async function* streamChat(p: ChatParams): AsyncGenerator<StreamEvent> {
  const response = await postJson(
    `${p.base ?? REMOTE_BASE}${V1}/chat`,
    { messages: p.messages, style: p.style },
    p.signal,
  )
  yield* readNdjson<StreamEvent>(response)
}
