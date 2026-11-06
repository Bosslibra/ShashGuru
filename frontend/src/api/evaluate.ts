import { evaluate } from '@/api/backend'
import type { Evaluation } from '@/types/api'

const TTL_MS = 5 * 60 * 1000
const MAX_ENTRIES = 300

const cache = new Map<string, { at: number; result: Evaluation }>()

/** `evaluate` with a small in-memory cache (positions are revisited a lot while navigating a game). */
export async function evaluateCached(
  fen: string,
  depth: number,
  lines: number,
  signal?: AbortSignal,
): Promise<Evaluation> {
  const key = `${fen}|${depth}|${lines}`
  const hit = cache.get(key)
  if (hit && Date.now() - hit.at < TTL_MS) return hit.result

  const result = await evaluate({ fen, depth, lines, signal })
  cache.delete(key)
  cache.set(key, { at: Date.now(), result })
  if (cache.size > MAX_ENTRIES) cache.delete(cache.keys().next().value as string)
  return result
}

export function clearEvaluationCache(): void {
  cache.clear()
}
