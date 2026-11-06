import { Chess } from 'chess.js'

export const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

export function isValidFen(fen: string): boolean {
  try {
    new Chess(fen.trim())
    return true
  } catch {
    return false
  }
}
