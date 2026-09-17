import { useEffect, useState } from 'react'
import { openSocket, PLAYER_ID_KEY } from './api'
import type { PlayerView, Team } from './types'

const TEAM_LABEL: Record<Team, string> = {
  townsfolk: '镇民',
  outsider: '外来者',
  minion: '爪牙',
  demon: '恶魔',
}

export default function RoleCard({ playerId }: { playerId: string }) {
  const [view, setView] = useState<PlayerView | null>(null)
  const [wsStatus, setWsStatus] = useState('connecting')

  useEffect(() => {
    let alive = true
    const ws = openSocket<PlayerView>(
      `who=${playerId}`,
      (v) => {
        setView(v)
        setWsStatus('live')
      },
      {
        keepAlive: () => alive,
        onFatal: () => {
          // 身份失效(被移除/本局已重置)
          localStorage.removeItem(PLAYER_ID_KEY)
          location.reload()
        },
      },
    )
    ws.onopen = () => setWsStatus('live')
    ws.onerror = () => setWsStatus('offline')
    return () => {
      alive = false
      ws.close()
    }
  }, [playerId])

  if (!view) return <div className="page center">连接中…</div>

  const { me, status, players } = view
  const role = me.role

  return (
    <div className="page rolecard">
      <div className="topbar">
        <span>
          座位 {me.seat} · {me.name}
        </span>
        <span
          className={wsStatus === 'live' ? 'dot ok' : 'dot bad'}
          title={wsStatus === 'live' ? '已连接' : '连接中断,重连中…'}
        />
      </div>

      {status === 'lobby' || !role ? (
        <div className="center grow">
          <p className="sub">已入座,等待说书人分配角色…</p>
          <p className="hint">把手机收好,别让别人看到屏幕</p>
        </div>
      ) : (
        <div className={`card team-${role.team} ${me.alive ? '' : 'dead'}`}>
          <div className="card-head">
            <span className="team-badge">{TEAM_LABEL[role.team]}</span>
            <span className="en">{role.en}</span>
          </div>
          <h2 className="role-name">{role.name}</h2>
          <p className="ability">{role.ability}</p>
          {!me.alive && <p className="death-note">☠ 你已死亡:夜晚请闭眼,白天可以继续发言</p>}
        </div>
      )}

      <div className="players">
        {players.map((p) => (
          <div key={p.id} className={`player-row ${p.alive ? '' : 'dead'}`}>
            <span className="seat">{p.seat}</span>
            <span className="pname">{p.name}</span>
            <span className="pstate">{p.alive ? '存活' : '☠'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
