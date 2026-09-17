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

// ================= 环形座位 =================
// 座位 1 在正上方,顺时针排布

function seatCircle(seats, opts = {}) {
  const wrap = h('<div class="circle-wrap"></div>')
  const n = seats.length
  if (n === 0) return wrap
  seats.forEach((s) => {
    const a = (2 * Math.PI / n) * (s.seat - 1) - Math.PI / 2
    const p = s.player
    const teamCls = p && p.role ? `team-${p.role.team}` : ''
    const node = h(`<div class="seat-node ${p ? 'occ' : 'free'} ${p && !p.alive ? 'dead' : ''} ${s.is_me ? 'mine' : ''} ${teamCls}"
        data-seat="${s.seat}" style="left:${(50 + 38 * Math.cos(a)).toFixed(2)}%;top:${(50 + 38 * Math.sin(a)).toFixed(2)}%">
      <span class="seat-num">${s.seat}</span>
      <span class="seat-name">${p ? esc(p.name) : (opts.freeLabel || '入座')}</span>
    </div>`)
    if (opts.clickSeat) node.addEventListener('click', () => opts.clickSeat(s))
    wrap.appendChild(node)
  })
  return wrap
}

// ================= 加入页 =================

function renderJoin() {
  app.replaceChildren(h(`<div class="page center">
    <h1>🩸 血染钟楼</h1>
    <p class="sub">输入名字加入本局,然后选座入座</p>
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
      renderPlayer(res.player_id)
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

// ================= 玩家视图 =================

function renderPlayer(playerId) {
  app.replaceChildren(h('<div class="page center">连接中…</div>'))
  function paint(view) {
    const { me, status, seats } = view

    // ---- 未入座:选座 ----
    if (me.seat == null) {
      app.replaceChildren(h(`<div class="page rolecard">
        <div class="topbar"><span>${esc(me.name)}</span><span class="dot ok" title="已连接"></span></div>
        <div class="center grow">
          <p class="sub">选择你的座位入座</p>
          <div id="circle"></div>
          <p class="hint">${seats.length ? `共 ${seats.length} 个座位,点一个空座位入座` : '等待说书人设置本局人数…'}</p>
          <p class="error" id="sit-err" style="display:none"></p>
        </div>
      </div>`))
      const err = document.getElementById('sit-err')
      document.getElementById('circle').appendChild(seatCircle(seats, {
        clickSeat: (s) => {
          if (s.player) return
          api(`/api/player/${playerId}/sit`, { method: 'POST', body: JSON.stringify({ seat: s.seat }) })
            .catch((e) => { err.textContent = e.message; err.style.display = '' })
        },
      }))
      return
    }

    // ---- 已入座 ----
    const role = me.role
    const card = status === 'lobby' || !role
      ? `<div class="center"><p class="sub">已入座,等待说书人分配角色…</p>
         <p class="hint">开局前点其他空座位可以换座</p></div>`
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
      <div id="circle"></div>
      ${card}
    </div>`))
    document.getElementById('circle').appendChild(seatCircle(seats, {
      clickSeat: (s) => {
        // 开局前可换座:点空座位移动过去
        if (!s.player && status === 'lobby') {
          api(`/api/player/${playerId}/sit`, { method: 'POST', body: JSON.stringify({ seat: s.seat }) }).catch(() => {})
        }
      },
    }))
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
  let selected = null // 选中的座位号(点击环形座位)

  function paint(view) {
    const { status, script, player_count: count, scripts, seats } = view
    const minP = scripts.find((s) => s.id === script)?.min || 5 // 该板子的人数下限(瓦釜雷鸣 7 人起)
    const seatedCount = seats.filter((s) => s.player).length
    const allSeated = seatedCount === count
    const selSeat = seats.find((s) => s.seat === selected)
    const selP = selSeat && selSeat.player

    app.replaceChildren(h(`<div class="page st">
      <div class="st-head">
        <h1>🕯 魔典</h1>
        <span class="sub">血染钟楼 · 说书人控制台</span>
        <div class="st-actions">
          <button class="btn primary" id="assign-btn" ${status === 'playing' || !allSeated ? 'disabled' : ''}>🎲 随机分配角色</button>
          <button class="btn danger" id="reset-btn">重置本局</button>
        </div>
      </div>
      <p class="error" id="err" style="display:none"></p>
      <div class="st-body">
        <div class="st-left">
          <div class="st-config">
            <label>板子
              <select id="script-select">
                ${scripts.map((s) => `<option value="${s.id}" ${s.id === script ? 'selected' : ''}>${esc(s.name)}( ${esc(s.en)} )</option>`).join('')}
              </select>
            </label>
            <label>人数
              <button class="btn small" id="dec" ${count <= minP ? 'disabled' : ''}>−</button>
              <span class="count">${count}</span>
              <button class="btn small" id="inc" ${count >= 15 ? 'disabled' : ''}>＋</button>
            </label>
            <span class="hint">修改板子/人数会清空座位,玩家需重新入座</span>
          </div>
          <div class="st-circle">
            <div id="circle"></div>
            <p class="hint">已入座 ${seatedCount}/${count}${status === 'playing' ? ' · 游戏中' : ' · 等待开局'}${allSeated && status === 'lobby' ? ' · 可以分配角色' : ''}</p>
          </div>
        </div>
        <div class="st-right">
          <div id="detail"></div>
          <h3>玩家加入</h3>
          <img src="/api/qr" alt="加入二维码" class="qr">
          <p class="hint">玩家手机连同一 WiFi 后,用相机扫码即可加入并选座</p>
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

    // ---- 环形座位 ----
    document.getElementById('circle').appendChild(seatCircle(seats, {
      freeLabel: '空',
      clickSeat: (s) => {
        selected = s.seat
        paint(view)
      },
    }))

    // ---- 选中玩家详情 ----
    const detail = document.getElementById('detail')
    if (selP) {
      detail.replaceChildren(h(`<div class="st-detail ${selP.alive ? '' : 'dead'}">
        <h3>座位 ${selP.seat} · ${esc(selP.name)}</h3>
        ${selP.role
          ? `<span class="team-badge team-${selP.role.team}">${TEAM_LABEL[selP.role.team]} · ${esc(selP.role.name)}</span>`
          : '<p class="hint">未分配角色</p>'}
        <div class="st-detail-actions">
          <button class="btn small" id="act-alive">${selP.alive ? '☠ 标记死亡' : '复活'}</button>
          <button class="btn small ghost" id="act-remove">移除</button>
        </div>
      </div>`))
      document.getElementById('act-alive').onclick = () => act(() => stApi(`/api/player/${selP.id}/alive`, { method: 'POST' }))
      document.getElementById('act-remove').onclick = () => {
        if (confirm(`移除 ${selP.name}?`)) act(() => stApi(`/api/player/${selP.id}/remove`, { method: 'POST' }))
      }
    } else {
      detail.replaceChildren(h('<p class="hint">点击环形座位查看/操作玩家</p>'))
    }

    // ---- 配置 ----
    function doConfig(sc, n) {
      const willClear = seats.some((s) => s.player) || status === 'playing'
      if (willClear && !confirm('修改配置会清空所有座位和角色分配,继续?')) {
        paint(view)
        return
      }
      act(() => stApi('/api/config', { method: 'POST', body: JSON.stringify({ script: sc, player_count: n }) })
        .then(() => { selected = null }))
    }
    document.getElementById('script-select').onchange = (e) => {
      // 切板子时若人数低于新板子下限(瓦釜雷鸣 7 人起),自动抬到下限
      const minNew = scripts.find((s) => s.id === e.target.value)?.min || 5
      doConfig(e.target.value, Math.max(count, minNew))
    }
    document.getElementById('dec').onclick = () => doConfig(script, count - 1)
    document.getElementById('inc').onclick = () => doConfig(script, count + 1)

    // ---- 分配 / 重置 ----
    document.getElementById('assign-btn').onclick = () => act(() => stApi('/api/assign', { method: 'POST' }))
    document.getElementById('reset-btn').onclick = () => {
      if (confirm('确定重置本局?所有玩家将退出。')) act(() => stApi('/api/reset', { method: 'POST' }))
    }
  }

  const pw = encodeURIComponent(localStorage.getItem(ST_PASSWORD_KEY) || '')
  openSocket(`who=storyteller&pw=${pw}`, paint)
}

// ================= 入口(hash 路由) =================

if (location.hash.startsWith('#/storyteller')) {
  renderStoryteller()
} else {
  const playerId = localStorage.getItem(PLAYER_ID_KEY)
  if (playerId) {
    api(`/api/me/${playerId}`)
      .then(() => renderPlayer(playerId))
      .catch(() => {
        localStorage.removeItem(PLAYER_ID_KEY)
        renderJoin()
      })
  } else {
    renderJoin()
  }
}
window.addEventListener('hashchange', () => location.reload())
