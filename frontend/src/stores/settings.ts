import { defineStore } from 'pinia'
import { reactive, toRefs, watch } from 'vue'
import {
  DEFAULT_DEPTH,
  DEFAULT_EVALUATION_ENABLED,
  DEFAULT_SHOW_BEST_MOVE,
  DEFAULT_SHOW_LINES,
  MAX_DEPTH,
  MAX_SHOW_LINES,
  MIN_DEPTH,
  MIN_SHOW_LINES,
} from '@/constants/evaluation'

const STORAGE_KEY = 'shashguru.settings'

interface Persisted {
  depth: number
  lines: number
  enabled: boolean
  showBestMove: boolean
}

const clamp = (n: number, min: number, max: number) => Math.min(max, Math.max(min, Math.round(n)))

function defaults(): Persisted {
  return {
    depth: DEFAULT_DEPTH,
    lines: DEFAULT_SHOW_LINES,
    enabled: DEFAULT_EVALUATION_ENABLED,
    showBestMove: DEFAULT_SHOW_BEST_MOVE,
  }
}

function load(): Persisted {
  const base = defaults()
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null')
    if (raw && typeof raw === 'object') {
      if (Number.isFinite(raw.depth)) base.depth = clamp(raw.depth, MIN_DEPTH, MAX_DEPTH)
      if (Number.isFinite(raw.lines)) base.lines = clamp(raw.lines, MIN_SHOW_LINES, MAX_SHOW_LINES)
      if (typeof raw.enabled === 'boolean') base.enabled = raw.enabled
      if (typeof raw.showBestMove === 'boolean') base.showBestMove = raw.showBestMove
    }
  } catch {
    /* storage unavailable or corrupted: use defaults */
  }
  return base
}

/** Engine evaluation settings, remembered across sessions. */
export const useSettingsStore = defineStore('settings', () => {
  const state = reactive<Persisted>(load())

  watch(state, (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
    } catch {
      /* ignore */
    }
  })

  function reset() {
    Object.assign(state, defaults())
  }

  return { ...toRefs(state), reset }
})
