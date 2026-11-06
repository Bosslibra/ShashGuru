import { describe, expect, it } from 'vitest'
import { createAuthClient } from './index'
import { createNoneAuth } from './none'
import { devToken } from './dev'

describe('auth adapters', () => {
  it('defaults to the none adapter', async () => {
    const client = createAuthClient()
    expect(client.name).toBe('none')
    await client.init()
    expect(client.getUser()).toBeNull()
    expect(await client.getToken()).toBeNull()
  })

  it('selects an adapter by name', () => {
    expect(createAuthClient('dev').name).toBe('dev')
    expect(createAuthClient('clerk').name).toBe('clerk')
    expect(createNoneAuth().name).toBe('none')
  })

  it('formats the dev token as dev:<subject>:<email>', () => {
    expect(devToken({ id: 'ann', email: 'ann@example.com' })).toBe('dev:ann:ann@example.com')
  })
})
