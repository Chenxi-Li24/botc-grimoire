import { getCsrfToken, setCsrfToken } from './session.js'

const accountEntry = new Set(['/api/account/register', '/api/account/login', '/api/account/reset-password'])

async function refreshCsrf() {
  const response = await fetch('/api/session', { credentials: 'same-origin' })
  if (response.ok) {
    const session = await response.json()
    setCsrfToken(session.csrf_token)
  }
}

export async function api(path, init) {
  const method = (init?.method || 'GET').toUpperCase()
  const write = !['GET', 'HEAD', 'OPTIONS'].includes(method)
  if (write && accountEntry.has(path) && !getCsrfToken()) await refreshCsrf()
  const send = () => fetch(path, {
    ...init,
    credentials: 'same-origin',
    headers: {
      ...((typeof init?.body === 'string' || !init?.body) ? { 'Content-Type': 'application/json' } : {}),
      ...(getCsrfToken() && write ? { 'X-CSRF-Token': getCsrfToken() } : {}),
      ...(init?.headers || {}),
    },
  })
  let response = await send()
  if (write && accountEntry.has(path) && response.status === 403) {
    const failure = await response.clone().json().catch(() => null)
    if (failure?.detail === '安全令牌无效') {
      await refreshCsrf()
      response = await send()
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item) => `${(item.loc || []).join('.')}: ${item.msg}`).join('; ')
      : body?.detail
    const error = new Error(body?.message || detail || `HTTP ${response.status}`)
    error.code = body?.code || null
    error.details = body?.details || null
    error.status = response.status
    throw error
  }

  return response.json()
}
