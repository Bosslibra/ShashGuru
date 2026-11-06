import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { getStyles, isLocalBackendAvailable, streamAnalysis, streamChat } from '@/api/backend'
import { LOCAL_BASE, REMOTE_BASE, isAbortError, isApiError } from '@/api/http'
import i18next from '@/i18n'
import { useAccountStore } from '@/stores/account'
import { useGameStore } from '@/stores/game'
import { useSettingsStore } from '@/stores/settings'
import type { LlmChoice, LlmSource, StreamEvent, StyleInfo } from '@/types/api'

/** Why an answer failed, so the UI can offer the right action (sign in, buy credits, analyse again...). */
export type ChatErrorKind = 'auth' | 'credits' | 'expired' | 'rateLimit' | 'other'

export interface ChatEntry {
  role: 'user' | 'assistant'
  content: string
  /** Legacy backends only: context for the model (the analysis prompt), sent but not displayed. */
  hidden?: boolean
  error?: boolean
  errorKind?: ChatErrorKind
}

const LLM_STORAGE_KEY = 'shashguru.llm'

interface LlmPrefs {
  source: LlmSource
  keyId: number | null
  managedModel: string
  byokModel: string
}

function loadPrefs(): LlmPrefs {
  const base: LlmPrefs = { source: 'managed', keyId: null, managedModel: '', byokModel: '' }
  try {
    const raw = JSON.parse(localStorage.getItem(LLM_STORAGE_KEY) ?? 'null')
    if (raw && typeof raw === 'object') {
      if (raw.source === 'managed' || raw.source === 'byok') base.source = raw.source
      if (Number.isInteger(raw.keyId)) base.keyId = raw.keyId
      if (typeof raw.managedModel === 'string') base.managedModel = raw.managedModel
      if (typeof raw.byokModel === 'string') base.byokModel = raw.byokModel
    }
  } catch {
    /* storage unavailable: defaults */
  }
  return base
}

export function errorKindOf(e: unknown, hasAnalysisId = false): ChatErrorKind {
  if (isApiError(e, 401)) return 'auth'
  if (isApiError(e, 402)) return 'credits'
  if (isApiError(e, 404) && hasAnalysisId) return 'expired'
  if (isApiError(e, 429)) return 'rateLimit'
  return 'other'
}

const FALLBACK_STYLES: StyleInfo[] = [{ value: 'default', label: 'Commentator' }]

