import { defineStore } from 'pinia'
import { computed, ref, shallowRef, watch } from 'vue'
import { evaluateCached } from '@/api/evaluate'
import { isAbortError } from '@/api/http'
import { useGameStore } from '@/stores/game'
import { useSettingsStore } from '@/stores/settings'
import type { Evaluation } from '@/types/api'

/**
 * Engine evaluation of the position currently on the board. It follows the current position and
 * the evaluation settings; a request that is no longer wanted is aborted.
 */
export const useEvaluationStore = defineStore('evaluation', () => {
  const game = useGameStore()
  const settings = useSettingsStore()

  /** Latest evaluation received. Kept while a new one is loading so the bar does not flicker. */
  const current = shallowRef<Evaluation | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  let controller: AbortController | null = null

  const lines = computed(() => current.value?.lines ?? [])
  /** Best move (UCI) for the position on the board, if the evaluation is up to date. */
  const bestMove = computed(() =>
    current.value?.fen === game.currentFen ? (current.value.lines[0]?.move ?? null) : null,
  )

  async function refresh() {
    controller?.abort()
    controller = null

    if (!settings.enabled || !game.currentFen) {
      current.value = null
      error.value = null
      loading.value = false
      return
    }

    const mine = new AbortController()
    controller = mine
    loading.value = true
    error.value = null
    try {
      const result = await evaluateCached(game.currentFen, settings.depth, settings.lines, mine.signal)
      if (mine.signal.aborted) return
      current.value = result
    } catch (e) {
      if (isAbortError(e) || mine.signal.aborted) return
      console.error('Error fetching evaluation:', e)
      error.value = 'Failed to get evaluation'
      current.value = null
    } finally {
      if (controller === mine) {
        loading.value = false
        controller = null
      }
    }
  }

  watch(
    () => [game.currentFen, settings.depth, settings.lines, settings.enabled],
    refresh,
    { immediate: true },
  )

  return { current, loading, error, lines, bestMove, refresh }
})
