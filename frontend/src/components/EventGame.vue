<script setup lang="ts">
import { computed, reactive } from 'vue'
import { Chess } from 'chess.js'
import { TheChessboard } from 'vue3-chessboard'
import { useRouter } from 'vue-router'
import { useTranslation } from 'i18next-vue'
import 'vue3-chessboard/style.css'
import { STARTING_FEN } from '@/lib/fen'
import { parseHeaders } from '@/lib/pgn'
import { useGameStore } from '@/stores/game'
import { useToastStore } from '@/stores/toast'

const props = withDefaults(defineProps<{ pgn?: string }>(), { pgn: '' })

const { t } = useTranslation()
const toast = useToastStore()
const game = useGameStore()
const router = useRouter()

const metadata = computed(() => {
  const tags = parseHeaders(props.pgn)
  return {
    whitePlayerTitle: tags.WhiteTitle ?? null,
    whitePlayerName: tags.White ?? null,
    whitePlayerRating: tags.WhiteElo ?? null,
    blackPlayerTitle: tags.BlackTitle ?? null,
    blackPlayerName: tags.Black ?? null,
    blackPlayerRating: tags.BlackElo ?? null,
    gameResult: tags.Result ?? null,
    openingName: tags.Opening ?? null,
  }
})

const cardLabel = computed(
  () => `${metadata.value.whitePlayerName ?? t('common.white')} - ${metadata.value.blackPlayerName ?? t('common.black')}`,
)

/** Final position of the game, or the starting position if the PGN cannot be read. */
function finalFen(pgn: string): string {
  try {
    const chess = new Chess()
    chess.loadPgn(pgn)
    return chess.fen()
  } catch {
    return STARTING_FEN
  }
}

const boardConfig = reactive({
  fen: finalFen(props.pgn),
  viewOnly: true, // Make the board read-only
  orientation: 'white' as const,
})

function navigateToAnalysis() {
  try {
    game.loadPgn(props.pgn)
  } catch (error) {
    console.warn(error)
    toast.error(t('errors.invalidPgn'))
    return
  }
  router.push({ name: 'home' })
}

function resultFor(side: 'white' | 'black'): string | null {
  const res = metadata.value.gameResult
  if (!res || res === '*') return null
  if (res === '1-0') return side === 'white' ? '1' : '0'
  if (res === '0-1') return side === 'white' ? '0' : '1'
  if (res === '1/2-1/2') return '½'
  return null
}

function resultClass(result: string | null): string {
  if (result === '1') return 'text-success'
  if (result === '0') return 'text-destructive'
  return 'text-muted-foreground'
}
</script>

<template>
  <div
    class="event-game-card min-w-0 cursor-pointer rounded-(--radius) border border-border bg-card p-2.5 outline-none transition-colors hover:border-olive hover:bg-accent/50 focus-visible:ring-2 focus-visible:ring-ring"
    role="button"
    tabindex="0"
    :aria-label="cardLabel"
    @click="navigateToAnalysis"
    @keydown.enter.self.prevent="navigateToAnalysis"
    @keydown.space.self.prevent="navigateToAnalysis"
  >
    <!-- Black player -->
    <div class="flex items-center gap-1.5 text-sm">
      <span v-if="metadata.blackPlayerTitle" class="shrink-0 text-xs font-bold text-olive">{{ metadata.blackPlayerTitle }}</span>
      <span class="min-w-0 flex-1 truncate">{{ metadata.blackPlayerName }}</span>
      <span v-if="metadata.blackPlayerRating" class="num shrink-0 text-xs text-muted-foreground">{{ metadata.blackPlayerRating }}</span>
      <span v-if="resultFor('black')" class="num w-4 shrink-0 text-right font-bold" :class="resultClass(resultFor('black'))">
        {{ resultFor('black') }}
      </span>
    </div>

    <!-- Board -->
    <div class="relative my-2 aspect-square w-full overflow-hidden rounded-[calc(var(--radius)*0.7)] ring-1 ring-border">
      <TheChessboard :board-config="boardConfig" class="w-full! max-w-none!" />
      <div
        v-if="metadata.gameResult === '*'"
        class="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-black/45 text-lg font-bold text-white"
      >
        <span class="size-2 animate-pulse rounded-full bg-destructive" aria-hidden="true"></span>
        {{ t('live.ongoing') }}
      </div>
    </div>

    <!-- White player -->
    <div class="flex items-center gap-1.5 text-sm">
      <span v-if="metadata.whitePlayerTitle" class="shrink-0 text-xs font-bold text-olive">{{ metadata.whitePlayerTitle }}</span>
      <span class="min-w-0 flex-1 truncate">{{ metadata.whitePlayerName }}</span>
      <span v-if="metadata.whitePlayerRating" class="num shrink-0 text-xs text-muted-foreground">{{ metadata.whitePlayerRating }}</span>
      <span v-if="resultFor('white')" class="num w-4 shrink-0 text-right font-bold" :class="resultClass(resultFor('white'))">
        {{ resultFor('white') }}
      </span>
    </div>
  </div>
</template>
