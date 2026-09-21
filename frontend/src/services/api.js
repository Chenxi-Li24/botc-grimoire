import { getCsrfToken } from './session.js'

export async function api(path, init) {
  const method = (init?.method || 'GET').toUpperCase()
  const csrf = getCsrfToken()
  const response = await fetch(path, {
    ...init,
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...(csrf && !['GET', 'HEAD', 'OPTIONS'].includes(method) ? { 'X-CSRF-Token': csrf } : {}),
      ...(init?.headers || {}),
    },
  })

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
