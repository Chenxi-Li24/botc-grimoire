import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../src/services/api.js'
import { clearCsrfToken, setCsrfToken } from '../src/services/session.js'

afterEach(() => {
  vi.unstubAllGlobals()
  clearCsrfToken()
})

it('sends cookie credentials and in-memory CSRF only for writes', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ok: true }) })
  vi.stubGlobal('fetch', fetchMock)
  setCsrfToken('csrf-secret')
  await api('/api/session')
  await api('/api/player/p1/vote', { method: 'POST' })
  expect(fetchMock.mock.calls[0][1].credentials).toBe('same-origin')
  expect(fetchMock.mock.calls[0][1].headers['X-CSRF-Token']).toBeUndefined()
  expect(fetchMock.mock.calls[1][1].headers['X-CSRF-Token']).toBe('csrf-secret')
  expect(localStorage.getItem('csrf-secret')).toBeNull()
})
