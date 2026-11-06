import { describe, expect, it } from 'vitest'
import { readNdjson } from './ndjson'

function responseFrom(chunks: string[]): Response {
  const enc = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c))
      controller.close()
    },
  })
  return new Response(stream)
}

async function collect<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const out: T[] = []
  for await (const item of gen) out.push(item)
  return out
}

describe('readNdjson', () => {
  it('reassembles lines split across chunks', async () => {
    const events = await collect(
      readNdjson(responseFrom(['{"type":"tok', 'en","text":"a"}\n{"type":"done"}', '\n'])),
    )
    expect(events).toEqual([{ type: 'token', text: 'a' }, { type: 'done' }])
  })

  it('handles several events in one chunk and a missing trailing newline', async () => {
    const events = await collect(readNdjson(responseFrom(['{"a":1}\n{"a":2}\n{"a":3}'])))
    expect(events).toEqual([{ a: 1 }, { a: 2 }, { a: 3 }])
  })

  it('does not split multi-byte characters', async () => {
    const bytes = new TextEncoder().encode('{"t":"é♞"}\n')
    const stream = new ReadableStream({
      start(c) {
        c.enqueue(bytes.slice(0, 7)) // cuts inside "é"
        c.enqueue(bytes.slice(7))
        c.close()
      },
    })
    expect(await collect(readNdjson(new Response(stream)))).toEqual([{ t: 'é♞' }])
  })
})
