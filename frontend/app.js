/* 血染钟楼说书人工具 · 前端(无构建,由 FastAPI 直接托管) */
'use strict'

const ST_PASSWORD_KEY = 'botc_st_password'
const PLAYER_ID_KEY = 'botc_player_id'
const TEAM_LABEL = { townsfolk: '镇民', outsider: '外来者', minion: '爪牙', demon: '恶魔' }
const app = document.getElementById('app')

function h(html) {
  const t = document.createElement('template')
  t.innerHTML = html.trim()
  return t.content.firstElementChild
}

function esc(s) {
  const d = document.createElement('div')
  d.textContent = s
  return d.innerHTML
}

async function api(path, init) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error((body && body.detail) || `HTTP ${res.status}`)
  }
  return res.json()
}

function stApi(path, init) {
  const password = localStorage.getItem(ST_PASSWORD_KEY) || ''
  return api(path, { ...init, headers: { 'X-Storyteller-Password': password, ...(init?.headers || {}) } })
}

function openSocket(query, onMessage, onFatal) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws?${query}`)
  ws.onmessage = (e) => onMessage(JSON.parse(e.data))
  ws.onclose = (e) => {
    // 4001 身份失效(被移除/重置),4003 密码错误 → 不再重连
    if (e.code === 4001 || e.code === 4003) {
      if (onFatal) onFatal()
      return
    }
    setTimeout(() => openSocket(query, onMessage, onFatal), 1500) // 断线重连
  }
  return ws
}

// ================= 加入页 =================

function renderJoin() {
  app.replaceChildren(h(`<div class="page center">
    <h1>🩸 血染钟楼</h1>
    <p class="sub">输入名字加入本局</p>
    <input class="input" id="name" placeholder="你的名字" maxlength="20" autofocus>
    <button class="btn primary" id="join-btn">加入</button>
    <p class="error" id="err" style="display:none"></p>
  </div>`))
  const input = document.getElementById('name')
  const btn = document.getElementById('join-btn')
  const err = document.getElementById('err')
  async function join() {
    const name = input.value.trim()
    if (!name) return
    btn.disabled = true
    try {
      const res = await api('/api/join', { method: 'POST', body: JSON.stringify({ name }) })
      localStorage.setItem(PLAYER_ID_KEY, res.player_id)
      renderRoleCard(res.player_id)
    } catch (e) {
      err.textContent = e.message
      err.style.display = ''
      btn.disabled = false
    }
  }
  btn.onclick = join
  input.onkeydown = (e) => {
    if (e.key === 'Enter') join()
  }
}

// ================= 玩家角色卡 =================

function renderRoleCard(playerId) {
  app.replaceChildren(h('<div class="page center">连接中…</div>'))
  function paint(view) {
    const { me, status, players } = view
    const role = me.role
    const rows = players.map((p) => `
      <div class="player-row ${p.alive ? '' : 'dead'}">
        <span class="seat">${p.seat}</span><span class="pname">${esc(p.name)}</span>
        <span class="pstate">${p.alive ? '存活' : '☠'}</span>
      </div>`).join('')
    const body = status === 'lobby' || !role
      ? `<div class="center grow"><p class="sub">已入座,等待说书人分配角色…</p>
         <p class="hint">把手机收好,别让别人看到屏幕</p></div>`
      : `<div class="card team-${role.team} ${me.alive ? '' : 'dead'}">
          <div class="card-head">
            <span class="team-badge">${TEAM_LABEL[role.team]}</span>
            <span class="en">${esc(role.en)}</span>
          </div>
          <h2 class="role-name">${esc(role.name)}</h2>
          <p class="ability">${esc(role.ability)}</p>
          ${me.alive ? '' : '<p class="death-note">☠ 你已死亡:夜晚请闭眼,白天可以继续发言</p>'}
        </div>`
    app.replaceChildren(h(`<div class="page rolecard">
      <div class="topbar"><span>座位 ${me.seat} · ${esc(me.name)}</span><span class="dot ok" title="已连接"></span></div>
      ${body}
      <div class="players">${rows}</div>
    </div>`))
  }
  const ws = openSocket(`who=${playerId}`, paint, () => {
    // 身份失效(被移除/本局已重置)→ 回加入页
    localStorage.removeItem(PLAYER_ID_KEY)
    location.reload()
  })
  window.addEventListener('beforeunload', () => ws.close())
}

// ================= 说书人魔典 =================

function renderStoryteller() {
  if (!localStorage.getItem(ST_PASSWORD_KEY)) {
    app.replaceChildren(h(`<div class="page center">
      <h1>🕯 说书人入口</h1>
      <input class="input" id="pw" type="password" placeholder="说书人密码" autofocus>
      <button class="btn primary" id="login-btn">进入魔典</button>
      <p class="hint">默认密码 grimoire,可用环境变量 STORYTELLER_PASSWORD 修改</p>
      <p class="error" id="err" style="display:none"></p>
    </div>`))
    const pw = document.getElementById('pw')
    const btn = document.getElementById('login-btn')
    const err = document.getElementById('err')
    async function login() {
      btn.disabled = true
      try {
        const { ok } = await api('/api/login', { method: 'POST', body: JSON.stringify({ password: pw.value }) })
        if (ok) {
          localStorage.setItem(ST_PASSWORD_KEY, pw.value)
          renderStoryteller()
        } else {
          err.textContent = '密码错误'
          err.style.display = ''
          btn.disabled = false
        }
      } catch (e) {
        err.textContent = '登录失败'
        err.style.display = ''
        btn.disabled = false
      }
    }
    btn.onclick = login
    pw.onkeydown = (e) => {
      if (e.key === 'Enter') login()
    }
    return
  }

  app.replaceChildren(h('<div class="page center">连接魔典…</div>'))
  function paint(view) {
    const players = view.players
    const rows = players.length === 0
      ? '<p class="hint">还没有玩家,让他们扫右边的二维码加入(至少 5 人才能分配角色)</p>'
      : players.map((p) => `
        <li class="${p.alive ? '' : 'dead'}" data-id="${p.id}">
          <span class="seat">${p.seat}</span>
          <span class="pname">${esc(p.name)}</span>
          ${p.role ? `<span class="team-badge team-${p.role.team}">${TEAM_LABEL[p.role.team]} · ${esc(p.role.name)}</span>` : ''}
          <span class="spacer"></span>
          <button class="btn small act-alive">${p.alive ? '☠ 标记死亡' : '复活'}</button>
          <button class="btn small ghost act-remove">移除</button>
        </li>`).join('')
    app.replaceChildren(h(`<div class="page st">
      <div class="st-head">
        <h1>🕯 魔典</h1>
        <span class="sub">血染钟楼 · 说书人控制台</span>
        <div class="st-actions">
          <button class="btn primary" id="assign-btn" ${view.status === 'playing' ? 'disabled' : ''}>🎲 随机分配角色</button>
          <button class="btn danger" id="reset-btn">重置本局</button>
        </div>
      </div>
      <p class="error" id="err" style="display:none"></p>
      <div class="st-body">
        <div class="st-left">
          <h3>玩家 (${players.length} 人${view.status === 'playing' ? ' · 游戏中' : ' · 等待开局'})</h3>
          <ul class="st-players">${rows}</ul>
        </div>
        <div class="st-right">
          <h3>玩家加入</h3>
          <img src="/api/qr" alt="加入二维码" class="qr">
          <p class="hint">玩家手机连同一 WiFi 后,用相机扫码即可加入</p>
        </div>
      </div>
    </div>`))

    const err = document.getElementById('err')
    async function act(fn) {
      try {
        await fn()
      } catch (e) {
        err.textContent = e.message
        err.style.display = ''
      }
    }
    document.getElementById('assign-btn').onclick = () => act(() => stApi('/api/assign', { method: 'POST' }))
    document.getElementById('reset-btn').onclick = () => {
      if (confirm('确定重置本局?所有玩家将退出。')) act(() => stApi('/api/reset', { method: 'POST' }))
    }
    app.querySelectorAll('.act-alive').forEach((b) => {
      b.onclick = () => act(() => stApi(`/api/player/${b.closest('li').dataset.id}/alive`, { method: 'POST' }))
    })
    app.querySelectorAll('.act-remove').forEach((b) => {
      b.onclick = () => {
        const li = b.closest('li')
        const name = li.querySelector('.pname').textContent
        if (confirm(`移除 ${name}?`)) act(() => stApi(`/api/player/${li.dataset.id}/remove`, { method: 'POST' }))
      }
    })
  }
  const pw = encodeURIComponent(localStorage.getItem(ST_PASSWORD_KEY) || '')
  const ws = openSocket(`who=storyteller&pw=${pw}`, paint)
  window.addEventListener('beforeunload', () => ws.close())
}

// ================= 入口(hash 路由) =================

if (location.hash.startsWith('#/storyteller')) {
  renderStoryteller()
} else {
  const playerId = localStorage.getItem(PLAYER_ID_KEY)
  if (playerId) {
    api(`/api/me/${playerId}`)
      .then(() => renderRoleCard(playerId))
      .catch(() => {
        localStorage.removeItem(PLAYER_ID_KEY)
        renderJoin()
      })
  } else {
    renderJoin()
  }
}
window.addEventListener('hashchange', () => location.reload())
