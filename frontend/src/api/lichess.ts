import { stripComments } from '@/lib/pgn'

const LICHESS = 'https://lichess.org/api/broadcast'

export async function fetchBroadcast(eventId: string): Promise<{ defaultRoundId: string }> {
  const res = await fetch(`${LICHESS}/${encodeURIComponent(eventId)}`)
  if (!res.ok) throw new Error('Event not found')
  const data = await res.json()
  const roundId = data.defaultRoundId || data.rounds?.[0]?.id || ''
  return { defaultRoundId: roundId }
}

/** All games of a broadcast round, as one PGN text with comments removed. */
export async function fetchRoundPgn(roundId: string): Promise<string> {
  const res = await fetch(`${LICHESS}/round/${encodeURIComponent(roundId)}.pgn`)
  if (!res.ok) throw new Error('Could not fetch PGN')
  return stripComments(await res.text())
}
