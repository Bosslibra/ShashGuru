import { Chess } from 'chess.js'
import type { Evaluation } from '@/types/api'
import { STARTING_FEN } from '@/lib/fen'

let nextId = 0

/** A position reached by `move` (SAN). The root has `move === null`. */
export class MoveNode {
  readonly id = `n${++nextId}`
  children: MoveNode[] = []
  /** The continuation shown in the main line; the other children are variations. */
  mainLine: MoveNode | null = null
  evaluation?: Evaluation
  shashinType?: string | null
  moveEvaluation?: string | null

  constructor(
    readonly move: string | null,
    readonly fen: string,
    readonly parent: MoveNode | null = null,
  ) {}

  addChild(move: string, fen: string): MoveNode {
    const child = new MoveNode(move, fen, this)
    this.children.push(child)
    if (!this.mainLine) this.mainLine = child
    return child
  }

  /** This node followed by its ancestors up to the root. */
  *lineage(): Generator<MoveNode> {
    // eslint-disable-next-line @typescript-eslint/no-this-alias
    for (let node: MoveNode | null = this; node; node = node.parent) yield node
  }

  /** Indices in `children` from the root down to this node. */
  getPath(): number[] {
    const path: number[] = []
    for (const node of this.lineage()) {
      if (node.parent) path.unshift(node.parent.children.indexOf(node))
    }
    return path
  }

  get isRoot(): boolean {
    return this.parent === null
  }

  isInSubtreeOf(ancestor: MoveNode): boolean {
    for (const node of this.lineage()) if (node === ancestor) return true
    return false
  }

  /** True when every step from the root to this node follows the main line. */
  isOnMainLinePath(): boolean {
    for (const node of this.lineage()) {
      if (node.parent && node.parent.mainLine !== node) return false
    }
    return true
  }
}

export class MoveTree {
  root: MoveNode

  constructor(rootFen: string = STARTING_FEN) {
    this.root = new MoveNode(null, rootFen)
  }

  /** Build a single-line tree. Stops at the first illegal move. */
  static fromSans(sans: string[], rootFen: string = STARTING_FEN): { tree: MoveTree; last: MoveNode } {
    const tree = new MoveTree(rootFen)
    const chess = new Chess(rootFen)
    let last = tree.root
    for (const san of sans) {
      try {
        const move = chess.move(san)
        last = last.addChild(move.san, chess.fen())
      } catch {
        break
      }
    }
    return { tree, last }
  }

  mainLineNodes(): MoveNode[] {
    const nodes: MoveNode[] = []
    for (let n = this.root.mainLine; n; n = n.mainLine) nodes.push(n)
    return nodes
  }

  /**
   * Play `move` (SAN or UCI-like, as accepted by chess.js) from `from`.
   * Reuses an existing child with the same SAN, otherwise adds a variation.
   * Returns null if the move is illegal.
   */
  play(from: MoveNode, move: string): MoveNode | null {
    const chess = new Chess(from.fen)
    let played
    try {
      played = chess.move(move)
    } catch {
      return null
    }
    const existing = from.children.find((c) => c.move === played.san)
    return existing ?? from.addChild(played.san, chess.fen())
  }

  /** Make the variation containing `node` the main line of the position where it branches off. */
  promote(node: MoveNode): boolean {
    if (!node.parent) return false
    let variationRoot = node
    while (variationRoot.parent && variationRoot.parent.mainLine === variationRoot) {
      variationRoot = variationRoot.parent
    }
    if (!variationRoot.parent) return false // the node is already on the main line
    variationRoot.parent.mainLine = variationRoot
    return true
  }

  /** Remove `node` and everything after it. Returns the node to go back to, or null if nothing changed. */
  remove(node: MoveNode): MoveNode | null {
    const parent = node.parent
    if (!parent) return null
    const index = parent.children.indexOf(node)
    if (index === -1) return null
    parent.children.splice(index, 1)
    if (parent.mainLine === node) parent.mainLine = parent.children[0] ?? null
    return parent
  }
}
