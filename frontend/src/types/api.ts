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

export type StreamEvent =
  | { type: 'context'; prompt: string }
  | { type: 'token'; text: string }
  | { type: 'done' }
  | { type: 'error'; message: string }
