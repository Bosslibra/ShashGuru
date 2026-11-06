import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { getStyles, isLocalBackendAvailable, streamAnalysis, streamChat } from '@/api/backend'
import { LOCAL_BASE, REMOTE_BASE, isAbortError } from '@/api/http'
import { useGameStore } from '@/stores/game'
import { useSettingsStore } from '@/stores/settings'
import type { StreamEvent, StyleInfo } from '@/types/api'

export interface ChatEntry {
  role: 'user' | 'assistant'
  content: string
  /** Context for the model (the analysis prompt): sent to the backend but not displayed. */
  hidden?: boolean
  error?: boolean
}

const FALLBACK_STYLES: StyleInfo[] = [{ value: 'default', label: 'Commentator' }]

export const useChatStore = defineStore('chat', () => {
  const game = useGameStore()
  const settings = useSettingsStore()

  const messages = ref<ChatEntry[]>([])
  const loading = ref(false)
  /** True when the Analyze button (rather than the question box) is shown. */
  const toAnalyse = ref(true)
  const style = ref('default')
  const styles = ref<StyleInfo[]>(FALLBACK_STYLES)
  const backend = ref<'checking' | 'local' | 'remote'>('checking')

  const checkingLocalBackend = computed(() => backend.value === 'checking')
  const isLocalBackendAvailable_ = computed(() => backend.value === 'local')
  const base = computed(() => (backend.value === 'local' ? LOCAL_BASE : REMOTE_BASE))
  const visibleMessages = computed(() => messages.value.map((m, index) => ({ ...m, index })).filter((m) => !m.hidden))

  let controller: AbortController | null = null
  let initPromise: Promise<void> | null = null

  // ----- backend selection and styles -------------------------------------

  async function loadStyles() {
    try {
      const list = await getStyles(base.value)
      styles.value = list.some((s) => s.value === 'default') ? list : [...FALLBACK_STYLES, ...list]
    } catch (e) {
      console.error('Error fetching analysis styles:', e)
      styles.value = FALLBACK_STYLES
    }
    if (!styles.value.some((s) => s.value === style.value)) style.value = 'default'
  }

  async function recheckBackend() {
    backend.value = 'checking'
    backend.value = (await isLocalBackendAvailable()) ? 'local' : 'remote'
    await loadStyles()
  }

  /** Detect the backend once per session; later calls reuse the result. */
  function init(): Promise<void> {
    initPromise ??= recheckBackend()
    return initPromise
  }

  // ----- streaming ---------------------------------------------------------

  function startRequest(): AbortSignal {
    controller?.abort()
    controller = new AbortController()
    loading.value = true
    return controller.signal
  }

  /** Append the events of a stream to `target`. Returns the analysis prompt if one was sent. */
  async function consume(events: AsyncGenerator<StreamEvent>, target: ChatEntry) {
    for await (const event of events) {
      if (event.type === 'context') {
        const index = messages.value.indexOf(target)
        messages.value.splice(index, 0, { role: 'user', content: event.prompt, hidden: true })
      } else if (event.type === 'token') {
        target.content += event.text
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    }
    target.content = target.content.trim()
  }

  function fail(target: ChatEntry, e: unknown, what: string) {
    if (isAbortError(e)) return
    console.error('Streaming error:', e)
    target.error = true
    target.content = e instanceof Error && e.message ? `Error: ${e.message}` : `Error: unable to fetch ${what}.`
  }

  function newAssistantEntry(): ChatEntry {
    messages.value.push({ role: 'assistant', content: '' })
    return messages.value[messages.value.length - 1]
  }

  async function analyze() {
    toAnalyse.value = false
    messages.value = []
    const signal = startRequest()
    const target = newAssistantEntry()
    try {
      await consume(
        streamAnalysis({ fen: game.currentFen, depth: settings.depth, style: style.value, base: base.value, signal }),
        target,
      )
    } catch (e) {
      fail(target, e, 'analysis')
    } finally {
      if (!signal.aborted) loading.value = false
    }
  }

  async function ask(question: string) {
    const text = question.trim()
    if (!text) return
    const history = messages.value
      .filter((m) => !m.error && m.content)
      .map(({ role, content }) => ({ role, content }))
    messages.value.push({ role: 'user', content: text })
    const signal = startRequest()
    const target = newAssistantEntry()
    try {
      await consume(
        streamChat({
          messages: [...history, { role: 'user', content: text }],
          style: style.value,
          base: base.value,
          signal,
        }),
        target,
      )
    } catch (e) {
      fail(target, e, 'response')
    } finally {
      if (!signal.aborted) loading.value = false
    }
  }

  /** Regenerate the last assistant message. */
  async function regenerate() {
    const last = messages.value.length - 1
    if (last < 0 || messages.value[last].role !== 'assistant') return
    const previous = messages.value[last - 1]
    if (!previous || previous.hidden) return analyze()
    messages.value.splice(last - 1, 2)
    return ask(previous.content)
  }

  // A new position or style makes the old analysis stale: offer to analyze again.
  watch(
    () => game.currentFen,
    () => (toAnalyse.value = true),
  )
  watch(style, () => {
    if (messages.value.length > 0) toAnalyse.value = true
  })

  return {
    messages, visibleMessages, loading, toAnalyse, style, styles,
    checkingLocalBackend, isLocalBackendAvailable: isLocalBackendAvailable_,
    init, recheckBackend, analyze, ask, regenerate,
  }
})
