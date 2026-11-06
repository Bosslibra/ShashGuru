<template>
  <section class="engine-lines panel">
    <header class="panel-header">
      <h3 class="panel-label">{{ t('engine.title') }}</h3>
      <span v-if="settings.enabled" class="eval-chip text-lime">{{ t('engine.depth', { depth }) }}</span>
    </header>

    <div class="relative min-h-24">
      <!-- Loading overlay on top of the content -->
      <div v-if="loading" class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2 bg-card/90">
        <Spinner class="size-5 text-lime" />
        <span class="text-sm text-muted-foreground">{{ t('engine.analyzing') }}</span>
      </div>

      <!-- Status when there are no lines to show -->
      <div
        v-if="!loading && displayLines.length === 0"
        class="flex flex-wrap items-center justify-center gap-2 p-(--pad) text-center text-sm"
        :class="settings.enabled && error ? 'text-destructive' : 'text-muted-foreground'"
        :role="settings.enabled && error ? 'alert' : 'status'"
      >
        <Power v-if="!settings.enabled" class="size-4" aria-hidden="true" />
        <CircleAlert v-else-if="error" class="size-4" aria-hidden="true" />
        <Info v-else class="size-4" aria-hidden="true" />
        <span>{{ !settings.enabled ? t('engine.off') : error ? t('engine.failed') : t('engine.noLines') }}</span>
        <Button v-if="settings.enabled && error" variant="outline" size="sm" @click="evaluation.refresh()">
          <RefreshCw aria-hidden="true" />{{ t('common.retry') }}
        </Button>
      </div>

      <ol v-else class="m-0 list-none p-0">
        <li
          v-for="(line, index) in displayLines"
          :key="index"
          class="engine-line grid grid-cols-[1.5rem_4rem_1fr] items-start gap-x-2 border-l-2 px-3 py-2 transition-colors"
          :class="index === 0 ? 'border-lime bg-lime/10' : 'border-transparent hover:bg-accent/50'"
        >
          <span class="num pt-0.5 text-xs text-muted-foreground">{{ index + 1 }}.</span>
          <span class="eval-chip justify-center self-start" :class="EVAL_TEXT[evaluationClass(line)]">
            {{ formatEvaluation(line) }}
          </span>
          <span class="flex flex-wrap items-center gap-1">
            <button
              v-for="(move, moveIndex) in parseMoves(line)"
              :key="moveIndex"
              type="button"
              class="line-move num inline-flex items-center gap-1 rounded-[calc(var(--radius)*0.6)] px-1.5 py-0.5 text-[13px] outline-none transition-colors hover:bg-lime/20 focus-visible:ring-2 focus-visible:ring-ring"
              :class="move.isWhite ? 'bg-white/10 text-foreground' : 'bg-black/30 text-foreground'"
              @click="onMoveClicked(move.san)"
            >
              <span v-if="move.moveNumber" class="text-muted-foreground">{{ move.moveNumber }}.</span>{{ move.san }}
            </button>
          </span>
        </li>
      </ol>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTranslation } from 'i18next-vue'
import { storeToRefs } from 'pinia'
import { Chess } from 'chess.js'
import { CircleAlert, Info, Power, RefreshCw } from '@lucide/vue'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { evalClass as getEvaluationClass, formatScore, isWhiteToMove } from '@/lib/evalFormat'
import { useEvaluationStore } from '@/stores/evaluation'
import { useGameStore } from '@/stores/game'
import { useSettingsStore } from '@/stores/settings'
import type { EngineLine } from '@/types/api'

interface DisplayMove {
  san: string
  uci: string
  isWhite: boolean
  moveNumber: number | null
}

const MAX_DISPLAYED_MOVES = 6

/** Evaluation class -> colour token (the colour coding of the scores). */
const EVAL_TEXT: Record<ReturnType<typeof getEvaluationClass>, string> = {
  'white-winning': 'text-eval-1',
  'white-better': 'text-eval-2',
  'white-slightly-better': 'text-eval-3',
  neutral: 'text-eval-4',
  'black-slightly-better': 'text-eval-5',
  'black-better': 'text-eval-6',
  'black-winning': 'text-eval-7',
}

const { t } = useTranslation()
const game = useGameStore()
const evaluation = useEvaluationStore()
const { lines, current, loading, error } = storeToRefs(evaluation)
const settings = useSettingsStore()

const currentFen = computed(() => game.currentNode.fen)
// Lines belong to the evaluated position; scores are relative to *its* side to move.
const evaluatedFen = computed(() => current.value?.fen ?? currentFen.value)
const whiteToMove = computed(() => isWhiteToMove(evaluatedFen.value))
const depth = computed(() => current.value?.depth || settings.depth)

// Display only the requested number of lines
const displayLines = computed(() => lines.value.slice(0, settings.lines))

function onMoveClicked(move: string) {
  // Only the first line's moves apply to the position on the board.
  game.play(move)
}

// Convert the engine line (UCI) to SAN, starting from the evaluated position
function parseMoves(line: EngineLine): DisplayMove[] {
  const fen = evaluatedFen.value
  if (!line.pv.length || !fen) return []

  const chess = new Chess(fen)
  const fenParts = fen.split(' ')
  let isWhite = fenParts[1] !== 'b'
  let moveNumber = parseInt(fenParts[5]) || 1

  const parsed: DisplayMove[] = []
  for (const uci of line.pv.slice(0, MAX_DISPLAYED_MOVES)) {
    let san = uci
    try {
      san = chess.move({
        from: uci.slice(0, 2),
        to: uci.slice(2, 4),
        promotion: uci.length > 4 ? uci[4] : undefined,
      }).san
    } catch (error) {
      console.warn(`Failed to parse UCI move: ${uci}`, error)
    }
    parsed.push({ san, uci, isWhite, moveNumber: isWhite ? moveNumber : null })
    if (!isWhite) moveNumber++
    isWhite = !isWhite
  }
  return parsed
}

const formatEvaluation = (line: EngineLine) => formatScore(line.score, whiteToMove.value)
const evaluationClass = (line: EngineLine) => getEvaluationClass(line.score, whiteToMove.value)
</script>
