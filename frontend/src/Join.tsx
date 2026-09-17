import { useEffect, useState } from 'react'
import { api, PLAYER_ID_KEY } from './api'
import RoleCard from './RoleCard'
import type { PlayerView } from './types'

export default function Join() {
  const [playerId, setPlayerId] = useState<string | null>(() => localStorage.getItem(PLAYER_ID_KEY))
  const [checking, setChecking] = useState(!!playerId)
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // 恢复上次身份(刷新页面不丢;被说书人移除/重置则自动回到加入页)
  useEffect(() => {
    if (!playerId) return
    api<PlayerView>(`/api/me/${playerId}`)
      .then(() => setChecking(false))
      .catch(() => {
        localStorage.removeItem(PLAYER_ID_KEY)
        setPlayerId(null)
        setChecking(false)
      })
  }, [playerId])

  const join = async () => {
    if (!name.trim()) return
    setBusy(true)
    setError('')
    try {
      const res = await api<{ player_id: string }>('/api/join', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim() }),
      })
      localStorage.setItem(PLAYER_ID_KEY, res.player_id)
      setPlayerId(res.player_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : '加入失败')
    } finally {
      setBusy(false)
    }
  }

  if (checking) return <div className="page center">正在恢复你的身份…</div>
  if (playerId) return <RoleCard playerId={playerId} />

  return (
    <div className="page center">
      <h1>🩸 血染钟楼</h1>
      <p className="sub">输入名字加入本局</p>
      <input
        className="input"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && join()}
        placeholder="你的名字"
        maxLength={20}
        autoFocus
      />
      <button className="btn primary" onClick={join} disabled={busy || !name.trim()}>
        加入
      </button>
      {error && <p className="error">{error}</p>}
    </div>
  )
}
