/** Parse a newline-delimited JSON response body as it arrives. Lines may be split across chunks. */
export async function* readNdjson<T>(response: Response): AsyncGenerator<T> {
  if (!response.body) throw new Error('Response has no body')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let newline: number
      while ((newline = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, newline).trim()
        buffer = buffer.slice(newline + 1)
        if (line) yield JSON.parse(line) as T
      }
      if (done) break
    }
    const rest = buffer.trim()
    if (rest) yield JSON.parse(rest) as T
  } finally {
    reader.releaseLock()
  }
}
