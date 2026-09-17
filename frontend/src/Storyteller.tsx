import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { api, openSocket, stApi, ST_PASSWORD_KEY } from './api'
import type { StorytellerView, Team } from './types'

const TEAM_LABEL: Record<Team, string> = {
  townsfolk: '镇民',
  outsider: '外来者',
  minion: '爪牙',
  demon: '恶魔',
}

export default function Storyteller() {
  const [authed, setAuthed] = useState(() => !!localStorage.getItem(ST_PASSWORD_KEY))
  const [password, setPassword] = useState('')
  const [view, setView] = useState<StorytellerView | null>(null)
  const [lanIp, setLanIp] = useState('')
  const [qr, setQr] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const joinUrl = lanIp ? `http://${lanIp}:8000/` : ''

  // 加入二维码:指向后端端口(与 run.py 的 PORT 常量一致)
  useEffect(() => {
    api<{ lan_ip: string }>('/api/info')
      .then((info) => {
        setLanIp(info.lan_ip)
        QRCode.toDataURL(`http://${info.lan_ip}:8000/`, { margin: 1, width: 220 }).then(setQr)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!authed) return
    let alive = true
    const pw = encodeURIComponent(localStorage.getItem(ST_PASSWORD_KEY) ?? '')
    const ws = openSocket<StorytellerView>(`who=storyteller&pw=${pw}`, setView, {
      keepAlive: () => alive,
    })
    return () => {
      alive = false
      ws.close()
    }
  }, [authed])

  const login = async () => {
    setBusy(true)
    setError('')
    try {
      const { ok } = await api<{ ok: boolean }>('/api/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      })
      if (ok) {
        localStorage.setItem(ST_PASSWORD_KEY, password)
        setAuthed(true)
      } else {
        setError('密码错误')
      }
    } catch {
      setError('登录失败')
    } finally {
      setBusy(false)
    }
  }

  if (!authed) {
    return (
      <div className="page center">
        <h1>🕯 说书人入口</h1>
        <input
          className="input"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && login()}
          placeholder="说书人密码"
          autoFocus
        />
        <button className="btn primary" onClick={login} disabled={busy}>
          进入魔典
        </button>
        <p className="hint">默认密码 grimoire,可用环境变量 STORYTELLER_PASSWORD 修改</p>
        {error && <p className="error">{error}</p>}
      </div>
    )
  }

  const doAction = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    setError('')
    try {
      await fn()
    } catch (e) {
      setError(e instanceof Error ? e.message : '操作失败')
    } finally {
      setBusy(false)
    }
  }

  const players = view?.players ?? []

  return (
    <div className="page st">
      <div className="st-head">
        <h1>🕯 魔典</h1>
        <span className="sub">血染钟楼 · 说书人控制台</span>
        <div className="st-actions">
          <button
            className="btn primary"
            disabled={busy || view?.status === 'playing'}
            onClick={() => doAction(() => stApi('/api/assign', { method: 'POST' }))}
          >
            🎲 随机分配角色
          </button>
          <button
            className="btn danger"
            disabled={busy}
            onClick={() => {
              if (confirm('确定重置本局?所有玩家将退出。')) doAction(() => stApi('/api/reset', { method: 'POST' }))
            }}
          >
            重置本局
          </button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="st-body">
        <div className="st-left">
          <h3>
            玩家 ({players.length} 人{view?.status === 'playing' ? ' · 游戏中' : ' · 等待开局'})
          </h3>
          {players.length === 0 && (
            <p className="hint">还没有玩家,让他们扫右边的二维码加入(至少 5 人才能分配角色)</p>
          )}
          <ul className="st-players">
            {players.map((p) => (
              <li key={p.id} className={p.alive ? '' : 'dead'}>
                <span className="seat">{p.seat}</span>
                <span className="pname">{p.name}</span>
                {p.role && (
                  <span className={`team-badge team-${p.role.team}`}>
                    {TEAM_LABEL[p.role.team]} · {p.role.name}
                  </span>
                )}
                <span className="spacer" />
                <button
                  className="btn small"
                  disabled={busy}
                  onClick={() => doAction(() => stApi(`/api/player/${p.id}/alive`, { method: 'POST' }))}
                >
                  {p.alive ? '☠ 标记死亡' : '复活'}
                </button>
                <button
                  className="btn small ghost"
                  disabled={busy}
                  onClick={() => {
                    if (confirm(`移除 ${p.name}?`)) doAction(() => stApi(`/api/player/${p.id}/remove`, { method: 'POST' }))
                  }}
                >
                  移除
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="st-right">
          <h3>玩家加入</h3>
          {qr && <img src={qr} alt="加入二维码" className="qr" />}
          {joinUrl && <p className="url">{joinUrl}</p>}
          <p className="hint">玩家手机连同一 WiFi 后,用相机扫码即可加入</p>
        </div>
      </div>
    </div>
  )
}
