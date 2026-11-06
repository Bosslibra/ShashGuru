<script setup lang="ts">
import { computed, reactive, ref, shallowRef, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { TheChessboard, type BoardApi, type PieceColor } from 'vue3-chessboard'
import 'vue3-chessboard/style.css'
import type { Move, Square } from 'chess.js'
import EvaluationBar from './EvaluationBar.vue'
import FenPgnInputs from './FenPgnInputs.vue'
import SettingsModal from './SettingsModal.vue'
import { useEvaluationStore } from '@/stores/evaluation'
import { useGameStore } from '@/stores/game'
import { useSettingsStore } from '@/stores/settings'

const game = useGameStore()
const settings = useSettingsStore()
const evaluation = useEvaluationStore()
const { bestMove } = storeToRefs(evaluation)

const boardAPI = shallowRef<BoardApi | null>(null)
const boardOrientation = ref<'white' | 'black'>('white')
const showSettings = ref(false)

const side = computed(() => game.currentFen.split(' ')[1])

const boardConfig = reactive({
  fen: game.currentFen,
  coordinates: true,
  autoCastle: true,
  highlight: {
    lastMove: true,
    check: true,
  },
  events: {
    select: () => drawBestMoveArrow(),
  },
})

// --- Board <-> game synchronisation ---

/** Show the game's current position on the board (only if it differs, to keep move highlights). */
function syncBoard() {
  const board = boardAPI.value
  if (board && board.getFen() !== game.currentFen) board.setPosition(game.currentFen)
}

function drawBestMoveArrow() {
  if (!settings.showBestMove || !bestMove.value) return
  boardAPI.value?.drawMove(
    bestMove.value.slice(0, 2) as Square,
    bestMove.value.slice(2, 4) as Square,
    'paleBlue',
  )
}

watch(() => game.currentFen, syncBoard)
watch([() => game.currentFen, bestMove, () => settings.showBestMove], () => nextTick(drawBestMoveArrow))

// --- Event handlers ---

function handleBoardCreated(api: BoardApi) {
  boardAPI.value = api
  syncBoard()
  drawBestMoveArrow()
}

function handleMove(move: Move) {
  game.play(move.san)
}

function handleCheckmate(mated: PieceColor) {
  alert(mated === 'white' ? 'Black wins by checkmate!' : 'White wins by checkmate!')
}

function toggleOrientation() {
  boardAPI.value?.toggleOrientation()
  boardOrientation.value = boardOrientation.value === 'white' ? 'black' : 'white'
}

function resetBoard() {
  game.reset()
  boardAPI.value?.resetBoard()
}
</script>

<template>
  <div class="chessboard-container" >
    <div class="board-section w-100">
      <div class="d-flex">
        <section role="region" aria-label="Board Controls" class="board-controls">
          <button type="button" @click="toggleOrientation" class="btn btn-sm m-1">
            Flip Board
          </button>
          <button type="button" @click="resetBoard" class="btn btn-sm m-1">
            Starting Position
          </button>
          <button type="button" @click="showSettings = !showSettings" class="btn btn-sm m-1">
            Settings
          </button>
        </section>
        <div v-if="side === 'w'" class="text-white p-2">White to play</div>
        <div v-else-if="side === 'b'" class="text-white p-2">Black to play</div>
      </div>

      <div class="board-with-eval">
        <div class="evaluation-panel">
          <EvaluationBar :board-orientation="boardOrientation" />
        </div>
        <div class="chessboard-container-wrapper">
          <TheChessboard
            :board-config="boardConfig"
            @board-created="handleBoardCreated"
            @checkmate="handleCheckmate"
            @move="handleMove"
            style="max-height: 70vh; max-width: 70vmin; min-width: 50vmin; "
            class=""
          />
        </div>
      </div>

      <FenPgnInputs />
    </div>

    <SettingsModal v-if="showSettings" @close="showSettings = false" />
  </div>
</template>

<style scoped>
.chessboard-container {
  width: 100%;
}

.board-section {
  display: flex;
  flex-direction: column;
}

.board-with-eval {
  display: flex;
  align-items: stretch;
  gap: 15px;
  height: 100%;
}

.evaluation-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.chessboard-container-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
}

.board-controls {
  margin-bottom: 1rem;
}

button.btn {
  background: #262421;
  color: #f2f2f2;
  border: none;
  font-weight: 600;
  border-radius: 6px;
  padding: 0.5em 1.2em;
  transition: background 0.2s, color 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}

button.btn:hover {
  background: #cdd26a;
  color: #232323;
  box-shadow: 0 4px 16px rgba(205, 210, 106, 0.15);
}
</style>
