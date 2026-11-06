import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ApiError } from '@/api/http'
import type { StreamEvent } from '@/types/api'

vi.mock('@/api/backend', () => ({
  getStyles: vi.fn(async () => [{ value: 'default', label: 'Commentator' }]),
  isLocalBackendAvailable: vi.fn(async () => false),
  streamAnalysis: vi.fn(),
  streamChat: vi.fn(),
  getConfig: vi.fn(),
  getMe: vi.fn(),
  getModels: vi.fn(),
  getKeys: vi.fn(),
  getOffers: vi.fn(),
}))

import * as backend from '@/api/backend'
import { errorKindOf, useChatStore } from './chat'
import { useAccountStore } from './account'

async function* events(...list: StreamEvent[]) {
  for (const e of list) yield e
}

const spies = () => ({
  analysis: vi.mocked(backend.streamAnalysis),
  chat: vi.mocked(backend.streamChat),
})

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
})

describe('chat store streaming', () => {
  it('keeps the analysis id and does not store a hidden prompt', async () => {
    spies().analysis.mockReturnValue(
      events(
        { type: 'context', analysis_id: 'an-1' },
        { type: 'token', text: 'Hello ' },
        { type: 'token', text: 'world' },
        { type: 'done' },
      ),
    )
    const chat = useChatStore()
    await chat.analyze()
    expect(chat.analysisId).toBe('an-1')
    expect(chat.messages).toHaveLength(1)
    expect(chat.messages[0].content).toBe('Hello world')
  })

  it('sends the analysis id and only the visible turns in follow-ups', async () => {
    spies().analysis.mockReturnValue(events({ type: 'context', analysis_id: 'an-1' }, { type: 'token', text: 'A' }, { type: 'done' }))
    spies().chat.mockReturnValue(events({ type: 'token', text: 'B' }, { type: 'done' }))
    const chat = useChatStore()
    await chat.analyze()
    await chat.ask('why?')
    const params = spies().chat.mock.calls[0][0]
    expect(params.analysisId).toBe('an-1')
    expect(params.messages).toEqual([
      { role: 'assistant', content: 'A' },
      { role: 'user', content: 'why?' },
    ])
  })

  it('falls back to a hidden context message for legacy backends', async () => {
    spies().analysis.mockReturnValue(events({ type: 'context', prompt: 'CTX' }, { type: 'token', text: 'A' }, { type: 'done' }))
    spies().chat.mockReturnValue(events({ type: 'done' }))
    const chat = useChatStore()
    await chat.analyze()
    expect(chat.analysisId).toBeNull()
    expect(chat.visibleMessages).toHaveLength(1)
    await chat.ask('q')
    expect(spies().chat.mock.calls[0][0].messages[0]).toEqual({ role: 'user', content: 'CTX' })
  })

  it('applies the balance from usage events', async () => {
    spies().analysis.mockReturnValue(
      events(
        { type: 'token', text: 'x' },
        { type: 'usage', input_tokens: 10, output_tokens: 5, credits: 2, balance: { subscription: 8, purchased: 0, total: 8 } },
        { type: 'done' },
      ),
    )
    const account = useAccountStore()
    const apply = vi.spyOn(account, 'applyBalance')
    const chat = useChatStore()
    await chat.analyze()
    expect(chat.lastUsage).toEqual({ input_tokens: 10, output_tokens: 5, credits: 2 })
    expect(apply).toHaveBeenCalledWith({ subscription: 8, purchased: 0, total: 8 })
  })

  it('marks failures with the kind that drives the UI action', async () => {
    spies().analysis.mockImplementation(async function* () {
      throw new ApiError(402, 'no credits')
    })
    const chat = useChatStore()
    await chat.analyze()
    expect(chat.messages[0]).toMatchObject({ error: true, errorKind: 'credits' })
  })

  it('does not send an LLM choice when not hosted (self-hosted / local AI PC)', async () => {
    spies().analysis.mockReturnValue(events({ type: 'done' }))
    const chat = useChatStore()
    await chat.analyze()
    const params = spies().analysis.mock.calls[0][0]
    expect(params.source).toBeUndefined()
    expect(params.key_id).toBeUndefined()
  })
})

describe('errorKindOf', () => {
  it('maps statuses', () => {
    expect(errorKindOf(new ApiError(401, ''))).toBe('auth')
    expect(errorKindOf(new ApiError(402, ''))).toBe('credits')
    expect(errorKindOf(new ApiError(429, ''))).toBe('rateLimit')
    expect(errorKindOf(new ApiError(404, ''), true)).toBe('expired')
    expect(errorKindOf(new ApiError(404, ''), false)).toBe('other')
    expect(errorKindOf(new Error('x'))).toBe('other')
  })
})
