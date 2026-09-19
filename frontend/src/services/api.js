export async function api(path, init) {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item) => `${(item.loc || []).join('.')}: ${item.msg}`).join('; ')
      : body?.detail
    throw new Error(detail || `HTTP ${response.status}`)
  }

  return response.json()
}
