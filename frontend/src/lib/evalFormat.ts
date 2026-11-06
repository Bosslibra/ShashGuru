import type { Score } from '@/types/api'

/** Engine scores are relative to the side to move: flip them to get White's point of view. */
export function toWhitePov(score: Score, whiteToMove: boolean): Score {
  if (whiteToMove) return score
  return {
    cp: score.cp === null ? null : -score.cp,
    mate: score.mate === null ? null : -score.mate,
  }
}

/** "+0.3", "-1.2", "M+3", "M-2". Always from White's point of view. */
export function formatScore(score: Score | null | undefined, whiteToMove: boolean): string {
  if (!score) return ''
  const white = toWhitePov(score, whiteToMove)
  if (white.mate !== null) return `M${white.mate >= 0 ? '+' : ''}${white.mate}`
  if (white.cp !== null) {
    const pawns = white.cp / 100
    return `${pawns >= 0 ? '+' : ''}${pawns.toFixed(1)}`
  }
  return ''
}

/** Position of the evaluation bar: percentage (0-100) of the bar filled by White. */
export function scoreToPercent(
  score: Score | null | undefined,
  whiteToMove: boolean,
  winprob: number | null = null,
): number {
  if (!score) return 50
  const white = toWhitePov(score, whiteToMove)
  if (white.mate !== null) return white.mate > 0 ? 100 : 0
  if (white.cp !== null) {
    const clamped = Math.max(-1000, Math.min(1000, white.cp))
    return Math.max(5, Math.min(95, 50 + clamped / 20))
  }
  if (winprob !== null) return whiteToMove ? winprob : 100 - winprob
  return 50
}

export type EvalClass =
  | 'neutral'
  | 'white-winning'
  | 'black-winning'
  | 'white-better'
  | 'white-slightly-better'
  | 'black-better'
  | 'black-slightly-better'

export function evalClass(score: Score | null | undefined, whiteToMove: boolean): EvalClass {
  if (!score) return 'neutral'
  const white = toWhitePov(score, whiteToMove)
  if (white.mate !== null) return white.mate > 0 ? 'white-winning' : 'black-winning'
  const cp = white.cp ?? 0
  if (cp > 100) return 'white-better'
  if (cp > 50) return 'white-slightly-better'
  if (cp < -100) return 'black-better'
  if (cp < -50) return 'black-slightly-better'
  return 'neutral'
}

export function isWhiteToMove(fen: string): boolean {
  return fen.split(' ')[1] !== 'b'
}