export const useChatStore = defineStore('chat', () => {
  const game = useGameStore()
  const settings = useSettingsStore()
  const account = useAccountStore()

  const messages = ref<ChatEntry[]>([])
  const loading = ref(false)
  /** True when the Analyze button (rather than the question box) is shown. */
  const toAnalyse = ref(true)
  const style = ref('default')
  const styles = ref<StyleInfo[]>(FALLBACK_STYLES)
  const backend = ref<'checking' | 'local' | 'remote'>('checking')
  /** Server-side id of the current analysis: follow-up questions refer to it instead of resending the context. */
  const analysisId = ref<string | null>(null)
  const lastUsage = ref<{ input_tokens: number; output_tokens: number; credits: number } | null>(null)

  // ----- who pays for the LLM ----------------------------------------------

  const prefs = ref<LlmPrefs>(loadPrefs())
  watch(
    prefs,
    (value) => {
      try {
        localStorage.setItem(LLM_STORAGE_KEY, JSON.stringify(value))
      } catch {
        /* ignore */
      }
    },
    { deep: true },
  )

  /** The source/model picker applies to the hosted backend only (not to the local AI PC or self-hosted installs). */
  const usesAccount = computed(() => account.saas && backend.value !== 'local')

  const llmChoice = computed<LlmChoice>(() => {
    if (!usesAccount.value) return {}
    if (prefs.value.source === 'byok') {
      return { source: 'byok', key_id: prefs.value.keyId ?? undefined, model: prefs.value.byokModel || undefined }
    }
    return { source: 'managed', model: prefs.value.managedModel || account.models?.default_managed || undefined }
  })

  /** False when the chosen source cannot work yet (BYOK without a saved key). */
  const canRun = computed(() => !usesAccount.value || prefs.value.source !== 'byok' || prefs.value.keyId !== null)

  // Keep the selection valid as keys/models load or change.
  watch(
    () => account.keys,
    (keys) => {
      if (keys.length === 0) prefs.value.keyId = null
      else if (!keys.some((k) => k.id === prefs.value.keyId)) prefs.value.keyId = keys[0].id
    },
    { deep: true },
  )
  watch(
    () => account.models,
    (models) => {
      if (!models) return
      if (!models.managed.some((m) => m.id === prefs.value.managedModel)) {
        prefs.value.managedModel = models.default_managed ?? models.managed[0]?.id ?? ''
      }
    },
  )

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

  /** Append the events of a stream to `target`. */
  async function consume(events: AsyncGenerator<StreamEvent>, target: ChatEntry) {
    let balanceUpdated = false
    for await (const event of events) {
      if (event.type === 'context') {
        if (event.analysis_id) {
          analysisId.value = event.analysis_id
        } else if (event.prompt) {
          const index = messages.value.indexOf(target)
          messages.value.splice(index, 0, { role: 'user', content: event.prompt, hidden: true })
        }
      } else if (event.type === 'token') {
        target.content += event.text
      } else if (event.type === 'usage') {
        lastUsage.value = { input_tokens: event.input_tokens, output_tokens: event.output_tokens, credits: event.credits }
        if (event.balance) {
          account.applyBalance(event.balance)
          balanceUpdated = true
        }
      } else if (event.type === 'error') {
        throw new Error(event.message)
      }
    }
    target.content = target.content.trim()
    // Managed usage costs credits: make sure the displayed balance is current.
    if (usesAccount.value && prefs.value.source === 'managed' && !balanceUpdated) void account.refreshMe()
  }

  function fail(target: ChatEntry, e: unknown, what: string) {
    if (isAbortError(e)) return
    console.error('Streaming error:', e)
    target.error = true
    target.errorKind = errorKindOf(e, analysisId.value !== null)
    // Keep the raw detail only; the UI shows a translated title and a retry button.
    target.content = e instanceof Error && e.message ? e.message : i18next.t('chat.fetchFailed', { what })
  }

  function newAssistantEntry(): ChatEntry {
    messages.value.push({ role: 'assistant', content: '' })
    return messages.value[messages.value.length - 1]
  }

  async function analyze() {
    toAnalyse.value = false
    messages.value = []
    analysisId.value = null
    lastUsage.value = null
    const signal = startRequest()
    const target = newAssistantEntry()
    try {
      await consume(
        streamAnalysis({
          fen: game.currentFen,
          depth: settings.depth,
          style: style.value,
          base: base.value,
          signal,
          ...llmChoice.value,
        }),
        target,
      )
    } catch (e) {
      fail(target, e, i18next.t('chat.whatAnalysis'))
    } finally {
      if (!signal.aborted) loading.value = false
    }
  }

  async function ask(question: string) {
    const text = question.trim()
    if (!text) return
    const history = messages.value
      // With a server-side analysis the context is not resent, so only visible turns go out.
      .filter((m) => !m.error && m.content && !(analysisId.value && m.hidden))
      .map(({ role, content }) => ({ role, content }))
    messages.value.push({ role: 'user', content: text })
    const signal = startRequest()
    const target = newAssistantEntry()
    try {
      await consume(
        streamChat({
          analysisId: analysisId.value ?? undefined,
          messages: [...history, { role: 'user', content: text }],
          style: style.value,
          base: base.value,
          signal,
          ...llmChoice.value,
        }),
        target,
      )
    } catch (e) {
      fail(target, e, i18next.t('chat.whatResponse'))
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
    analysisId, lastUsage, prefs, usesAccount, llmChoice, canRun,
    checkingLocalBackend, isLocalBackendAvailable: isLocalBackendAvailable_,
    backend, init, recheckBackend, analyze, ask, regenerate,
  }
})
