export type PgnHeaders = Record<string, string>

const HEADER_RE = /\[(\w+)\s+"((?:[^"\\]|\\.)*)"\]/g

export function parseHeaders(pgn: string): PgnHeaders {
  const headers: PgnHeaders = {}
  for (const m of pgn.matchAll(HEADER_RE)) headers[m[1]] = m[2]
  return headers
}

/** Move text only: headers removed, whitespace collapsed. */
export function stripHeaders(pgn: string): string {
  return pgn.replace(HEADER_RE, '').replace(/\s+/g, ' ').trim()
}

/** Remove `{comments}` and `$NAG`s (e.g. clock annotations in Lichess broadcasts). */
export function stripComments(pgn: string): string {
  return pgn
    .replace(/\{[^}]*\}/g, '')
    .replace(/\$\d+/g, '')
    .trim()
}

/** Split a multi-game PGN export into single games. */
export function splitPgns(text: string): string[] {
  return text
    .trim()
    .split(/\n\s*\n(?=\[Event )/)
    .filter((g) => g.trim().length > 0)
}

export function displayResult(result: string | undefined): string {
  if (!result) return '-'
  if (result === '*') return 'Ongoing'
  if (result === '1/2-1/2') return '½-½'
  return result
}

/** Extract `{eventId, roundId}` from a Lichess broadcast URL, or a bare round id. */
export function parseBroadcastInput(input: string): { eventId?: string; roundId: string } | null {
  const text = input.trim()
  if (!text) return null
  const url = text.match(/lichess\.org\/broadcast\/(?:[^/]+\/)?([A-Za-z0-9]{8})\/(?:[^/]+\/)?([A-Za-z0-9]{8})/)
  if (url) return { eventId: url[1], roundId: url[2] }
  const round = text.match(/lichess\.org\/broadcast\/round\/([A-Za-z0-9]{8})/)
  if (round) return { roundId: round[1] }
  if (/^[A-Za-z0-9]{8}$/.test(text)) return { roundId: text }
  return null
}
