import { describe, expect, it } from 'vitest'
import { evalClass, formatScore, scoreToPercent, toWhitePov } from './evalFormat'

const cp = (n: number) => ({ cp: n, mate: null })
const mate = (n: number) => ({ cp: null, mate: n })

describe('evalFormat', () => {
  it('flips scores to White point of view', () => {
    expect(toWhitePov(cp(30), false)).toEqual({ cp: -30, mate: null })
    expect(toWhitePov(mate(3), true)).toEqual(mate(3))
  })

  it('formats centipawns and mates', () => {
    expect(formatScore(cp(34), true)).toBe('+0.3')
    expect(formatScore(cp(34), false)).toBe('-0.3')
    expect(formatScore(cp(0), false)).toBe('+0.0')
    expect(formatScore(mate(3), true)).toBe('M+3')
    expect(formatScore(mate(3), false)).toBe('M-3')
    expect(formatScore(null, true)).toBe('')
  })

  it('maps scores to bar percentage', () => {
    expect(scoreToPercent(cp(0), true)).toBe(50)
    expect(scoreToPercent(cp(100), true)).toBe(55)
    expect(scoreToPercent(cp(100), false)).toBe(45)
    expect(scoreToPercent(cp(5000), true)).toBe(95)
    expect(scoreToPercent(mate(2), false)).toBe(0)
    expect(scoreToPercent(null, true)).toBe(50)
    expect(scoreToPercent({ cp: null, mate: null }, false, 70)).toBe(30)
  })

  it('classifies evaluations', () => {
    expect(evalClass(cp(20), true)).toBe('neutral')
    expect(evalClass(cp(80), true)).toBe('white-slightly-better')
    expect(evalClass(cp(80), false)).toBe('black-slightly-better')
    expect(evalClass(cp(150), true)).toBe('white-better')
    expect(evalClass(mate(1), false)).toBe('black-winning')
  })
})
