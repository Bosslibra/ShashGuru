import { describe, expect, it } from 'vitest'
import { MoveTree } from './moveTree'

describe('MoveTree', () => {
  it('builds a line and stops at the first illegal move', () => {
    const { tree, last } = MoveTree.fromSans(['e4', 'e5', 'Nf3', 'Qxx9', 'Nc6'])
    expect(tree.mainLineNodes().map((n) => n.move)).toEqual(['e4', 'e5', 'Nf3'])
    expect(last.move).toBe('Nf3')
    expect(last.getPath()).toEqual([0, 0, 0])
  })

  it('play() reuses an existing child and otherwise adds a variation', () => {
    const { tree } = MoveTree.fromSans(['e4', 'e5'])
    const e4 = tree.root.mainLine!
    expect(tree.play(tree.root, 'e4')).toBe(e4)
    const c5 = tree.play(e4, 'c5')!
    expect(e4.children).toHaveLength(2)
    expect(e4.mainLine!.move).toBe('e5')
    expect(c5.isOnMainLinePath()).toBe(false)
    expect(tree.play(e4, 'Ke4')).toBeNull()
  })

  it('promote() makes a whole variation the main line', () => {
    const { tree } = MoveTree.fromSans(['e4', 'e5'])
    const e4 = tree.root.mainLine!
    const c5 = tree.play(e4, 'c5')!
    const nf3 = tree.play(c5, 'Nf3')!
    expect(tree.promote(nf3)).toBe(true)
    expect(tree.mainLineNodes().map((n) => n.move)).toEqual(['e4', 'c5', 'Nf3'])
    expect(nf3.isOnMainLinePath()).toBe(true)
    expect(tree.promote(nf3)).toBe(false) // already main line
  })

  it('remove() drops the subtree and falls back to the next child', () => {
    const { tree } = MoveTree.fromSans(['e4', 'e5'])
    const e4 = tree.root.mainLine!
    const e5 = e4.mainLine!
    const c5 = tree.play(e4, 'c5')!
    expect(tree.remove(e5)).toBe(e4)
    expect(e4.mainLine).toBe(c5)
    expect(tree.remove(c5)).toBe(e4)
    expect(e4.mainLine).toBeNull()
    expect(tree.remove(tree.root)).toBeNull()
  })

  it('isInSubtreeOf', () => {
    const { tree, last } = MoveTree.fromSans(['e4', 'e5', 'Nf3'])
    expect(last.isInSubtreeOf(tree.root.mainLine!)).toBe(true)
    expect(tree.root.mainLine!.isInSubtreeOf(last)).toBe(false)
  })

  it('supports a custom root position', () => {
    const fen = '4k3/8/8/8/8/8/4P3/4K3 w - - 0 1'
    const { tree, last } = MoveTree.fromSans(['e4'], fen)
    expect(tree.root.fen).toBe(fen)
    expect(last.fen.startsWith('4k3/8/8/8/4P3/8/8/4K3 b')).toBe(true)
  })
})
