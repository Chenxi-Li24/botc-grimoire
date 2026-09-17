export const ST_PASSWORD_KEY = 'botc_st_password'
export const PLAYER_ID_KEY = 'botc_player_id'

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function stApi<T>(path: string, init?: RequestInit): Promise<T> {
  const password = localStorage.getItem(ST_PASSWORD_KEY) ?? ''
  return api<T>(path, {
    ...init,
    headers: { 'X-Storyteller-Password': password, ...(init?.headers ?? {}) },
  })
}

export function openSocket<T>(
  query: string,
  onMessage: (view: T) => void,
  opts?: { onFatal?: () => void; keepAlive?: () => boolean },
): WebSocket {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws?${query}`)
  ws.onmessage = (e) => onMessage(JSON.parse(e.data))
  ws.onclose = (e) => {
    // 4001 身份失效(被移除/重置),4003 说书人密码错误 → 不再重连
    if (e.code === 4001 || e.code === 4003) {
      opts?.onFatal?.()
      return
    }
    if (!(opts?.keepAlive?.() ?? true)) return
    setTimeout(() => openSocket(query, onMessage, opts), 1500) // 断线自动重连
  }
  return ws
}
