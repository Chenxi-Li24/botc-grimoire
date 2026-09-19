import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../src/services/api.js'

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('merges JSON and caller headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ ok: true }),
    })
    vi.stubGlobal('fetch', fetchMock)
    await api('/api/state', { headers: { 'X-Storyteller-Password': 'secret' } })
    expect(fetchMock.mock.calls[0][1].headers).toEqual({
      'Content-Type': 'application/json',
      'X-Storyteller-Password': 'secret',
    })
  })

  it('formats FastAPI 422 errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: [{ loc: ['body', 'room_code'], msg: 'invalid' }] }),
    }))
    await expect(api('/api/join')).rejects.toThrow('body.room_code: invalid')
  })

  it('falls back to the HTTP status for non-JSON errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => { throw new Error('not json') },
    }))
    await expect(api('/api/info')).rejects.toThrow('HTTP 503')
  })
})
