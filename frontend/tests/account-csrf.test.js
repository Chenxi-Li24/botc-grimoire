import { beforeEach, expect, it, vi } from 'vitest'
import { api } from '../src/services/api.js'
import { clearCsrfToken, setCsrfToken } from '../src/services/session.js'

beforeEach(() => {
  clearCsrfToken()
  vi.restoreAllMocks()
})

it('refreshes a valid guest CSRF token before account registration', async () => {
  const fetcher = vi.spyOn(globalThis, 'fetch')
  fetcher.mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'guest-token' })))
  fetcher.mockResolvedValueOnce(new Response(JSON.stringify({ uid: '1234' })))
  await api('/api/account/register', { method: 'POST', body: '{}' })
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(fetcher.mock.calls[0][0]).toBe('/api/session')
  expect(fetcher.mock.calls[1][1].headers['X-CSRF-Token']).toBe('guest-token')
})

it('refreshes and retries once when a guest CSRF token became stale', async () => {
  setCsrfToken('stale')
  const fetcher = vi.spyOn(globalThis, 'fetch')
  fetcher.mockResolvedValueOnce(new Response(JSON.stringify({ detail: '安全令牌无效' }), { status: 403 }))
  fetcher.mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'fresh' })))
  fetcher.mockResolvedValueOnce(new Response(JSON.stringify({ uid: '1234' })))
  await api('/api/account/register', { method: 'POST', body: '{}' })
  expect(fetcher).toHaveBeenCalledTimes(3)
  expect(fetcher.mock.calls[2][1].headers['X-CSRF-Token']).toBe('fresh')
})
