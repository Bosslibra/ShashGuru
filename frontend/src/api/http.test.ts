import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, LOCAL_BASE, REMOTE_BASE, request, setAuthTokenProvider } from './http'

function mockFetch(status = 200, body: unknown = {}) {
  const fn = vi.fn(async () => new Response(JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fn)
  return fn
}

function sentHeaders(fn: ReturnType<typeof mockFetch>): Headers {
  const init = (fn.mock.calls[0] as unknown as [string, RequestInit])[1]
  return new Headers(init?.headers)
}

afterEach(() => {
  setAuthTokenProvider(null)
  vi.unstubAllGlobals()
})

describe('request', () => {
  it('adds the bearer token to requests for our backend', async () => {
    const fetchMock = mockFetch()
    setAuthTokenProvider(async () => 'abc')
    await request(`${REMOTE_BASE}/api/v1/me`)
    expect(sentHeaders(fetchMock).get('Authorization')).toBe('Bearer abc')
  })

  it('keeps existing headers when adding the token', async () => {
    const fetchMock = mockFetch()
    setAuthTokenProvider(async () => 'abc')
    await request(`${REMOTE_BASE}/api/v1/chat`, { headers: { 'Content-Type': 'application/json' } })
    const headers = sentHeaders(fetchMock)
    expect(headers.get('Content-Type')).toBe('application/json')
    expect(headers.get('Authorization')).toBe('Bearer abc')
  })

  it('never sends the token to the local AI PC or other hosts', async () => {
    const fetchMock = mockFetch()
    setAuthTokenProvider(async () => 'abc')
    await request(`${LOCAL_BASE}/api/v1/styles`)
    expect(sentHeaders(fetchMock).has('Authorization')).toBe(false)
  })

  it('sends no header when signed out', async () => {
    const fetchMock = mockFetch()
    setAuthTokenProvider(async () => null)
    await request(`${REMOTE_BASE}/api/v1/styles`)
    expect(sentHeaders(fetchMock).has('Authorization')).toBe(false)
  })

  it.each([401, 402, 404, 429])('exposes status %i on ApiError', async (status) => {
    mockFetch(status, { detail: 'nope' })
    const error = await request(`${REMOTE_BASE}/x`).catch((e) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(status)
    expect(error.message).toBe('nope')
  })
})
