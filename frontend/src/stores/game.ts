import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import { Chess } from 'chess.js'
import { evaluateCached } from '@/api/evaluate'
import { STARTING_FEN, isValidFen } from '@/lib/fen'
import { MoveNode, MoveTree } from '@/lib/moveTree'
import { displayResult, parseHeaders, stripHeaders, type PgnHeaders } from '@/lib/pgn'
import { useSettingsStore } from '@/stores/settings'

const EVALUATION_CONCURRENCY = 3

/**
 * The game being studied: its move tree (main line + variations), the current position,
 * and the PGN metadata. Tree nodes are plain (non-reactive) objects; `version` is bumped on
 * every mutation so that computeds and components depending on the tree re-run.
 */
export const useGameStore = defineStore('game', () => {
  const tree = shallowRef(new MoveTree())
  const currentNode = shallowRef<MoveNode>(tree.value.root)
  const version = ref(0)
  const headers = ref<PgnHeaders>({})
  /** Text of the PGN input box, kept here so it survives navigation between pages. */
  const pgnText = ref('')
  const analysisMode = ref(false)
  const loadingEvaluations = ref(false)

  const touch = () => version.value++

  const currentFen = computed(() => currentNode.value.fen)
  const root = computed(() => (version.value, tree.value.root))
  const hasMoves = computed(() => (version.value, tree.value.root.children.length > 0))
  const mainLine = computed(() => (version.value, tree.value.mainLineNodes()))
  const selectedPath = computed(() => (version.value, currentNode.value.getPath()))
  const canGoBack = computed(() => currentNode.value.parent !== null)
  const canGoForward = computed(() => (version.value, currentNode.value.mainLine !== null))

  const hasPlayerInfo = computed(() => Boolean(headers.value.White && headers.value.Black))
  const whitePlayer = computed(() => headers.value.White ?? '')
  const blackPlayer = computed(() => headers.value.Black ?? '')
  const gameResult = computed(() => displayResult(headers.value.Result))

  // ----- loading ---------------------------------------------------------

  function setTree(next: MoveTree, at: MoveNode = next.root) {
    tree.value = next
    currentNode.value = at
    touch()
  }

  /** Throws an Error with a user-presentable message if the PGN is invalid or empty. */
  function loadPgn(raw: string) {
    const text = raw.trim()
    const chess = new Chess()
    try {
      chess.loadPgn(text)
    } catch {
      try {
        chess.loadPgn(stripHeaders(text))
      } catch {
        throw new Error('PGN is invalid or empty.')
      }
    }
    const sans = chess.history()
    if (sans.length === 0) throw new Error('PGN is invalid or empty.')

    const parsed = parseHeaders(text)
    const rootFen = parsed.SetUp === '1' && parsed.FEN ? parsed.FEN : STARTING_FEN
    // The board shows the start of the game, like opening a game in an analysis board.
    setTree(MoveTree.fromSans(sans, rootFen).tree)
    headers.value = parsed
    pgnText.value = text
  }

  /** Start a fresh analysis from an arbitrary position. Returns false if the FEN is invalid. */
  function loadFen(fen: string): boolean {
    const value = fen.trim()
    if (!isValidFen(value)) return false
    if (value === currentNode.value.fen) return true
    setTree(new MoveTree(value))
    headers.value = {}
    pgnText.value = ''
    return true
  }

  function reset() {
    setTree(new MoveTree())
    headers.value = {}
    pgnText.value = ''
  }

  // ----- navigation ------------------------------------------------------

  function goTo(node: MoveNode) {
    currentNode.value = node
  }

  const goToStart = () => goTo(tree.value.root)

  function back() {
    if (currentNode.value.parent) goTo(currentNode.value.parent)
  }

  function forward() {
    if (currentNode.value.mainLine) goTo(currentNode.value.mainLine)
  }

  function goToEnd() {
    const line = tree.value.mainLineNodes()
    if (line.length) goTo(line[line.length - 1])
  }

  function goToMainLineIndex(index: number) {
    if (index === -1) return goToStart()
    const node = tree.value.mainLineNodes()[index]
    if (node) goTo(node)
  }

  // ----- editing ---------------------------------------------------------

  /** Play a move (SAN) from the current position. Returns false if it is illegal. */
  function play(move: string): boolean {
    const node = tree.value.play(currentNode.value, move)
    if (!node) return false
    currentNode.value = node
    touch()
    return true
  }

  function promote(node: MoveNode) {
    if (tree.value.promote(node)) touch()
  }

  function remove(node: MoveNode) {
    const fallback = tree.value.remove(node)
    if (!fallback) return
    if (currentNode.value.isInSubtreeOf(node)) currentNode.value = fallback
    touch()
  }

  function setShashinType(node: MoveNode, type: string | null) {
    node.shashinType = type
    touch()
  }

  function setMoveEvaluation(node: MoveNode, type: string | null) {
    node.moveEvaluation = type
    touch()
  }

  function toggleAnalysisMode() {
    analysisMode.value = !analysisMode.value
  }

  // ----- per-move engine evaluations --------------------------------------

  /** Evaluate every position of the main line that has no evaluation yet. */
  async function fetchMainLineEvaluations() {
    const settings = useSettingsStore()
    const pending = tree.value.mainLineNodes().filter((n) => !n.evaluation)
    if (!pending.length || loadingEvaluations.value) return
    loadingEvaluations.value = true
    try {
      const queue = [...pending]
      const worker = async () => {
        for (let node = queue.shift(); node; node = queue.shift()) {
          try {
            node.evaluation = await evaluateCached(node.fen, settings.depth, settings.lines)
            touch()
          } catch (error) {
            console.error(`Error fetching evaluation for ${node.move}:`, error)
          }
        }
      }
      await Promise.all(Array.from({ length: EVALUATION_CONCURRENCY }, worker))
    } finally {
      loadingEvaluations.value = false
    }
  }

  return {
    // state
    currentNode, headers, pgnText, analysisMode, loadingEvaluations, version,
    // derived
    root, currentFen, hasMoves, mainLine, selectedPath, canGoBack, canGoForward,
    hasPlayerInfo, whitePlayer, blackPlayer, gameResult,
    // actions
    loadPgn, loadFen, reset, goTo, goToStart, back, forward, goToEnd, goToMainLineIndex,
    play, promote, remove, setShashinType, setMoveEvaluation, toggleAnalysisMode,
    fetchMainLineEvaluations,
  }
})
