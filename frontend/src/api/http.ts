/** Backend behind the nginx reverse proxy (or the Vite dev proxy): `/backend/*` -> backend `/*`. */
export const REMOTE_BASE = import.meta.env.BASE_URL + 'backend'
/** Backend started on the user's own machine ("AI PC" mode). */
export const LOCAL_BASE = 'http://localhost:5000'

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/** FastAPI errors are `{detail: string | [{msg, loc}]}`. */
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join('; ')
  } catch {
    /* not JSON */
  }
  return response.statusText || `HTTP ${response.status}`
}

export async function request(url: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(url, init)
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  return response
}

export async function postJson(url: string, body: unknown, signal?: AbortSignal): Promise<Response> {
  return request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}
