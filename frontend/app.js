/* 血染钟楼说书人工具 · 前端(无构建,由 FastAPI 直接托管) */
'use strict'

const ST_PASSWORD_KEY = 'botc_st_password'
const PLAYER_ID_KEY = 'botc_player_id'
const TEAM_LABEL = { townsfolk: '镇民', outsider: '外来者', minion: '爪牙', demon: '恶魔' }
const TEAM_INDEX = { townsfolk: 0, outsider: 1, minion: 2, demon: 3 } // 配比 [镇,外,爪,恶] 的下标
const TEAM_ORDER = [['townsfolk', '镇民'], ['outsider', '外来者'], ['minion', '爪牙'], ['demon', '恶魔']]
const MARKER_LABEL = { poisoned: '中毒', drunk: '醉酒', mad: '疯狂' }
const MARKER_CHAR = { poisoned: '中', drunk: '醉', mad: '疯' }
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
    ...init,
    // headers 必须放在 ...init 之后合并:否则 init.headers(如 X-Storyteller-Password)
    // 会整体覆盖 Content-Type,浏览器默认 text/plain,FastAPI 收到字符串直接 422
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    // 422 校验失败时 detail 是数组:[{loc: ['body','player_count'], msg: ...}, ...]
    const detail = Array.isArray(body && body.detail)
      ? body.detail.map((d) => `${(d.loc || []).join('.')}: ${d.msg}`).join('; ')
      : body && body.detail
    throw new Error(detail || `HTTP ${res.status}`)
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
    const badge = opts.draftBadge ? opts.draftBadge(s) : null // { name, team }
    const voted = opts.voted ? opts.voted(s) : false // 投票中该座举手
    const markers = opts.markers ? opts.markers(s) : [] // 状态标记(仅说书人)
    const node = h(`<div class="seat-node ${p ? 'occ' : 'free'} ${p && !p.alive ? 'dead' : ''} ${s.is_me ? 'mine' : ''} ${voted ? 'voted' : ''} ${teamCls}"
        data-seat="${s.seat}" style="left:${(50 + 38 * Math.cos(a)).toFixed(2)}%;top:${(50 + 38 * Math.sin(a)).toFixed(2)}%">
      <span class="seat-num">${s.seat}</span>
      <span class="seat-name">${p ? esc(p.name) : (opts.freeLabel || '入座')}</span>
      ${badge ? `<span class="draft-badge team-${badge.team}">${esc(badge.name)}</span>` : ''}
      ${markers.map((m) => `<span class="marker-badge m-${m}">${MARKER_CHAR[m]}</span>`).join('')}
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
    const { me, status, seats, phase, night_no: nightNo, day_no: dayNo, current } = view

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
    // 预发身份时入座即继承角色:只要有角色就显示角色卡(即使本局还在 lobby 等人)
    const card = !role
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
    // 白天/夜晚进度(公开)+ 投票实时票数(公开,举手票型)
    const phaseTxt = status === 'playing'
      ? (phase === 'night' ? ` · 🌙 第 ${nightNo} 夜` : phase === 'day' ? ` · ☀️ 第 ${dayNo} 天` : '')
      : ''
    const voteLine = current
      ? `<p class="vote-public">🗳 座${current.nominator} 提名座${current.nominee} · 赞成 ${current.votes.length} 票</p>`
      : ''
    app.replaceChildren(h(`<div class="page rolecard">
      <div class="topbar"><span>座位 ${me.seat} · ${esc(me.name)}${phaseTxt}</span><span class="dot ok" title="已连接"></span></div>
      <div id="circle"></div>
      ${voteLine}
      ${card}
      ${role && status === 'lobby' ? '<p class="hint">身份已到手,等待其他玩家入座开局…</p>' : ''}
    </div>`))
    document.getElementById('circle').appendChild(seatCircle(seats, {
      voted: (s) => !!current && current.votes.includes(s.seat), // 举手票型公开,玩家也可见
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
  let manual = false // 手动发身份模式
  let draft = {} // 手动模式草稿:座位号 → 角色 id
  let godfatherAdj = 1 // 教父外来者调整:说书人可选 +1 或 −1,默认 +1

  function paint(view) {
    const { status, script, player_count: count, scripts, seats, roles, composition,
      adjust_roles, seat_roles, phase, night_no: nightNo, day_no: dayNo, night,
      nominations, current, alive_count: aliveCount, quorum, saved_at: savedAt } = view
    const minP = scripts.find((s) => s.id === script)?.min || 5 // 该板子的人数下限(瓦釜雷鸣 7 人起)
    const seatedCount = seats.filter((s) => s.player).length
    if (status === 'playing') { manual = false; draft = {} } // 发牌完成后退出草稿
    const allSeated = seatedCount === count
    const selSeat = seats.find((s) => s.seat === selected)
    const selP = selSeat && selSeat.player
    const seatNames = {}
    seats.forEach((s) => { if (s.player) seatNames[s.seat] = s.player.name })
    const phaseTxt = status === 'playing'
      ? (phase === 'night' ? `🌙 第 ${nightNo} 夜` : phase === 'day' ? `☀️ 第 ${dayNo} 天` : '')
      : ''

    app.replaceChildren(h(`<div class="page st">
      <div class="st-head">
        <h1>🕯 魔典</h1>
        <span class="sub">血染钟楼 · 说书人控制台${savedAt ? ' · 💾 自动存档' : ''}</span>
        <div class="st-actions">
          ${status === 'playing' ? `<span class="phase-badge ${phase}">${phaseTxt}</span>` : ''}
          ${status === 'lobby'
            ? `<button class="btn ${manual ? 'primary' : ''}" id="manual-btn">${manual ? '✖ 退出手动' : '🃏 手动发身份'}</button>`
            : ''}
          <button class="btn primary" id="assign-btn" ${status === 'playing' || !allSeated || manual ? 'disabled' : ''}>🎲 随机分配角色</button>
          <button class="btn small ghost" id="load-btn" title="从磁盘恢复上次自动存档">💾 读档</button>
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
            <p class="hint">已入座 ${seatedCount}/${count}${status === 'playing' ? ' · 游戏中' : ' · 等待开局'}${allSeated && status === 'lobby' ? ' · 可以分配角色' : ''}${!allSeated && seat_roles && Object.keys(seat_roles).length === count ? ' · 已预发身份,等玩家入座' : ''}</p>
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

    const roleById = Object.fromEntries(roles.map((r) => [r.id, r]))

    // ---- 手动发身份面板(草稿只在前端,确认后才提交) ----
    function renderManualPicker(detail, selSeat) {
      const picked = [0, 0, 0, 0]
      const draftRoles = [...new Set(Object.values(draft))] // 去重:旧服务端可能存有重复角色
      for (const rid of draftRoles) {
        const r = roleById[rid]
        if (r) picked[TEAM_INDEX[r.team]]++
      }
      // 教父的外来者调整可 +1 可 −1(说书人选择),其余调整角色用固定值
      const effAdj = (rid) => (rid === 'godfather' && adjust_roles[rid])
        ? [-godfatherAdj, godfatherAdj, 0, 0]
        : adjust_roles[rid]
      const expected = [...composition]
      for (const rid of draftRoles) {
        const adj = effAdj(rid)
        if (adj) {
          expected[0] += adj[0]; expected[1] += adj[1]; expected[2] += adj[2]; expected[3] += adj[3]
        }
      }
      if (expected[1] < 0) { expected[0] += expected[1]; expected[1] = 0 }
      const ok = picked[3] === 1 && picked[2] >= 1
      const full = Object.keys(draft).length === count
      // 调整角色导致的配比变化:标出是哪个角色、改了什么(如 方古:−1镇/+1外)
      const ADJ_NAMES = ['镇', '外', '爪', '恶']
      const adjTexts = []
      for (const rid of draftRoles) {
        const adj = effAdj(rid)
        if (adj) {
          const parts = []
          adj.forEach((d, i) => { if (d) parts.push(`${d > 0 ? '+' : ''}${d}${ADJ_NAMES[i]}`) })
          adjTexts.push(`${roleById[rid].name}:${parts.join('/')}`)
        }
      }
      const adjLine = adjTexts.length
        ? `<p class="manual-adjust">配比调整:${adjTexts.map(esc).join(' · ')}</p>`
        : ''
      // 重复角色(如旧服务端残留的预发数据)禁止提交:与后端校验一致
      const hasDup = new Set(Object.values(draft)).size !== Object.keys(draft).length
      // 教父在场时,外来者 ±1 由说书人选择(点按钮切换,配比与标注实时联动)
      const gfChoice = draftRoles.includes('godfather') && adjust_roles.godfather
        ? `<div class="manual-gf"><span class="hint">教父 外来者调整:</span>
            <button class="chip ${godfatherAdj === 1 ? 'on' : ''}" data-gf="1">+1 外来者</button>
            <button class="chip ${godfatherAdj === -1 ? 'on' : ''}" data-gf="-1">−1 外来者</button>
          </div>`
        : ''
      const summaryTxt = TEAM_ORDER.map(([t, l]) => {
        const i = TEAM_INDEX[t]
        // 与基础配比不同 → 目标数变金色,提示配比被调整角色改变了
        const exp = expected[i] !== composition[i] ? `<span class="delta">${expected[i]}</span>` : expected[i]
        return `${l} ${picked[i]}/${exp}`
      }).join(' · ')
      const box = h(`<div class="st-detail">
        <h3>🃏 手动发身份${selSeat ? ` · 座位 ${selSeat.seat}${selSeat.player ? `(${esc(selSeat.player.name)})` : '(空)'}` : ''}</h3>
        <p class="manual-summary ${full && ok && !hasDup ? '' : 'warn'}">${summaryTxt}${hasDup ? ' · ⚠ 角色重复,请先取消重复项' : ''}</p>
        ${adjLine}
        ${gfChoice}
        <p class="hint">${selSeat ? (selSeat.player ? '点击角色发给该座位,再点一次取消' : '该座还没人:可以先发身份,玩家入座自动继承') : '先点击环形座位,再选角色'}</p>
      </div>`)
      const usedBy = {} // 角色 id → 已发的座位号(角色全局唯一,已发出的不可再发)
      for (const [seat, rid] of Object.entries(draft)) usedBy[rid] = Number(seat)
      TEAM_ORDER.forEach(([team, label]) => {
        const group = h(`<div class="role-group"><span class="team-badge team-${team}">${label}</span></div>`)
        roles.filter((r) => r.team === team).forEach((r) => {
          const on = selSeat && draft[selSeat.seat] === r.id
          const usedSeat = usedBy[r.id]
          const usedElsewhere = usedSeat != null && (!selSeat || usedSeat !== selSeat.seat)
          const chip = h(`<button class="chip team-${r.team} ${on ? 'on' : ''} ${usedElsewhere ? 'used' : ''}"
              title="${esc(r.ability)}${usedElsewhere ? `&#10;已发:座位 ${usedSeat}` : ''}">
              ${esc(r.name)}${usedElsewhere ? `<span class="chip-used">座${usedSeat}</span>` : ''}</button>`)
          chip.onclick = () => {
            if (!selSeat || usedElsewhere) return // 已发到别的座位 → 禁止重复发
            if (draft[selSeat.seat] === r.id) delete draft[selSeat.seat]
            else draft[selSeat.seat] = r.id
            paint(view)
          }
          group.appendChild(chip)
        })
        box.appendChild(group)
      })
      box.appendChild(h(`<div class="st-detail-actions">
        <button class="btn primary small" id="manual-confirm" ${full && ok && !hasDup ? '' : 'disabled'}>✅ 确认发身份</button>
        <button class="btn small ghost" id="manual-cancel">取消</button>
      </div>`))
      detail.replaceChildren(box)
      box.querySelectorAll('[data-gf]').forEach((b) => {
        b.onclick = () => { godfatherAdj = Number(b.dataset.gf); paint(view) }
      })
      document.getElementById('manual-confirm').onclick = () => act(() => {
        const assignments = Object.entries(draft).map(([seat, role]) => ({ seat: Number(seat), role }))
        return stApi('/api/assign/manual', { method: 'POST', body: JSON.stringify({ assignments }) })
          .then((v) => { manual = false; draft = {}; selected = null; paint(v) })
          // 空座预发时状态仍是 lobby,直接以响应视图重绘(不等推送)
      })
      document.getElementById('manual-cancel').onclick = () => { manual = false; draft = {}; paint(view) }
    }

    // ---- 选中玩家详情条(夜晚/白天面板顶部复用) ----

    function markerRow(slot) {
      const ms = slot.markers || []
      return `<div class="st-markers"><span class="hint">标记:</span>
        ${Object.entries(MARKER_LABEL).map(([k, l]) =>
          `<button class="chip ${ms.includes(k) ? 'on' : ''} marker-chip m-${k}" data-mk="${k}">${l}</button>`).join('')}
      </div>`
    }

    function selPDetailHtml(slot, p) {
      return `<div class="st-detail sel-strip ${p.alive ? '' : 'dead'}">
        <h3>座位 ${p.seat} · ${esc(p.name)}</h3>
        ${p.role
          ? `<span class="team-badge team-${p.role.team}">${TEAM_LABEL[p.role.team]} · ${esc(p.role.name)}</span>`
          : '<p class="hint">未分配角色</p>'}
        ${fakeRow(slot)}
        ${markerRow(slot)}
        <div class="st-detail-actions">
          <button class="btn small" id="act-alive">${p.alive ? '☠ 标记死亡' : '复活'}</button>
          <button class="btn small ghost" id="act-remove">移除</button>
        </div>
      </div>`
    }

    function wireSelPDetail() {
      const aliveBtn = document.getElementById('act-alive')
      if (aliveBtn && selP) aliveBtn.onclick = () => act(() => stApi(`/api/player/${selP.id}/alive`, { method: 'POST' }))
      const removeBtn = document.getElementById('act-remove')
      if (removeBtn && selP) removeBtn.onclick = () => {
        if (confirm(`移除 ${selP.name}?`)) act(() => stApi(`/api/player/${selP.id}/remove`, { method: 'POST' }))
      }
      detail.querySelectorAll('.marker-chip').forEach((c) => {
        c.onclick = () => act(() => stApi('/api/marker', {
          method: 'POST',
          body: JSON.stringify({ seat: selSeat.seat, marker: c.dataset.mk, on: !(selSeat.markers || []).includes(c.dataset.mk) }),
        }))
      })
    }

    // ---- 夜晚流程助手 ----

    function renderNightPanel(detail) {
      const strip = selP ? selPDetailHtml(selSeat, selP) : ''
      const steps = night.steps
      const cur = steps[night.idx]
      let wake = []
      if (cur) {
        if (cur.key === 'minioninfo') wake = seats.filter((s) => s.player && s.player.role && s.player.role.team === 'minion')
        else if (cur.key === 'demoninfo') wake = seats.filter((s) => s.player && s.player.role && s.player.role.team === 'demon')
        else if (cur.fake_for != null) wake = seats.filter((s) => s.seat === cur.fake_for)
        else if (cur.key !== 'dusk' && cur.key !== 'dawn') wake = seats.filter((s) => s.player && s.player.role && s.player.role.id === cur.key)
      }
      const wakeTxt = wake.length
        ? '唤醒:' + wake.map((s) => `座${s.seat} ${esc(s.player.name)}${s.player.alive ? '' : ' ☠'}`).join('、')
        : (cur && cur.key !== 'dusk' && cur.key !== 'dawn' ? '该角色不在场,此步可跳过' : '')
      const fakeNote = cur && cur.fake_for != null ? ` · 🍺 酒鬼扮演(座${cur.fake_for})` : ''
      const box = h(`<div class="st-detail">
        ${strip}
        <div class="night-panel">
          <h3>🌙 第 ${nightNo} 夜 · 步骤 ${night.idx + 1}/${steps.length}</h3>
          ${cur ? `<div class="step-card">
            <div class="step-name">${esc(cur.name)}${fakeNote}</div>
            ${wakeTxt ? `<div class="step-seats">${wakeTxt}</div>` : ''}
            <p class="step-hint">${esc(cur.hint)}</p>
          </div>` : '<p class="hint">本夜没有步骤</p>'}
          <div class="step-list">
            ${steps.map((st, i) => `<button class="step-chip ${i < night.idx ? 'done' : ''} ${i === night.idx ? 'cur' : ''}"
                title="${esc(st.name)}${st.fake_for != null ? ` · 酒鬼扮演(座${st.fake_for})` : ''}">${i + 1} ${esc(st.name)}${st.fake_for != null ? ' 🍺' : ''}</button>`).join('')}
          </div>
          <div class="st-detail-actions">
            <button class="btn small ghost" id="night-prev" ${night.idx <= 0 ? 'disabled' : ''}>← 上一步</button>
            ${night.idx + 1 < steps.length
              ? '<button class="btn small primary" id="night-next">下一步 →</button>'
              : '<button class="btn small primary" id="night-dawn">🌅 天亮</button>'}
          </div>
        </div>
      </div>`)
      detail.replaceChildren(box)
      wireSelPDetail()
      box.querySelectorAll('.step-chip').forEach((c, i) => {
        c.onclick = () => act(() => stApi('/api/night/goto', { method: 'POST', body: JSON.stringify({ idx: i }) }))
      })
      const prev = document.getElementById('night-prev')
      if (prev) prev.onclick = () => act(() => stApi('/api/night/prev', { method: 'POST' }))
      const next = document.getElementById('night-next')
      if (next) next.onclick = () => act(() => stApi('/api/night/next', { method: 'POST' }))
      const dawn = document.getElementById('night-dawn')
      if (dawn) dawn.onclick = () => act(() => stApi('/api/night/next', { method: 'POST' }))
    }

    // ---- 白天面板:提名 → 投票 → 处决 ----

    function renderDayPanel(detail) {
      const strip = selP ? selPDetailHtml(selSeat, selP) : ''
      const seatOpts = seats.filter((s) => s.player)
        .map((s) => `<option value="${s.seat}">座${s.seat} · ${esc(s.player.name)}${s.player.alive ? '' : ' ☠'}</option>`).join('')
      const todays = nominations.filter((n) => n.day === dayNo)
      const hist = todays.length
        ? `<h4>今日提名</h4>` + todays.map((n) => `<div class="nom-row ${n.executed ? 'exec' : ''}">
            座${n.nominator} ${esc(seatNames[n.nominator] || '?')} 提名 座${n.nominee} ${esc(seatNames[n.nominee] || '?')}
            · ${n.votes.length} 票 ${n.executed ? '· ⚔ 处决' : '· 未处决'}</div>`).join('')
        : '<p class="hint">今天还没有提名</p>'
      const voting = current
        ? `<div class="vote-box">
            <p class="vote-title">🗳 座${current.nominator} ${esc(seatNames[current.nominator] || '?')} 提名
              座${current.nominee} ${esc(seatNames[current.nominee] || '?')}</p>
            <p class="vote-line ${current.votes.length >= quorum ? 'ok' : ''}">赞成 ${current.votes.length} 票 · 需 ≥${quorum} 票(存活 ${aliveCount} 人)</p>
            <p class="hint">点击环形座位记录举手;死者投票由说书人把握</p>
            <div class="st-detail-actions">
              <button class="btn small danger" id="nom-exec">⚔ 处决</button>
              <button class="btn small ghost" id="nom-skip">无效(不足/平票)</button>
            </div>
          </div>`
        : `<div class="vote-box"><div class="nom-start">
            <select id="nom-from">${seatOpts}</select><span class="hint">提名</span>
            <select id="nom-to">${seatOpts}</select>
            <button class="btn small primary" id="nom-go">发起提名</button>
          </div></div>`
      const box = h(`<div class="st-detail">
        ${strip}
        <div class="day-panel">
          <h3>☀️ 第 ${dayNo} 天 · 存活 ${aliveCount} 人</h3>
          ${voting}
          ${hist}
          <div class="st-detail-actions"><button class="btn small primary" id="day-end">🌙 天黑 → 第 ${nightNo + 1} 夜</button></div>
        </div>
      </div>`)
      detail.replaceChildren(box)
      wireSelPDetail()
      const go = document.getElementById('nom-go')
      if (go) go.onclick = () => {
        const from = Number(document.getElementById('nom-from').value)
        const to = Number(document.getElementById('nom-to').value)
        act(() => stApi('/api/nomination', { method: 'POST', body: JSON.stringify({ nominator: from, nominee: to }) }))
      }
      const exe = document.getElementById('nom-exec')
      if (exe) exe.onclick = () => {
        if (confirm('⚔ 处决被提名者?')) act(() => stApi('/api/nomination/resolve', { method: 'POST', body: JSON.stringify({ executed: true }) }))
      }
      const skip = document.getElementById('nom-skip')
      if (skip) skip.onclick = () => act(() => stApi('/api/nomination/resolve', { method: 'POST', body: JSON.stringify({ executed: false }) }))
      const end = document.getElementById('day-end')
      if (end) end.onclick = () => act(() => stApi('/api/day/end', { method: 'POST' }))
    }

    // ---- 环形座位 ----
    document.getElementById('circle').appendChild(seatCircle(seats, {
      freeLabel: '空',
      draftBadge: (s) => {
        // 手动模式显示草稿;非手动时,空座上的预发身份也显示在徽章里。徽章按阵营配色
        const badgeOf = (rid) => ({ name: roleById[rid].name, team: roleById[rid].team })
        if (manual && draft[s.seat] && roleById[draft[s.seat]]) return badgeOf(draft[s.seat])
        if (!s.player && seat_roles && seat_roles[s.seat] && roleById[seat_roles[s.seat]]) {
          return badgeOf(seat_roles[s.seat])
        }
        return null
      },
      voted: (s) => status === 'playing' && phase === 'day' && current && s.player && current.votes.includes(s.seat),
      markers: (s) => s.markers || [],
      clickSeat: (s) => {
        // 投票进行中:点座位 = 记录举手/放下
        if (status === 'playing' && phase === 'day' && current && s.player) {
          act(() => stApi('/api/nomination/vote', { method: 'POST', body: JSON.stringify({ seat: s.seat }) }))
          return
        }
        selected = s.seat
        paint(view)
      },
    }))

    // ---- 选中玩家详情 ----
    const detail = document.getElementById('detail')
    // 认知覆盖:酒鬼座位由说书人标记「玩家看到哪个镇民角色」,真实身份只有说书人可见
    const fakeRow = (slot) => {
      const real = slot.player ? slot.player.role : slot.assigned_role
      if (!real || real.id !== 'drunk') return ''
      const cur = slot.fake_role
      return `<div class="st-fake"><span class="hint">🍺 酒鬼看到:</span>
        <select id="fake-sel">
          <option value="">真实身份(酒鬼)</option>
          ${roles.filter((r) => r.team === 'townsfolk').map((r) =>
            `<option value="${r.id}" ${cur && cur.id === r.id ? 'selected' : ''}>${esc(r.name)}</option>`).join('')}
        </select></div>`
    }
    if (manual) {
      renderManualPicker(detail, selSeat)
    } else if (status === 'playing' && phase === 'night') {
      renderNightPanel(detail) // 夜晚流程助手(顶部含选中玩家条)
    } else if (status === 'playing' && phase === 'day') {
      renderDayPanel(detail) // 白天提名投票(顶部含选中玩家条)
    } else if (selP) {
      detail.replaceChildren(h(selPDetailHtml(selSeat, selP)))
      wireSelPDetail()
    } else if (selSeat && selSeat.assigned_role) {
      const r = selSeat.assigned_role
      detail.replaceChildren(h(`<div class="st-detail">
        <h3>座位 ${selSeat.seat} · 空</h3>
        <span class="team-badge team-${r.team}">${TEAM_LABEL[r.team]} · ${esc(r.name)}</span>
        ${fakeRow(selSeat)}
        <p class="hint">身份已预发,等玩家入座自动继承</p>
      </div>`))
    } else {
      detail.replaceChildren(h('<p class="hint">点击环形座位查看/操作玩家</p>'))
    }
    const fakeSelEl = document.getElementById('fake-sel')
    if (fakeSelEl) fakeSelEl.onchange = () => act(() => stApi('/api/fake', {
      method: 'POST',
      body: JSON.stringify({ seat: selSeat.seat, role: fakeSelEl.value || null }),
    }))

    // ---- 配置 ----
    function doConfig(sc, n) {
      n = Number(n)
      if (!Number.isInteger(n) || !sc) { // 参数异常直接提示,而不是发一个必然 422 的请求
        err.textContent = `配置参数异常(板子=${sc}, 人数=${n}),请 Ctrl+F5 刷新后重试`
        err.style.display = ''
        return
      }
      const willClear = seats.some((s) => s.player) || status === 'playing'
        || (seat_roles && Object.keys(seat_roles).length > 0)
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
    const manualBtn = document.getElementById('manual-btn')
    if (manualBtn) {
      manualBtn.onclick = () => {
        manual = !manual
        // 进入手动模式时载入已预发的身份,便于微调;退出则清空草稿
        draft = manual && seat_roles
          ? Object.fromEntries(Object.entries(seat_roles).map(([s, r]) => [Number(s), r]))
          : {}
        paint(view)
      }
    }
    document.getElementById('dec').onclick = () => doConfig(script, count - 1)
    document.getElementById('inc').onclick = () => doConfig(script, count + 1)

    // ---- 分配 / 重置 / 读档 ----
    document.getElementById('assign-btn').onclick = () => act(() => stApi('/api/assign', { method: 'POST' }))
    document.getElementById('reset-btn').onclick = () => {
      if (confirm('确定重置本局?所有玩家将退出。')) act(() => stApi('/api/reset', { method: 'POST' }))
    }
    document.getElementById('load-btn').onclick = () => {
      if (confirm('从磁盘恢复上次自动存档?当前内存状态将被丢弃。')) act(() => stApi('/api/load', { method: 'POST' }))
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
