<script setup lang="ts">
import { computed, reactive, ref, shallowRef, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useTranslation } from 'i18next-vue'
import { TheChessboard, type BoardApi, type PieceColor } from 'vue3-chessboard'
import 'vue3-chessboard/style.css'
import type { Move, Square } from 'chess.js'
import { ArrowUpDown, RotateCcw, SlidersHorizontal } from '@lucide/vue'
import EvaluationBar from './EvaluationBar.vue'
import FenPgnInputs from './FenPgnInputs.vue'
import SettingsDialog from './SettingsDialog.vue'
import { Button } from '@/components/ui/button'
import { useEvaluationStore } from '@/stores/evaluation'
import { useGameStore } from '@/stores/game'
import { useSettingsStore } from '@/stores/settings'
import { useToastStore } from '@/stores/toast'

const { t } = useTranslation()
const toast = useToastStore()
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
  toast.success(mated === 'white' ? t('board.blackWins') : t('board.whiteWins'), 8000)
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
  <div class="chessboard-container w-full">
    <div class="board-section flex w-full flex-col">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
        <section role="region" :aria-label="t('board.controls')" class="board-controls flex flex-wrap gap-2">
          <Button variant="outline" size="sm" @click="toggleOrientation">
            <ArrowUpDown aria-hidden="true" />{{ t('board.flip') }}
          </Button>
          <Button variant="outline" size="sm" @click="resetBoard">
            <RotateCcw aria-hidden="true" />{{ t('board.start') }}
          </Button>
          <Button variant="outline" size="sm" @click="showSettings = true">
            <SlidersHorizontal aria-hidden="true" />{{ t('board.settings') }}
          </Button>
        </section>

        <!-- Side to move: a small square in the colour of the side, then the text -->
        <div v-if="side" class="flex items-center gap-2 text-sm font-medium text-foreground" role="status">
          <span
            class="size-3.5 rounded-[3px] border"
            :class="side === 'w' ? 'border-cream bg-cream' : 'border-muted-foreground bg-black'"
            aria-hidden="true"
          ></span>
          {{ side === 'w' ? t('board.whiteToPlay') : t('board.blackToPlay') }}
        </div>
      </div>

      <div
        class="board-with-eval mx-auto flex w-full items-stretch gap-2 max-w-[calc(min(70vh,100vmin)_+_60px)] sm:gap-3"
      >
        <div class="evaluation-panel flex shrink-0 flex-col items-center">
          <EvaluationBar :board-orientation="boardOrientation" />
        </div>
        <div class="chessboard-container-wrapper relative flex min-w-0 flex-1 flex-col">
          <div class="overflow-hidden rounded-(--radius) ring-1 ring-border shadow-(--panel-shadow)">
            <TheChessboard
              :board-config="boardConfig"
              class="w-full! max-w-none!"
              @board-created="handleBoardCreated"
              @checkmate="handleCheckmate"
              @move="handleMove"
            />
          </div>
        </div>
      </div>

      <FenPgnInputs />
    </div>

    <SettingsDialog v-model:open="showSettings" />
  </div>
</template>
