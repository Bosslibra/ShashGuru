import { describe, expect, it } from 'vitest'
import { displayResult, parseBroadcastInput, parseHeaders, splitPgns, stripComments, stripHeaders } from './pgn'

const PGN = `[Event "Test"]
[White "A"]
[Black ""]
[Result "1/2-1/2"]

1. e4 e5 1/2-1/2`

describe('pgn', () => {
  it('parses headers, including empty values', () => {
    expect(parseHeaders(PGN)).toEqual({ Event: 'Test', White: 'A', Black: '', Result: '1/2-1/2' })
  })

  it('strips headers and comments', () => {
    expect(stripHeaders(PGN)).toBe('1. e4 e5 1/2-1/2')
    expect(stripComments('1. e4 {[%clk 0:01:00]} $1 e5')).toBe('1. e4   e5')
  })

  it('splits multi-game exports', () => {
    const games = splitPgns(`${PGN}\n\n[Event "Second"]\n[White "C"]\n\n1. d4 *\n`)
    expect(games).toHaveLength(2)
    expect(games[1]).toContain('[Event "Second"]')
  })

  it('formats results', () => {
    expect(displayResult('*')).toBe('Ongoing')
    expect(displayResult('1/2-1/2')).toBe('½-½')
    expect(displayResult(undefined)).toBe('-')
    expect(displayResult('1-0')).toBe('1-0')
  })

  it('parses broadcast URLs and ids', () => {
    expect(parseBroadcastInput('https://lichess.org/broadcast/knight-invitational/sO7W9Jje/eJLgkG7n#x')).toEqual({
      eventId: 'sO7W9Jje',
      roundId: 'eJLgkG7n',
    })
    expect(parseBroadcastInput('https://lichess.org/broadcast/round/eJLgkG7n')).toEqual({ roundId: 'eJLgkG7n' })
    expect(parseBroadcastInput(' eJLgkG7n ')).toEqual({ roundId: 'eJLgkG7n' })
    expect(parseBroadcastInput('https://lichess.org/broadcast/only-a-slug')).toBeNull()
    expect(parseBroadcastInput('')).toBeNull()
  })
})
