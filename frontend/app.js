/* 血染钟楼说书人工具 · 前端(无构建,由 FastAPI 直接托管) */
'use strict'

const ST_PASSWORD_KEY = 'botc_st_password'
// 角落署名(防剽窃水印):玩家页右下角常驻,pointer-events 不挡任何操作
const CREDIT = '<span class="credit">botc-grimoire · github.com/Chenxi-Li24/botc-grimoire</span>'
const PLAYER_ID_KEY = 'botc_player_id'
const TEAM_LABEL = { townsfolk: '镇民', outsider: '外来者', minion: '爪牙', demon: '恶魔', traveler: '旅行者' }
const TEAM_INDEX = { townsfolk: 0, outsider: 1, minion: 2, demon: 3 } // 配比 [镇,外,爪,恶] 的下标
const TEAM_ORDER = [['townsfolk', '镇民'], ['outsider', '外来者'], ['minion', '爪牙'], ['demon', '恶魔']]
const MARKER_LABEL = { poisoned: '中毒', drunk: '醉酒', mad: '疯狂', 'role-change': '角色转变', 'team-change': '阵营转变' }
const MARKER_CHAR = { poisoned: '中', drunk: '醉', mad: '疯', 'role-change': '🔄', 'team-change': '⚖', redherring: '🐟' }
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

// 投票名单:只显示座位号,等宽 chip 自动换行对齐(不显示玩家名字);旅行者显示 🎒 名字(角色公开、阵营保密)
function voteChips(votes, tNames) {
  const names = tNames || {}
  return votes && votes.length
    ? `<span class="vote-chips">${votes.map((v) => `<span class="vote-chip">${typeof v === 'number' ? `${v}号` : `🎒${esc(names[v] || '旅行者')}`}</span>`).join('')}</span>`
    : ''
}

// 提名/投票中的目标展示:座位号 →「X号」,旅行者 id(t1)→「🎒 名字」
function whoTxt(target, tNames) {
  return typeof target === 'number' ? `${target}号` : `🎒${esc((tNames || {})[target] || '旅行者')}`
}

// 两步确认(不弹系统框):第一次点击按钮变「确认?」,3 秒内再点才执行;任何推送重绘都会自动还原
function armClick(btn, armedLabel, action) {
  let timer = null
  btn.addEventListener('click', () => {
    if (btn.dataset.armed === '1') {
      clearTimeout(timer)
      delete btn.dataset.armed
      btn.textContent = btn.dataset.orig
      action()
      return
    }
    btn.dataset.armed = '1'
    if (!btn.dataset.orig) btn.dataset.orig = btn.textContent
    btn.textContent = armedLabel
    timer = setTimeout(() => {
      delete btn.dataset.armed
      btn.textContent = btn.dataset.orig
    }, 3000)
  })
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
    const deadVote = p && !p.alive && s.dead_vote_left // 死者死票未交出:骷髅左边常驻 🗳,举手交出死票后消失
    const markers = opts.markers ? opts.markers(s) : [] // 状态标记(仅说书人)
    const bubble = opts.bubble ? opts.bubble(s) : null // 💬 私聊气泡:同群同色,所有人可见
    const node = h(`<div class="seat-node ${p ? 'occ' : 'free'} ${p && !p.alive ? 'dead' : ''} ${s.is_me ? 'mine' : ''} ${voted ? 'voted' : ''} ${deadVote ? 'dead-vote' : ''} ${teamCls} ${opts.pickSeat === s.seat ? 'pick' : ''}"
        data-seat="${s.seat}" style="left:${(50 + 38 * Math.cos(a)).toFixed(2)}%;top:${(50 + 38 * Math.sin(a)).toFixed(2)}%">
      <span class="seat-num">${s.seat}</span>
      <span class="seat-name">${p ? esc(p.name) : (opts.freeLabel || '入座')}</span>
      ${badge ? `<span class="draft-badge team-${badge.team}">${esc(badge.name)}</span>` : ''}
      ${bubble ? `<span class="seat-bubble" style="background:${bubble}"></span>` : ''}
      ${markers.length || s.role_change || s.team_change ? `<span class="marker-badges">${markers.map((m) => `<span class="marker-badge m-${m}">${MARKER_CHAR[m] || '?'}</span>`).join('')}${s.role_change ? `<span class="marker-badge plain">🔄${esc(s.role_change.name)}</span>` : ''}${s.team_change ? `<span class="marker-badge plain">⚖${s.team_change === 'good' ? '善良' : '邪恶'}</span>` : ''}</span>` : ''}
    </div>`)
    if (opts.clickSeat) node.addEventListener('click', () => opts.clickSeat(s))
    wrap.appendChild(node)
  })
  // 圆盘中央:🕯 说书人(两端都显示;入群时带同色气泡;第一夜吊着摆动)
  const centerBubble = opts.centerBubble ? opts.centerBubble() : null
  wrap.appendChild(h(`<div class="seat-center ${opts.centerHanged ? 'hanged' : ''}">
    ${opts.centerHanged ? '<span class="seat-center-rope">🪢</span>' : ''}
    ${centerBubble ? `<span class="seat-bubble" style="background:${centerBubble}"></span>` : ''}
    <span class="seat-center-icon">🕯</span>
    <span class="seat-center-name">说书人</span>
  </div>`))
  return wrap
}

// 🕯 血染钟楼背景戏剧:第一夜说书人被吊死在钟楼之上(每局每个设备播一次,点击或 5 秒后消失)
function dramaOverlay(roomCode, phase, nightNo, status) {
  if (status !== 'playing' || phase !== 'night' || nightNo !== 1) return
  const key = `botc_drama_${roomCode}`
  if (localStorage.getItem(key)) return
  localStorage.setItem(key, '1')
  const node = h(`<div class="drama">
    <div class="drama-scene">
      <div class="drama-tower">
        <div class="tower-roof"></div>
        <div class="tower-body">
          <div class="tower-clock"><span class="clock-h"></span><span class="clock-m"></span></div>
        </div>
      </div>
      <div class="drama-hang"><span class="drama-rope">🪢</span><span class="drama-body">🕯</span></div>
      <p class="drama-text">第一夜,说书人被吊死在钟楼之上…</p>
      <p class="drama-sub">—— 血染钟楼 · 点击继续 ——</p>
    </div>
  </div>`)
  app.appendChild(node)
  const close = () => {
    if (!node.parentNode) return
    node.classList.add('fadeout')
    setTimeout(() => node.remove(), 600)
  }
  node.onclick = close
  setTimeout(close, 5000)
}

// ================= 加入页 =================

function renderJoin() {
  // 二维码/分享链接形如 #/?room=1234 → 扫码后自动预填房间号
  const hashRoom = new URLSearchParams(location.hash.split('?')[1] || '').get('room') || ''
  app.replaceChildren(h(`<div class="page center">
    <h1>🩸 血染钟楼</h1>
    <p class="sub">输入名字和房间号加入本局,然后选座入座</p>
    <input class="input" id="name" placeholder="你的名字" maxlength="20" autofocus>
    <input class="input" id="room" placeholder="房间号(4位数字)" maxlength="4" inputmode="numeric" value="${esc(hashRoom)}">
    <button class="btn primary" id="join-btn">加入</button>
    <p class="error" id="err" style="display:none"></p>
    ${CREDIT}
  </div>`))
  const input = document.getElementById('name')
  const roomInput = document.getElementById('room')
  const btn = document.getElementById('join-btn')
  const err = document.getElementById('err')
  async function join() {
    const name = input.value.trim()
    const roomCode = roomInput.value.trim()
    if (!name) return
    if (!/^\d{4}$/.test(roomCode)) {
      err.textContent = '房间号需为 4 位数字'
      err.style.display = ''
      return
    }
    btn.disabled = true
    try {
      const res = await api('/api/join', { method: 'POST', body: JSON.stringify({ name, room_code: roomCode }) })
      localStorage.setItem(PLAYER_ID_KEY, res.player_id)
      renderPlayer(res.player_id)
    } catch (e) {
      err.textContent = e.message
      err.style.display = ''
      btn.disabled = false
    }
  }
  btn.onclick = join
  const onEnter = (e) => {
    if (e.key === 'Enter') join()
  }
  input.onkeydown = onEnter
  roomInput.onkeydown = onEnter
}

// ================= 玩家视图 =================

function renderPlayer(playerId) {
  app.replaceChildren(h('<div class="page center">连接中…</div>'))
  // 🃏 收起身份:白天盘信息时防旁人偷看(只藏隐私,公开信息照常)。
  // 状态放在 paint 外面——每次 ws 推送都整页重绘,重绘后收起状态不丢
  let cardHidden = false
  let lastView = null
  let nomPick = false // 手机端发起提名:进入「点人选人」模式(说书人一结票或天黑就退出)
  let nomTarget = null // 提名点选中已选的目标 {label, value}(页内确认条,不弹系统框)
  let pickSeats = [] // 夜晚选人(占卜师等):已点选的座位,满配置数量后提交
  let pickChar = null // 麻脸巫婆:变身后选中的角色 id
  let settleMode = 'settle' // 终局后:settle 结算页 | review 复盘页(分开展示)
  let chatPick = false // 私聊:发起邀请的点选模式
  let chatInvitees = [] // 私聊:已点选的被邀请者(座位/旅行者/说书人)
  let chatDraft = '' // 私聊输入草稿(ws 推送整页重绘时保留)
  function paint(view) {
    lastView = view
    document.body.dataset.phase = view.phase || '' // 黑夜/白天自动切换配色(body[data-phase] 变量覆盖)
    const { me, status, seats, phase, night_no: nightNo, day_no: dayNo, current, nominations, bluffs,
      demon_seats: demonSeats, minion_seats: minionSeats, lunatic_seats: lunaticSeats,
      script: scriptName, player_count: count, composition, sentinel: sentinelOn,
      room_code: roomCode, team_changed: teamChanged, role_changed: roleChanged,
      deaths, traveler: meTraveler, travelers_public: travelersPub, day_stage: dayStage,
      me_wish: meWish, night_wake: nightWake, my_kill: myKill, lunatic_kill: lunaticKill,
      night_choice: nightChoice, grimoire: grimoireData, my_mad: myMad, fabled: fabledList,
      chat: chatData } = view
    if (phase !== 'day' || current) { nomPick = false; nomTarget = null } // 提名点选模式:天黑/结票后自动退出
    if (!(nightWake && nightWake.action === 'pick')) { pickSeats = []; pickChar = null } // 选人界面消失 → 清掉未提交的选择
    if (phase !== 'day') { chatPick = false; chatInvitees = [] } // 天黑私聊点选自动退出

    // ---- 🏁 结算页 + 📜 复盘页(分开展示,标签切换):说书人宣布游戏结束后生效 ----
    if (view.result) {
      const r = view.result
      const hasTeam = !!meTraveler || !!me.role
      const myTeam = meTraveler ? (meTraveler.align || 'good') : (teamChanged || (me.role && me.role.team))
      const good = ['good', 'townsfolk', 'outsider'].includes(myTeam)
      const evil = ['evil', 'minion', 'demon'].includes(myTeam)
      const iWon = (r.winner === 'good' && good) || (r.winner === 'evil' && evil)
      const settleBody = `<div class="settle-banner ${hasTeam ? (iWon ? 'win' : 'lose') : ''}">
          <p class="settle-title">${!hasTeam ? '🏁 本局结束' : (iWon ? '🎉 你赢了!' : '💀 你输了')}</p>
          <p class="settle-sub">${r.winner === 'good' ? '善良阵营获胜' : '邪恶阵营获胜'} · 第 ${dayNo} 天 · ${esc(scriptName)}</p>
        </div>
        <div class="settle-list">
          <h4>🃏 全场角色揭晓</h4>
          ${r.seats.map((g) => `<p class="settle-row ${g.alive === false ? 'dead' : ''}">${g.role ? `<span class="team-badge team-${g.role.team}">${TEAM_LABEL[g.role.team]}</span>` : ''} ${g.seat}号 ${esc(g.name || '空座')}:${g.role ? esc(g.role.name) : '—'}${g.seat === me.seat ? '(你)' : ''}</p>`).join('')}
          ${r.travelers.map((t) => `<p class="settle-row ${t.alive ? '' : 'dead'}">🎒 ${esc(t.name)}:${t.role ? esc(t.role.name) : '—'}(${t.align === 'evil' ? '邪恶' : '善良'})</p>`).join('')}
        </div>
        <p class="hint">结果由说书人宣布,如有异议请找说书人</p>`
      const review = view.review || { groups: [], has_data: false }
      const reviewBody = review.has_data
        ? review.groups.map((g) => `<h4 class="review-day">${esc(g.label)}</h4>`
            + g.items.map((it) => `<p class="settle-row review-row ${it.wrong ? 'wrong' : ''}">${it.wrong ? '⚠ ' : ''}${it.text}${it.why ? ` <span class="review-why">(${esc(it.why)})</span>` : ''}</p>`).join('')).join('')
        : '<p class="hint">本局没有复盘数据(老存档或未记录事件)</p>'
      app.replaceChildren(h(`<div class="page rolecard">
        <div class="topbar"><span>🏁 游戏结束 · ${esc(me.name)} · 🚪 ${esc(roomCode)}</span><span class="dot ok" title="已连接"></span></div>
        <div class="settle-tabs">
          <button class="chip ${settleMode === 'settle' ? 'on' : ''}" id="tab-settle">🏁 结算</button>
          <button class="chip ${settleMode === 'review' ? 'on' : ''}" id="tab-review">📜 复盘</button>
        </div>
        <div class="center grow">${settleMode === 'settle' ? settleBody : reviewBody}${CREDIT}</div>
      </div>`))
      document.getElementById('tab-settle').onclick = () => { settleMode = 'settle'; paint(lastView) }
      document.getElementById('tab-review').onclick = () => { settleMode = 'review'; paint(lastView) }
      return
    }
    // 官方配比(公开信息):只展示基础配比,实际调整(男爵/教父等)不给玩家
    const compLine = composition && composition.length === 4
      ? `<p class="hint">📋 ${esc(scriptName)} · ${count} 人 · 官方配比:${['townsfolk', 'outsider', 'minion', 'demon']
        .map((t, i) => `${TEAM_LABEL[t]} ${composition[i]}`).join(' · ')}</p>`
      : ''
    // 哨兵(神职角色)在场是公开信息;调整方向保密,玩家只知「可能 ±1 或不变」
    const sentinelNote = sentinelOn
      ? '<p class="hint">🧙 哨兵在场:外来者数量可能比官方配比 +1 或 −1,也可能不变</p>'
      : ''
    // 传奇角色公开:所有玩家可见在场列表
    const fabledLine = fabledList && fabledList.length
      ? `<p class="hint">🧙 传奇角色:${fabledList.map((f) => esc(f.name)).join(' · ')}</p>`
      : ''

    const pubLines = sentinelNote + fabledLine

    // ---- 公开信息块(座位玩家与旅行者共用) ----
    // 旅行者公开名单:名字与角色公开(官方宣告),阵营保密 → 投票/提名名单显示用
    const tNames = Object.fromEntries((travelersPub || []).map((t) => [t.id, t.name]))
    // 白天/夜晚进度(公开)+ 投票实时票数(公开,举手票型)
    const phaseTxt = status === 'playing'
      ? (phase === 'night' ? ` · 🌙 第 ${nightNo} 夜`
        : phase === 'day' ? ` · ☀️ 第 ${dayNo} 天${dayStage === 'nom' ? ' · 🗳 提名' : ' · 💬 公聊'}` : '')
      : ''
    // 计票器:实时票型公开——谁提名谁、谁投了票(死票会在座位骷髅左边显示 🗳 标记;名单只显示座位号)
    const voteLine = current
      ? `<div class="vote-public">
          <p class="vote-title-p">🗳 ${whoTxt(current.nominator, tNames)} 提名 ${whoTxt(current.nominee, tNames)}</p>
          <p class="vote-count-p">赞成 ${current.votes.length} 票 ${voteChips(current.votes, tNames)}</p>
        </div>`
      : ''
    // 历史投票:按天分组,每天谁提名谁、谁投票、是否处决
    const histByDay = {}
    ;(nominations || []).forEach((n) => { (histByDay[n.day] = histByDay[n.day] || []).push(n) })
    const voteHist = (nominations || []).length
      ? `<div class="vote-hist"><h4>📜 投票记录</h4>${Object.entries(histByDay).map(([day, ns]) =>
          `<p class="hist-day">第${day}天</p>` + ns.map((n) =>
            `<p class="hist-line">${whoTxt(n.nominator, tNames)} 提名 ${whoTxt(n.nominee, tNames)} · 赞成 ${n.votes.length} 票 ${voteChips(n.votes, tNames)}${n.executed ? (typeof n.nominee === 'string' ? ' · 🏴 流放' : ' · ⚔ 处决') : (n.passed ? ' · ⚖ 待处决' : ' · 未通过')}</p>`).join('')
        ).join('')}</div>`
      : ''
    // 已死亡名单按天分组换行(后端按 day 排序,夜里刚死的人天亮才出现在名单里);
    // 旅行者(座位是 t1 字符串)显示 🎒 名字,流放标注(流放)
    const deathsByDay = {}
    ;(deaths || []).forEach((d) => { (deathsByDay[d.day] = deathsByDay[d.day] || []).push(d) })
    const deathTxt = (d) => (typeof d.seat === 'number' ? `${d.seat}号 ${esc(d.name)}` : `🎒 ${esc(d.name)}`) +
      (d.exiled ? '(流放)' : '') + (d.empty ? '(空座)' : '')
    const deadLine = (deaths || []).length
      ? `<div class="dead-announce">☠ 已死亡:${Object.entries(deathsByDay).map(([day, list]) =>
          `<span class="dead-day">第${day}天:${list.map(deathTxt).join('、')}</span>`).join('')}</div>`
      : ''

    // ---- 手机端操作:发起提名 + 举手投票(说书人魔典仍可代记,双通道同步) ----
    const myTarget = meTraveler ? meTraveler.id : me.seat
    const myAlive = meTraveler ? meTraveler.alive : me.alive
    const myDeadVoteUsed = meTraveler ? meTraveler.dead_vote_used : me.dead_vote_used
    const myInVotes = !!current && current.votes.includes(myTarget)
    const iNominatedToday = (nominations || []).some((n) => n.day === dayNo && n.nominator === myTarget)
    const canAct = status === 'playing' && phase === 'day' && dayStage === 'nom' // 提名阶段才开放操作
    const voteActions = canAct && current
      ? myInVotes
        ? `<button class="btn" id="my-vote">✋ 放下(取消举手)</button>`
        : myAlive
          ? `<button class="btn primary" id="my-vote">🖐 举手赞成</button>`
          : !myDeadVoteUsed
            ? `<button class="btn danger" id="my-vote">🖐 举手(交出唯一死票)</button>`
            : '<button class="btn ghost" disabled>🗳 死票已交</button>'
      : ''
    const nomActions = canAct && !current && myAlive && !iNominatedToday
      ? nomPick
        ? `<button class="btn ghost" id="nom-cancel">✖ 取消提名</button>
           ${nomTarget ? '' : '<p class="sub">👇 点圆盘上的玩家,或下方旅行者列表</p>'}`
        : `<button class="btn" id="nom-start">🗳 发起提名</button>`
      : (canAct && !current && myAlive && iNominatedToday
        ? '<p class="hint">你今天已经提名过了,等说书人结票</p>'
        : '')
    const pickChips = nomPick
      ? `<div class="t-pick">🎒 提名旅行者:${(travelersPub || []).filter((t) => !t.exiled).map((t) =>
          `<button class="chip team-traveler ${nomTarget && nomTarget.value === t.id ? 'on' : ''}" data-nom-t="${t.id}">${esc(t.name)}${t.role ? ' · ' + esc(t.role.name) : ''}</button>`).join('') || '<span class="hint">无</span>'}</div>`
      : ''
    // 页内确认条:点中目标后出现,再点「确认提名」才提交(不弹系统框)
    const nomConfirm = nomPick && nomTarget
      ? `<div class="nom-confirm">🗳 提名 ${esc(nomTarget.label)}?
          <button class="btn primary" id="nom-go">✅ 确认提名</button>
          <button class="btn ghost" id="nom-pick-cancel">✖ 换人</button>
        </div>`
      : ''
    const playerActions = `<div class="player-actions">${nomActions}${voteActions}${nomConfirm}${pickChips}
      ${status === 'playing' && phase === 'day' && dayStage === 'talk'
        ? '<p class="hint">💬 公聊私聊阶段:说书人宣布进入提名阶段后才能提名与投票</p>'
        : ''}
      <p class="error" id="action-err" style="display:none"></p></div>`
    // 🙏 许愿(仅大厅):开局前表达愿望——善良/邪恶预设或自定义文字;仅说书人与本人可见
    const wishBlock = status === 'lobby'
      ? `<div class="wish-box">
          <p class="hint">🙏 开局前许愿(说书人配板时参考,仅说书人可见):</p>
          <div class="wish-row">
            <button class="chip ${meWish === '善良' ? 'on' : ''}" data-wish="善良">😇 善良阵营</button>
            <button class="chip ${meWish === '邪恶' ? 'on' : ''}" data-wish="邪恶">😈 邪恶阵营</button>
          </div>
          <div class="wish-row">
            <input class="input" id="wish-custom" maxlength="30" placeholder="自定义:如 想玩信息角色">
            <button class="btn small" id="wish-save">🙏 许愿</button>
            ${meWish ? '<button class="btn small ghost" id="wish-clear">清除</button>' : ''}
          </div>
          ${meWish ? `<p class="hint">当前愿望:${esc(meWish)}</p>` : ''}
          <p class="error" id="wish-err" style="display:none"></p>
        </div>`
      : ''
    const wireWish = () => {
      const werr = document.getElementById('wish-err')
      const fail = (e) => { werr.textContent = e.message; werr.style.display = '' }
      const post = (wish) => api(`/api/player/${playerId}/wish`, { method: 'POST', body: JSON.stringify({ wish }) }).catch(fail)
      document.querySelectorAll('[data-wish]').forEach((b) => {
        b.onclick = () => post(meWish === b.dataset.wish ? null : b.dataset.wish) // 再点已选中的=清除
      })
      const save = document.getElementById('wish-save')
      if (save) save.onclick = () => {
        const v = (document.getElementById('wish-custom').value || '').trim()
        if (!v) { werr.textContent = '先输入愿望文字'; werr.style.display = ''; return }
        post(v)
      }
      const clr = document.getElementById('wish-clear')
      if (clr) clr.onclick = () => post(null)
    }

    // 😈 夜晚刀人(瓦釜雷鸣测试):说书人走到恶魔步骤时手机点亮,选目标后天亮自动执行
    const killBox = nightWake && nightWake.action === 'kill'
      ? `<div class="kill-box">
          <p class="sub">😈 夜晚行动:选择你要杀死的玩家${nightWake.lunatic ? '' : '(天亮自动执行,可改)'}</p>
          <div class="kill-chips">${nightWake.targets.map((s) =>
            `<button class="chip kill-chip ${myKill === s ? 'on' : ''}" data-kill="${s}"
              title="${esc((seats.find((x) => x.seat === s)?.player || {}).name || '')}">${s}号</button>`).join('')}</div>
          ${myKill != null ? `<p class="hint">已选择:${myKill}号,再点其他座位可改</p>` : ''}
          <p class="error" id="kill-err" style="display:none"></p>
        </div>`
      : ''
    const wireKill = () => {
      const kerr = document.getElementById('kill-err')
      document.querySelectorAll('[data-kill]').forEach((b) => {
        b.onclick = () => api(`/api/player/${playerId}/kill`, { method: 'POST', body: JSON.stringify({ seat: Number(b.dataset.kill) }) })
          .catch((e) => { kerr.textContent = e.message; kerr.style.display = '' })
      })
    }

    // 恶魔夜间私讯(官方:恶魔知道疯子是谁,也知道他每夜刀了谁)
    const lunaticKillBox = status === 'playing' && phase === 'night' && lunaticKill != null
      ? `<div class="lunatic-kill-note">🩻 疯子选择了刀杀 ${lunaticKill}号</div>`
      : ''

    // 🔮 夜晚选人(占卜师/筑梦师等):说书人走到对应步骤时点亮,选完提交等电子回复
    const pickBox = nightWake && nightWake.action === 'pick'
      ? `<div class="kill-box">
          <p class="sub">🔮 夜晚行动:选择 ${nightWake.count} 名玩家</p>
          <div class="kill-chips">${nightWake.targets.map((s) =>
            `<button class="chip kill-chip ${pickSeats.includes(s) ? 'on' : ''}" data-pick="${s}"
              title="${esc((seats.find((x) => x.seat === s)?.player || {}).name || '')}">${s}号</button>`).join('')}</div>
          <p class="hint">已选 ${pickSeats.length}/${nightWake.count}:${pickSeats.length ? pickSeats.map((s) => `${s}号`).join('、') : '尚未选择'}
            ${nightChoice && nightChoice.targets ? ` · 已提交:${nightChoice.targets.map((t) => `${t}号`).join('、')}(可改)` : ''}</p>
          ${nightWake.grimoire ? '<p class="hint">💡 选自己:善良玩家不会得知寡妇在场(官方规则)</p>' : ''}
          ${nightWake.char
            ? `<p class="sub">👤 变身后的角色(不在场才会生效,你不会知道谁在场):</p>
               <div class="kill-chips">${(nightWake.chars || []).map((c) =>
                 `<button class="chip kill-chip ${pickChar === c.id ? 'on' : ''}" data-pickchar="${c.id}">${esc(c.name)}</button>`).join('')}</div>
               ${pickChar ? `<p class="hint">已选角色:${esc((nightWake.chars.find((c) => c.id === pickChar) || {}).name || '')}</p>` : ''}`
            : ''}
          <button class="btn primary" id="pick-go" ${pickSeats.length === nightWake.count && (!nightWake.char || pickChar) ? '' : 'disabled'}>提交选择</button>
          <p class="error" id="pick-err" style="display:none"></p>
        </div>`
      : ''
    // 📖 寡妇首夜魔典(仅此夜此步可见,睡下后消失)
    const grimoireBox = nightWake && nightWake.grimoire && grimoireData
      ? `<div class="grimoire-box">
          <p class="sub">📖 魔典(仅此夜,看完即忘)</p>
          ${grimoireData.seats.map((g) => `<span class="grimoire-row ${g.alive === false ? 'dead' : ''}">${g.seat}号 ${esc(g.name || '空')}:<b>${g.role ? esc(g.role.name) : '—'}</b></span>`).join('')}
          ${(grimoireData.travelers || []).map((t) => `<span class="grimoire-row ${t.alive ? '' : 'dead'}">🎒 ${esc(t.name)}:<b>${t.role ? esc(t.role.name) : '—'}</b>(${t.align === 'evil' ? '邪恶' : '善良'})</span>`).join('')}
        </div>`
      : ''
    // 说书人电子回复(夜里随时可见)
    const replyBox = status === 'playing' && phase === 'night' && nightChoice && nightChoice.reply
      ? `<div class="lunatic-kill-note">📩 说书人:${esc(nightChoice.reply)}</div>`
      : ''
    // 🎭 疯狂通知:被疯狂者必须被告知(直到说书人解除,否则可能被处决)
    const madBox = myMad
      ? `<div class="lunatic-kill-note">🎭 你疯狂了:你必须声称自己是「${esc(myMad.role.name)}」,直到说书人解除,否则可能被处决</div>`
      : ''

    // ---- 💬 白天私聊(说书人可作为特殊玩家被邀请;后加入者看不到历史) ----
    const chatNameOf = (who) => {
      if (who === 'st' || String(who) === 'st') return '🕯 说书人'
      const n = Number(who)
      if (!Number.isNaN(n)) {
        const p = (seats.find((x) => x.seat === n) || {}).player
        return p ? p.name : `${n}号`
      }
      const t = (travelersPub || []).find((x) => x.id === who)
      return t ? t.name : who
    }
    const chatColorOf = (seat) => {
      if (!chatData || !chatData.chats_public) return null
      const c = chatData.chats_public.find((x) => x.members.some((m) => String(m.who) === String(seat)))
      return c ? c.color : null
    }
    const chatBox = status === 'playing' && phase === 'day' && chatData
      ? (chatData.my_chat
        ? `<div class="chat-box">
            <div class="chat-head"><span class="chat-dot" style="background:${chatData.my_chat.color}"></span>💬 私聊
              ${chatData.my_chat.members.map((m) => String(m.who) === 'st'
                ? '<span class="chip small st-in-chat">🕯 说书人</span>' : `<span>${esc(m.name)}</span>`).join('、')}
              ${chatData.my_chat.is_owner ? '<button class="chip small primary" id="chat-invite-more">➕ 邀请</button>' : ''}
              ${chatData.my_chat.is_owner ? '<button class="chip small ghost" id="chat-close">关闭</button>' : ''}
              <button class="chip small ghost" id="chat-leave">退出</button></div>
            <div class="chat-msgs" id="chat-msgs">${chatData.my_chat.messages.length
              ? chatData.my_chat.messages.map((m) => `<p class="chat-msg ${String(m.from) === String(chatData.who) ? 'mine' : ''}"><b>${esc(m.name)}</b>:${esc(m.text)}</p>`).join('')
              : '<p class="hint">暂无消息</p>'}</div>
            ${chatData.my_chat.requests.length
              ? chatData.my_chat.requests.map((r) => `<p class="chat-request">🙋 ${esc(r.name)}申请加入
                  <button class="chip small" data-apr="${r.who}" data-apr-y="1">同意</button>
                  <button class="chip small ghost" data-apr="${r.who}" data-apr-y="0">拒绝</button></p>`).join('')
              : ''}
            ${chatPick
              ? `<p class="sub">👇 点选要邀请的玩家:</p>
                 <div class="chat-pick">
                   ${seats.filter((x) => x.player && x.is_me !== true && !chatData.my_chat.members.some((m) => String(m.who) === String(x.seat)))
                     .map((x) => `<button class="chip small ${chatInvitees.includes(String(x.seat)) ? 'on' : ''}" data-chatpick="${x.seat}">${x.seat}号 ${esc(x.player.name)}</button>`).join('')}
                   ${(travelersPub || []).filter((t) => !t.exiled && !chatData.my_chat.members.some((m) => String(m.who) === t.id))
                     .map((t) => `<button class="chip small ${chatInvitees.includes(t.id) ? 'on' : ''}" data-chatpick="${t.id}">🎒 ${esc(t.name)}</button>`).join('')}
                   ${!chatData.my_chat.members.some((m) => String(m.who) === 'st')
                     ? `<button class="chip small ${chatInvitees.includes('st') ? 'on' : ''}" data-chatpick="st">🕯 说书人</button>` : ''}
                 </div>
                 <div class="chat-pick-actions">
                   ${chatInvitees.length ? '<button class="btn small primary" id="chat-invite-go">发送邀请</button>' : ''}
                   <button class="chip small ghost" id="chat-pick-cancel">取消</button>
                 </div>`
              : ''}
            <div class="chat-input">
              <input class="input" id="chat-text" maxlength="500" placeholder="输入消息(仅本群可见)" value="${esc(chatDraft)}">
              <button class="btn small primary" id="chat-send">发送</button>
            </div>
          </div>`
        : `<div class="chat-box">
            <div class="chat-head">💬 私聊大厅
              ${chatData.invites.length ? `<span class="hint">有 ${chatData.invites.length} 个邀请</span>` : ''}
              <button class="chip small primary" id="chat-new">🙋 发起私聊</button></div>
            ${chatData.invites.map((iv) => `<p class="chat-invite"><span class="chat-dot" style="background:${iv.color}"></span>${esc(iv.owner_name)} 邀请你私聊
              <button class="chip small primary" data-inv="${iv.id}" data-inv-y="1">✅ 接受</button>
              <button class="chip small ghost" data-inv="${iv.id}" data-inv-y="0">❌ 拒绝</button></p>`).join('')}
            ${chatPick
              ? `<p class="sub">👇 点选要邀请的玩家(可多选,再点取消):</p>
                 <div class="chat-pick">
                   ${seats.filter((s) => s.player && s.is_me !== true).map((s) => `<button class="chip small ${chatInvitees.includes(s.seat) ? 'on' : ''}" data-chatpick="${s.seat}">${s.seat}号 ${esc(s.player.name)}</button>`).join('')}
                   ${(travelersPub || []).filter((t) => !t.exiled).map((t) => `<button class="chip small ${chatInvitees.includes(t.id) ? 'on' : ''}" data-chatpick="${t.id}">🎒 ${esc(t.name)}</button>`).join('')}
                   <button class="chip small ${chatInvitees.includes('st') ? 'on' : ''}" data-chatpick="st">🕯 说书人</button>
                 </div>
                 <div class="chat-pick-actions">
                   ${chatInvitees.length ? '<button class="btn small primary" id="chat-create-go">发送邀请</button>' : ''}
                   <button class="chip small ghost" id="chat-pick-cancel">取消</button>
                 </div>`
              : ''}
            ${chatData.chats_public.length
              ? '<p class="hint">进行中的私聊(点申请加入):</p>' + chatData.chats_public.map((c) =>
                  `<p class="chat-pub"><span class="chat-dot" style="background:${c.color}"></span>${c.members.map((m) => esc(m.name)).join('、')}
                    ${c.requested ? '<span class="hint">已申请,等发起者同意</span>'
                      : `<button class="chip small" data-join="${c.id}">申请加入</button>`}</p>`).join('')
              : '<p class="hint">还没有进行中的私聊</p>'}
          </div>`)
      : ''
    // 私聊操作绑定(座位页与旅行者页共用)
    const wireChat = () => {
      const chatErr = (e) => { const el = document.getElementById('chat-err'); if (el) { el.textContent = e.message; el.style.display = '' } }
      const post = (path, body) => api(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }).catch(chatErr)
      const msgs = document.getElementById('chat-msgs')
      if (msgs) msgs.scrollTop = 999999 // 新消息滚到底
      const sendBtn = document.getElementById('chat-send')
      if (sendBtn) sendBtn.onclick = () => {
        const v = (document.getElementById('chat-text').value || '').trim()
        if (!v) return
        post(`/api/chat/${chatData.my_chat.id}/send?player_id=${playerId}`, { text: v }).then(() => { chatDraft = '' })
      }
      const textInput = document.getElementById('chat-text')
      if (textInput) {
        textInput.oninput = () => { chatDraft = textInput.value }
        textInput.onkeydown = (e) => { if (e.key === 'Enter') sendBtn && sendBtn.click() }
      }
      const leave = document.getElementById('chat-leave')
      if (leave) leave.onclick = () => post(`/api/chat/${chatData.my_chat.id}/leave?player_id=${playerId}`)
      const close = document.getElementById('chat-close')
      if (close) close.onclick = () => post(`/api/chat/${chatData.my_chat.id}/close?player_id=${playerId}`)
      const inviteMore = document.getElementById('chat-invite-more')
      if (inviteMore) inviteMore.onclick = () => { chatInvitees = []; chatPick = true; paint(lastView) }
      const inviteGo = document.getElementById('chat-invite-go')
      if (inviteGo) inviteGo.onclick = () => {
        post(`/api/chat/${chatData.my_chat.id}/invite-more?player_id=${playerId}`, { invitees: chatInvitees.map((x) => (/^\d+$/.test(x) ? Number(x) : x)) })
          .then(() => { chatPick = false; chatInvitees = [] })
      }
      document.querySelectorAll('[data-apr]').forEach((b) => {
        b.onclick = () => post(`/api/chat/${chatData.my_chat.id}/approve?player_id=${playerId}`, { who: Number(b.dataset.apr) || b.dataset.apr, approve: b.dataset.aprY === '1' })
      })
      document.querySelectorAll('[data-inv]').forEach((b) => {
        b.onclick = () => post(`/api/chat/${b.dataset.inv}/invite?player_id=${playerId}`, { accept: b.dataset.invY === '1' })
      })
      document.querySelectorAll('[data-join]').forEach((b) => {
        b.onclick = () => post(`/api/chat/${b.dataset.join}/request?player_id=${playerId}`)
      })
      const newBtn = document.getElementById('chat-new')
      if (newBtn) newBtn.onclick = () => { chatInvitees = []; chatPick = true; paint(lastView) }
      const cancelBtn = document.getElementById('chat-pick-cancel')
      if (cancelBtn) cancelBtn.onclick = () => { chatPick = false; chatInvitees = []; paint(lastView) }
      document.querySelectorAll('[data-chatpick]').forEach((b) => {
        b.onclick = () => {
          const w = b.dataset.chatpick
          chatInvitees = chatInvitees.includes(w) ? chatInvitees.filter((x) => x !== w) : [...chatInvitees, w]
          paint(lastView)
        }
      })
      const go = document.getElementById('chat-create-go')
      if (go) go.onclick = () => {
        post(`/api/chat/create?player_id=${playerId}`, { invitees: chatInvitees.map((x) => (/^\d+$/.test(x) ? Number(x) : x)) })
          .then(() => { chatPick = false; chatInvitees = [] })
      }
    }
    const wirePick = () => {
      const perr = document.getElementById('pick-err')
      document.querySelectorAll('[data-pick]').forEach((b) => {
        b.onclick = () => {
          const s = Number(b.dataset.pick)
          if (pickSeats.includes(s)) pickSeats = pickSeats.filter((x) => x !== s)
          else if (pickSeats.length < nightWake.count) pickSeats = [...pickSeats, s]
          else return
          paint(lastView)
        }
      })
      document.querySelectorAll('[data-pickchar]').forEach((b) => {
        b.onclick = () => { pickChar = b.dataset.pickchar === pickChar ? null : b.dataset.pickchar; paint(lastView) }
      })
      const go = document.getElementById('pick-go')
      if (go) go.onclick = () => {
        const body = nightWake.char ? { targets: pickSeats, char: pickChar } : { targets: pickSeats }
        api(`/api/player/${playerId}/choice`, { method: 'POST', body: JSON.stringify(body) })
          .then(() => { pickSeats = []; pickChar = null }).catch((e) => { perr.textContent = e.message; perr.style.display = '' })
      }
    }
    // 提名/投票的按钮与错误行绑定(座位页与旅行者页共用)
    const failAction = (e) => {
      const actionErr = document.getElementById('action-err')
      if (actionErr) { actionErr.textContent = e.message; actionErr.style.display = '' }
    }
    const wirePlayerActions = () => {
      const vbtn = document.getElementById('my-vote')
      if (vbtn) {
        if (!myAlive && !myInVotes) {
          armClick(vbtn, '☠ 确认交出死票?', () => api(`/api/player/${playerId}/vote`, { method: 'POST' }).catch(failAction))
        } else {
          vbtn.onclick = () => api(`/api/player/${playerId}/vote`, { method: 'POST' }).catch(failAction)
        }
      }
      const nbtn = document.getElementById('nom-start')
      if (nbtn) nbtn.onclick = () => { nomTarget = null; nomPick = true; paint(lastView) }
      const cbtn = document.getElementById('nom-cancel')
      if (cbtn) cbtn.onclick = () => { nomPick = false; nomTarget = null; paint(lastView) }
      const ngo = document.getElementById('nom-go')
      if (ngo) ngo.onclick = () => {
        const target = nomTarget.value
        nomPick = false; nomTarget = null
        api(`/api/player/${playerId}/nominate`, { method: 'POST', body: JSON.stringify({ nominee: target }) }).catch(failAction)
      }
      const npc = document.getElementById('nom-pick-cancel')
      if (npc) npc.onclick = () => { nomTarget = null; paint(lastView) }
      document.querySelectorAll('[data-nom-t]').forEach((b) => {
        b.onclick = () => {
          nomTarget = { label: `旅行者 ${tNames[b.dataset.nomT] || ''}`, value: b.dataset.nomT }
          paint(lastView)
        }
      })
    }
    const nominateSeat = (s) => {
      if (!s.player) return
      nomTarget = { label: `${s.seat}号 ${s.player.name}`, value: s.seat }
      paint(lastView)
    }

    // ---- 未入座:选座(旅行者已单独成支,不占座位) ----
    if (me.seat == null && !meTraveler) {
      app.replaceChildren(h(`<div class="page rolecard">
        <div class="topbar"><span>${esc(me.name)} · 🚪 ${esc(roomCode)}</span><span class="dot ok" title="已连接"></span></div>
        <div class="center grow">
          <p class="sub">${status === 'playing' ? '游戏已开始(迟到):点空座入座,继承该座预发身份' : '选择你的座位入座'}</p>
          ${compLine}
          ${pubLines}
          <div id="circle"></div>
          <p class="hint">${seats.length ? `共 ${seats.length} 个座位,点一个空座位入座` : '等待说书人设置本局人数…'}</p>
          ${status === 'playing'
            ? `<button class="btn primary" id="traveler-btn">🎒 以旅行者身份加入</button>
               <p class="hint">满座或不想占座时选这个:不算配板,角色由说书人指派,可随时离开(流放)</p>`
            : ''}
          ${wishBlock}
          <p class="error" id="sit-err" style="display:none"></p>
        </div>
        ${CREDIT}
      </div>`))
      const err = document.getElementById('sit-err')
      document.getElementById('circle').appendChild(seatCircle(seats, {
        centerHanged: status === 'playing' && phase === 'night' && nightNo === 1,
        clickSeat: (s) => {
          if (s.player) return
          api(`/api/player/${playerId}/sit`, { method: 'POST', body: JSON.stringify({ seat: s.seat }) })
            .catch((e) => { err.textContent = e.message; err.style.display = '' })
        },
      }))
      wireWish()
      dramaOverlay(roomCode, phase, nightNo, status)
      const tbtn = document.getElementById('traveler-btn')
      if (tbtn) tbtn.onclick = () => api(`/api/player/${playerId}/traveler`, { method: 'POST' })
        .catch((e) => { err.textContent = e.message; err.style.display = '' })
      return
    }

    // ---- 旅行者页:不占座位,只有角色卡与公开信息(白天同样可以收起身份) ----
    if (meTraveler) {
      const role = meTraveler.role
      const joinTxt = `${meTraveler.joined_phase === 'day' ? '第 ' + meTraveler.joined_no + ' 天' : '第 ' + meTraveler.joined_no + ' 夜'}加入`
      const card = !role
        ? `<div class="center"><p class="sub">🎒 你已作为旅行者加入,等待说书人指派角色…</p></div>`
        : cardHidden
          ? `<button class="card-cover" id="card-cover">
              <span class="cover-icon">🃏</span>
              <span class="cover-title">身份已隐藏</span>
              <span class="cover-hint">点击恢复 · 电脑按 H 键</span>
            </button>`
          : `<div class="card team-traveler ${meTraveler.alive ? '' : 'dead'}" id="role-card">
              <div class="card-head">
                <span class="team-badge">${meTraveler.align === 'evil' ? '邪恶' : '善良'}</span>
                <span class="en">${esc(role.en)} · Traveler</span>
              </div>
              <h2 class="role-name">${esc(role.name)}</h2>
              <p class="ability">${esc(role.ability)}</p>
              ${meTraveler.alive ? '' : `<p class="death-note">${meTraveler.exiled ? '🏴 你已被流放,离开小镇' : '☠ 你已死亡:夜晚请闭眼,白天可以继续发言'}</p>`}
              <p class="hide-hint">🃏 点卡片收起身份 · 电脑按 H 键</p>
            </div>`
      // 邪恶旅行者:加入时由说书人告知恶魔是谁(恶魔线在会面数据里,后端只给 evil 旅行者推)
      const demonLine = demonSeats && demonSeats.length
        ? `<p class="meet-line">😈 恶魔:${demonSeats.map((d) => `${d.seat}号${d.name ? ` ${esc(d.name)}` : ''}`).join(' · ')}</p>`
        : ''
      app.replaceChildren(h(`<div class="page rolecard">
        <div class="topbar"><span>🎒 旅行者 · ${esc(me.name)}${phaseTxt} · 🚪 ${esc(roomCode)}</span><span class="dot ok" title="已连接"></span></div>
        <div id="circle"></div>
        <div class="center grow">
          <p class="sub">${joinTxt} · 阵营只有你和说书人知道</p>
          ${card}
          ${chatBox}
          ${voteLine}
          ${playerActions}
          ${voteHist}
          ${compLine}
          ${pubLines}
          ${deadLine}
          ${cardHidden ? '' : demonLine}
          ${CREDIT}
        </div>
      </div>`))
      // 圆盘:平时纯查看(旅行者不占座位);提名点选模式下点击=选被提名者
      document.getElementById('circle').appendChild(seatCircle(seats, {
        voted: (s) => !!current && current.votes.includes(s.seat),
        bubble: (s) => chatColorOf(s.seat),
        centerBubble: () => chatColorOf('st'),
        centerHanged: phase === 'night' && nightNo === 1,
        clickSeat: (s) => {
          if (chatPick && s.player) { // 私聊邀请点选
            const w = String(s.seat)
            chatInvitees = chatInvitees.includes(w) ? chatInvitees.filter((x) => x !== w) : [...chatInvitees, w]
            paint(lastView)
            return
          }
          if (nomPick) nominateSeat(s)
        },
        pickSeat: nomPick && nomTarget && typeof nomTarget.value === 'number' ? nomTarget.value : null,
      }))
      wirePlayerActions()
      wireChat()
      dramaOverlay(roomCode, phase, nightNo, status)
      const cover = document.getElementById('card-cover')
      if (cover) cover.addEventListener('click', () => { cardHidden = false; paint(lastView) })
      const roleCard = document.getElementById('role-card')
      if (roleCard) roleCard.addEventListener('click', () => { cardHidden = true; paint(lastView) })
      return
    }

    // ---- 已入座 ----
    const role = roleChanged || me.role // 角色转变:角色卡直接展示新角色
    // 阵营与角色分开算:只有说书人显式标记「阵营转变」才改阵营;角色转变不改阵营(换角色≠换阵营),
    // 否则玩家角色一变,卡框颜色和阵营徽章也跟着变,等于偷偷替说书人做了阵营转变
    const team = teamChanged || (me.role && me.role.team)
    // 开局前不揭示身份:说书人开始游戏玩家才拿到角色
    const card = !role
      ? `<div class="center"><p class="sub">${status === 'lobby' ? '已入座,等待说书人开始游戏…' : '等待说书人分配角色…'}</p>
         ${status === 'lobby' ? '<p class="hint">开局前点其他空座位可以换座</p>' : ''}</div>`
      : cardHidden
        ? `<button class="card-cover" id="card-cover">
            <span class="cover-icon">🃏</span>
            <span class="cover-title">身份已隐藏</span>
            <span class="cover-hint">点击恢复 · 电脑按 H 键</span>
          </button>`
        : `<div class="card team-${team} ${me.alive ? '' : 'dead'}" id="role-card" ${teamChanged ? `style="--team:${teamChanged === 'good' ? '#55b5ff' : '#e92a2a'};--team-text:${teamChanged === 'good' ? '#101828' : '#ffffff'}"` : ''}>
          <div class="card-head">
            <span class="team-badge">${teamChanged ? (teamChanged === 'good' ? '善良' : '邪恶') : TEAM_LABEL[team]}</span>
            <span class="en">${esc(role.en)}</span>
          </div>
          <h2 class="role-name">${esc(role.name)}</h2>
          <p class="ability">${esc(role.ability)}</p>
          ${me.alive ? '' : '<p class="death-note">☠ 你已死亡:夜晚请闭眼,白天可以继续发言</p>'}
          <p class="hide-hint">🃏 点卡片收起身份 · 电脑按 H 键</p>
        </div>`
    // 伪装:仅恶魔(后端按真实身份判断)能看到三个不在场好角色,恶魔会面推进后才揭晓
    const bluffLine = bluffs && bluffs.length
      ? `<p class="bluffs">🧪 伪装(不在场,可假装):${bluffs.map((r) => esc(r.name)).join(' · ')}</p>`
      : ''
    // 会面揭晓(信息不可收回):爪牙会面=所有爪牙同时醒来——爪牙手机显示恶魔是谁+其他爪牙(彼此可见);
    // 恶魔会面=恶魔独醒——恶魔手机显示爪牙名单
    const demonLine = demonSeats && demonSeats.length
      ? `<p class="meet-line">😈 恶魔:${demonSeats.map((d) => `${d.seat}号${d.name ? ` ${esc(d.name)}` : ''}`).join(' · ')}</p>`
      : ''
    const minionLine = minionSeats && minionSeats.length
      ? `<p class="meet-line">🩸 爪牙:${minionSeats.map((m) => `${m.seat}号${m.name ? ` ${esc(m.name)}` : ''}${m.seat === me.seat ? '(你)' : ''}`).join(' · ')}</p>`
      : ''
    // 恶魔/爪牙都知道疯子是谁:他就是疯子,不是真恶魔
    const lunaticLine = lunaticSeats && lunaticSeats.length
      ? `<p class="meet-line">🩻 疯子:${lunaticSeats.map((l) => `${l.seat}号${l.name ? ` ${esc(l.name)}` : ''}`).join(' · ')}</p>`
      : ''
    // 角色/阵营转变:文字提示保留(无背景色),与角色卡/卡框换色同步展示
    const roleChangeLine = roleChanged
      ? `<p class="meet-line">🔄 角色转变:你的角色已变为「${esc(roleChanged.name)}」</p>`
      : ''
    const teamChangeLine = teamChanged
      ? `<p class="meet-line">⚖ 阵营转变:你的阵营已变为 ${teamChanged === 'good' ? '善良' : '邪恶'}</p>`
      : ''
    // 隐私行(伪装/会面/转变)与身份卡一起收起;公开信息(投票/死者名单/配比)不受影响
    const privateLines = cardHidden ? '' : bluffLine + demonLine + minionLine + lunaticLine + roleChangeLine + teamChangeLine
    app.replaceChildren(h(`<div class="page rolecard">
      <div class="topbar"><span>座位 ${me.seat} · ${esc(me.name)}${phaseTxt} · 🚪 ${esc(roomCode)}</span><span class="dot ok" title="已连接"></span></div>
      <div id="circle"></div>
      ${killBox}
      ${lunaticKillBox}
      ${grimoireBox}
      ${pickBox}
      ${replyBox}
      ${madBox}
      ${chatBox}
      ${voteLine}
      ${playerActions}
      ${wishBlock}
      ${voteHist}
      ${compLine}
      ${pubLines}
      ${card}
      ${deadLine}
      ${privateLines}
      ${CREDIT}
    </div>`))
    document.getElementById('circle').appendChild(seatCircle(seats, {
      voted: (s) => !!current && current.votes.includes(s.seat), // 举手票型公开,玩家也可见
      centerBubble: () => chatColorOf('st'),
      centerHanged: phase === 'night' && nightNo === 1,
      clickSeat: (s) => {
        if (chatPick && s.player) { // 私聊邀请点选(多选)
          const w = String(s.seat)
          chatInvitees = chatInvitees.includes(w) ? chatInvitees.filter((x) => x !== w) : [...chatInvitees, w]
          paint(lastView)
          return
        }
        if (nomPick) { nominateSeat(s); return } // 提名点选模式:点人=提名
        // 开局前可换座:点空座位移动过去
        if (!s.player && status === 'lobby') {
          api(`/api/player/${playerId}/sit`, { method: 'POST', body: JSON.stringify({ seat: s.seat }) }).catch(() => {})
        }
      },
      bubble: (s) => chatColorOf(s.seat),
      pickSeat: nomPick && nomTarget && typeof nomTarget.value === 'number' ? nomTarget.value : null,
    }))
    wirePlayerActions()
    wireWish()
    wireKill()
    wirePick()
    wireChat()
    dramaOverlay(roomCode, phase, nightNo, status)
    // 🃏 收起身份:点卡片收起、点封盖恢复(H 键切换在 renderPlayer 里注册)
    const cover = document.getElementById('card-cover')
    if (cover) cover.addEventListener('click', () => { cardHidden = false; paint(lastView) })
    const roleCard = document.getElementById('role-card')
    if (roleCard) roleCard.addEventListener('click', () => { cardHidden = true; paint(lastView) })
  }
  // 🃏 H 键收起/恢复身份:白天盘信息时防旁人看到自己的角色(输入框/组合键/输入法不触发)
  window.addEventListener('keydown', (e) => {
    if (e.key !== 'h' && e.key !== 'H') return
    if (e.ctrlKey || e.metaKey || e.altKey || e.isComposing) return
    const t = e.target
    if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return
    if (!lastView) return
    cardHidden = !cardHidden
    paint(lastView)
  })
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
  let draftBluffs = [] // 手动模式伪装草稿:不在场好角色 id ×3(配版时选好)
  let draftFakes = {} // 手动模式认知覆盖草稿:座位号 → 假角色 id(说书人显式选择)
  let draftLunMinions = {} // 手动模式:疯子座位号 → 以为的爪牙座位列表
  let draftLunBluffs = {} // 手动模式:疯子座位号 → 3 个伪装角色 id
  let godfatherAdj = 1 // 教父外来者调整:说书人可选 +1 或 −1,默认 +1
  let rolePickSeat = null // 角色转变:正在为该座位选择「变成哪个角色」
  let teamPickSeat = null // 阵营转变:正在为该座位选择新阵营(善良/邪恶)
  let madPickSeat = null // 疯狂:正在为该座位选择「疯狂宣称哪个善良角色」
  let opState = { key: null, pick: [], char: null } // 夜晚代操作(空座测试):当前步骤的选人/角色状态
  let endPick = false // 结算:点「🏁 结算」后显示获胜方选择
  let reviewMode = false // 终局后:魔典切换为独立复盘视图(标错/讲解用)
  let stChatOpen = null // 私聊总览:展开查看哪个群的消息流
  let stArchiveOpen = null // 私聊档案:展开查看哪个已关闭群的留档
  let travelerPick = null // 旅行者:正在为这个旅行者指派角色(t1..)/选阵营
  let travelerAlign = 'good' // 旅行者指派时的阵营选择(官方:绝大多数情况给善良)
  let configArm = false // 配置两步确认:第一次点提示,3 秒内再点才执行(不弹系统框)

  function paint(view) {
    document.body.dataset.phase = view.phase || '' // 黑夜/白天自动切换配色(body[data-phase] 变量覆盖)
    const { status, script, player_count: count, scripts, seats, roles, composition,
      adjust_roles, seat_roles, phase, night_no: nightNo, day_no: dayNo, night,
      nominations, current, alive_count: aliveCount, quorum, can_start: canStart,
      bluffs, demon_seats: demonSeats, minion_seats: minionSeats, sentinel, saved_at: savedAt,
      fake_pools: fakePools, lunatic_seats: lunaticSeats, lunatic_minions: lunaticMinions,
      lunatic_bluffs: lunaticBluffs, fakes_pending: fakesPending, room_code: roomCode,
      travelers, traveler_roles, traveler_recommended: travelerRec, total_players: totalPlayers,
      exile_quorum: exileQuorum, day_stage: dayStage, players, night_kills: nightKills,
      fortuneteller_red: fortunetellerRed, night_choices: nightChoices, night_actions: nightActions,
      winner, fabled, fabled_pool: fabledPool, chats: stChats } = view
    // 旅行者:补上角色对象便于展示;阵营说书人可见(玩家只知道自己的)
    const tById = Object.fromEntries((traveler_roles || []).map((r) => [r.id, r]))
    const tList = (travelers || []).map((t) => ({ ...t, role: t.role_id ? tById[t.role_id] : null }))
    const tNames = Object.fromEntries(tList.map((t) => [t.id, t.name]))
    const nomIsTraveler = current && typeof current.nominee === 'string'

    // 💬 说书人私聊徽章(模板要用,必须先算):有邀请或已在群里时顶栏显眼提示
    const stChatBadge = (stChats || []).some((c) => !c.closed && (c.invites || []).some((i) => i.who === 'st'))
      ? '有私聊邀请!'
      : (stChats || []).some((c) => !c.closed && (c.members || []).some((m) => m.who === 'st'))
        ? '你在私聊中' : ''
    const stChatName = (w) => (String(w) === 'st' ? '🕯 说书人'
      : (/^\d+$/.test(String(w)) ? (((seats.find((x) => x.seat === Number(w)) || {}).player || {}).name || `${w}号`)
        : (((tList || []).find((t) => t.id === w) || {}).name || w)))

    // ---- 📜 独立复盘视图(终局后魔典切换):时间线 + 标错/撤销标注 ----
    if (winner && reviewMode) {
      const review = view.review || { groups: [], has_data: false }
      app.replaceChildren(h(`<div class="page st">
        <div class="st-head"><h1>📜 复盘</h1><span class="sub">血染钟楼 · 终局复盘(说书人讲解用)</span>
          <div class="st-actions"><button class="btn" id="review-back">↩ 返回魔典</button></div></div>
        <div class="review-page">
          ${review.has_data
            ? review.groups.map((g) => `<div class="review-group"><h4>${esc(g.label)}</h4>`
                + g.items.map((it) => `<div class="review-line ${it.wrong ? 'wrong' : ''}">
                    <span>${it.wrong ? '⚠ ' : ''}${it.text}${it.why ? ` <span class="review-why">(${esc(it.why)})</span>` : ''}</span>
                    ${it.mark ? `<button class="chip small ${it.wrong ? '' : 'danger'}" data-mark-seat="${it.mark.seat}"
                      data-mark-night="${it.mark.night}" data-mark-wrong="${it.wrong ? 0 : 1}">${it.wrong ? '↩ 撤销标错' : '❌ 标错'}</button>` : ''}
                  </div>`).join('') + '</div>').join('')
            : '<p class="hint">本局没有复盘数据(旧存档或未记录事件)</p>'}
        </div>
      </div>`))
      document.getElementById('review-back').onclick = () => { reviewMode = false; paint(view) }
      document.querySelectorAll('[data-mark-seat]').forEach((b) => {
        b.onclick = async () => {
          try {
            await stApi('/api/review/mark', { method: 'POST', body: JSON.stringify({
              seat: Number(b.dataset.markSeat), night: Number(b.dataset.markNight),
              wrong: b.dataset.markWrong === '1' }) })
          } catch (e) {
            // 推送会重绘,此处只需吞掉错误(标错目标不存在等)
          }
        }
      })
      return
    }
    const minP = scripts.find((s) => s.id === script)?.min || 5 // 该板子的人数下限(瓦釜雷鸣 7 人起)
    const seatedCount = seats.filter((s) => s.player).length
    if (status === 'playing') { manual = false; draft = {}; draftFakes = {}; draftLunMinions = {}; draftLunBluffs = {} } // 发牌完成后退出草稿
    const allSeated = seatedCount === count
    const selSeat = seats.find((s) => s.seat === selected)
    const selP = selSeat && selSeat.player
    const phaseTxt = status === 'playing'
      ? (phase === 'night' ? `🌙 第 ${nightNo} 夜`
        : phase === 'day' ? `☀️ 第 ${dayNo} 天 · ${dayStage === 'nom' ? '🗳 提名' : '💬 公聊'}` : '')
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
          <button class="btn primary" id="assign-btn" ${status === 'playing' || manual ? 'disabled' : ''}>🎲 随机分配角色</button>
          ${status === 'lobby' && canStart && !allSeated
            ? '<button class="btn primary" id="start-btn">🌙 开始游戏(人未齐)</button>'
            : ''}
          <button class="btn small ghost" id="load-btn" title="从磁盘恢复上次自动存档">💾 读档</button>
          <button class="btn danger" id="reset-btn">重置本局</button>
          ${status === 'playing' && !winner ? '<button class="btn primary" id="end-btn">🏁 结算</button>' : ''}
          ${status === 'playing' && phase === 'day' && !winner && stChatBadge
            ? `<button class="btn small primary" id="st-chat-badge">💬 ${stChatBadge}</button>`
            : ''}
        </div>
      </div>
      ${winner
        ? `<div class="end-banner">🏆 本局结束:${winner === 'good' ? '善良' : '邪恶'}阵营获胜
            <button class="chip small primary" id="end-review">📜 复盘</button>
            <button class="chip small ghost" id="end-undo">↩ 撤销结算</button></div>`
        : ''}
      ${endPick
        ? `<div class="end-pick">🏁 判定获胜方:
            <button class="chip tc-good" data-end="good">善良阵营获胜</button>
            <button class="chip tc-evil" data-end="evil">邪恶阵营获胜</button>
            <button class="chip ghost" id="end-cancel">取消</button>
          </div>`
        : ''}
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
            <label>房间号
              <input class="input" id="room-code" maxlength="4" inputmode="numeric" style="width:4.5em"
                value="${esc(roomCode)}">
              <button class="btn small" id="room-random" title="随机换一个房间号">🎲</button>
            </label>
            <span class="hint">修改板子/人数会清空座位,玩家需重新入座</span>
            <span class="hint">🧙 传奇角色(公开,说书人勾选):
              ${(fabledPool || []).map((f) => `<button class="chip small fabled-chip ${(fabled || []).some((x) => x.id === f.id) ? 'on' : ''}" data-fabled="${f.id}" title="${esc(f.ability)}">${esc(f.name)}</button>`).join('')}
            </span>
            <span class="hint">🧙 哨兵(神职角色,外来者数调整):
              ${[0, -1, 2, 1].map((v) => {
                // 关 / −1 / 不变 / +1;「不变」= 哨兵在场但不调整,方向保密玩家只知在场。
                // −1 禁用只看官方基础配比有无外来者(与后端一致),不看当前哨兵选择——
                // 之前扣回当前 delta 会误禁:+1 状态下想改 −1(基础外来者=1)会被错误禁用
                const off = status === 'playing' || (v === -1 && (composition[1] || 0) < 1)
                const label = v === 0 ? '关' : v === 2 ? '不变' : v > 0 ? '+1 外来者' : '−1 外来者'
                return `<button class="chip small sentinel-chip ${sentinel === v ? 'on' : ''}" data-sentinel="${v}"
                  ${off ? 'disabled' : ''}>${label}</button>`
              }).join('')}
            </span>
          </div>
          <div class="st-circle">
            <div id="circle"></div>
            <p class="hint">已入座 ${seatedCount}/${count}${status === 'playing' ? ' · 游戏中' : ' · 等待开局'}${allSeated && status === 'lobby' ? ' · 可以分配角色' : ''}${!allSeated && status === 'lobby' && canStart ? ' · 已预发全部身份,人未齐也可开始' : ''}${!allSeated && status === 'lobby' && !canStart ? ' · 人未齐:随机分配或手动发身份后即可开始' : ''}${bluffs && bluffs.length && !manual ? ' · 🧪 伪装:' + bluffs.map((r) => r.name).join('/') : ''}</p>
          </div>
          ${status === 'playing'
            ? `<div class="traveler-strip">
                <div class="t-strip-head">🎒 旅行者 ${tList.length ? `· ${tList.length} 人` : ''}
                  <span class="hint">流放需 ≥${exileQuorum} 票(全体 ${totalPlayers} 人一半) · 加入与流放不限时刻</span>
                  <input class="input t-add-input" id="t-add-name" maxlength="20" placeholder="新旅行者名字">
                  <button class="chip small" id="t-add" title="说书人直接添加旅行者(无手机关联,代管投票/生死)">➕ 添加</button>
                </div>
                ${tList.map((t) => `<div class="t-row ${t.alive ? '' : 'dead'}">
                  <span class="t-name">🎒 ${esc(t.name)}</span>
                  ${t.role
                    ? `<span class="chip team-traveler" title="${esc(t.role.ability)}">${esc(t.role.name)}</span>
                       <span class="t-align ${t.align}">${t.align === 'evil' ? '邪恶' : '善良'}</span>`
                    : `<button class="chip ghost" data-t-assign="${t.id}">指派角色</button>`}
                  ${t.alive ? '' : (t.exiled ? '<span class="t-state">🏴 已流放</span>' : '<span class="t-state">☠ 已死亡</span>')}
                  ${!t.alive && t.dead_vote_used ? '<span class="t-state">🗳 死票已交</span>' : ''}
                  <span class="t-actions">
                    ${current && !t.exiled
                      ? `<button class="chip small ${current.votes.includes(t.id) ? 'on' : ''}" data-t-vote="${t.id}"
                          title="${t.alive ? '旅行者举手投票' : '死亡旅行者举手(交出唯一死票)'}">🗳 举手</button>`
                      : ''}
                    ${t.role && !t.exiled ? `<button class="chip small ghost" data-t-alive="${t.id}">${t.alive ? '☠ 死亡' : '💚 复活'}</button>` : ''}
                    <button class="chip small ghost" data-t-exile="${t.id}">${t.exiled ? '↩ 撤销流放' : '🏴 流放'}</button>
                  </span>
                </div>`).join('')}
                ${tList.length ? '' : '<p class="hint">满座或迟到的玩家可在手机上点「以旅行者身份加入」,在这里指派角色</p>'}
              </div>`
            : ''}
        </div>
        <div class="st-right">
          <div id="detail"></div>
          <h3>玩家加入</h3>
          <img src="/api/qr?t=${encodeURIComponent(roomCode)}" alt="加入二维码" class="qr">
          <p class="hint">房间号 <b>${esc(roomCode)}</b> · 扫码自动预填,改号后请告知玩家新码</p>
          ${(stChats || []).filter((c) => c.closed).length
            ? `<div class="wish-list"><h4>📦 私聊档案(说书人留档,玩家端已销毁)</h4>
                ${stChats.filter((c) => c.closed).map((c) => `<p class="wish-line">
                  <button class="chip small" data-st-archive="${c.id}">${stArchiveOpen === c.id ? '收起' : '查看'}</button>
                  <span class="chat-dot" style="background:${c.color}"></span>${(c.members || []).map((m) => esc(m.name)).join('、')}</p>
                  ${stArchiveOpen === c.id ? `<div class="st-chat-msgs">${c.messages.length
                    ? c.messages.map((m) => `<p class="chat-msg"><b>${esc(m.name)}</b>:${esc(m.text)}</p>`).join('')
                    : '<p class="hint">无消息</p>'}</div>` : ''}`).join('')}
              </div>`
            : ''}
          ${(players || []).filter((p) => p.wish).length
            ? `<div class="wish-list"><h4>🙏 许愿(配板参考)</h4>
                ${players.filter((p) => p.wish).map((p) => `<p class="wish-line">${esc(p.name)}${p.seat ? `(${p.seat}号)` : '(未入座)'} → <span class="wish-tag ${p.wish === '善良' ? 'good' : p.wish === '邪恶' ? 'evil' : ''}">${esc(p.wish)}</span></p>`).join('')}
              </div>`
            : ''}
        </div>
      </div>
    </div>`))

    dramaOverlay(roomCode, phase, nightNo, status) // 🕯 第一夜戏剧(说书人端同步播放)
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
    const FAKE_LABEL = { drunk: '🍺 酒鬼', lunatic: '🌙 疯子' }
    const FAKE_ICON = { drunk: '🍺', lunatic: '🌙' }

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
      if (sentinel === 1 || sentinel === -1) {
        expected[1] += sentinel // 哨兵:说书人已选的外来者 +1/−1(2=不变 不调整)
        expected[0] -= sentinel // 镇民反向调整,总人数保持不变
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
      if (sentinel) adjTexts.push(sentinel === 2 ? '哨兵:不变'
        : `哨兵:${sentinel > 0 ? '+' : ''}${sentinel}外/${-sentinel > 0 ? '+' : ''}${-sentinel}镇`)
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
      // 伪装:发身份时选好 3 个不在场好角色(暗流涌动限镇民,其余脚本镇民+外来者)。
      // 已进入草稿的角色从候选池剔除;进入手动模式时带回上次选好的伪装
      const bluffTeams = script === 'trouble-brewing' ? ['townsfolk'] : ['townsfolk', 'outsider']
      if (!draftBluffs.length && bluffs && bluffs.length) draftBluffs = bluffs.map((r) => r.id)
      draftBluffs = draftBluffs.filter((rid) => !Object.values(draft).includes(rid)) // 被发到座位 → 自动移出伪装
      const bluffPool = roles.filter((r) => bluffTeams.includes(r.team) && !Object.values(draft).includes(r.id))
      const bluffOk = draftBluffs.length === 3
      const box = h(`<div class="st-detail">
        <h3>🃏 手动发身份${selSeat ? ` · 座位 ${selSeat.seat}${selSeat.player ? `(${esc(selSeat.player.name)})` : '(空)'}` : ''}</h3>
        <p class="manual-summary ${full && ok && !hasDup ? '' : 'warn'}">${summaryTxt} · 🧪 伪装 ${draftBluffs.length}/3${hasDup ? ' · ⚠ 角色重复,请先取消重复项' : ''}</p>
        ${adjLine}
        ${gfChoice}
        <p class="hint">${selSeat ? (selSeat.player ? '点击角色发给该座位,再点一次取消' : '该座还没人:可以先发身份,玩家入座自动继承') : '先点击环形座位,再选角色'}</p>
      </div>`)
      const usedBy = {} // 角色 id → 已发的座位号(角色全局唯一,已发出的不可再发)
      for (const [seat, rid] of Object.entries(draft)) usedBy[rid] = Number(seat)
      TEAM_ORDER.forEach(([team, label]) => {
        const group = h(`<div class="role-group team-${team}"><span class="role-group-head">${label}</span></div>`)
        roles.filter((r) => r.team === team).forEach((r) => {
          const on = selSeat && draft[selSeat.seat] === r.id
          const usedSeat = usedBy[r.id]
          const usedElsewhere = usedSeat != null && (!selSeat || usedSeat !== selSeat.seat)
          const chip = h(`<button class="chip team-${r.team} ${on ? 'on' : ''} ${usedElsewhere ? 'used' : ''}"
              title="${esc(r.ability)}${usedElsewhere ? `&#10;已发:座位 ${usedSeat}` : ''}">
              ${(FAKE_ICON[r.id] || '') + esc(r.name)}${usedElsewhere ? `<span class="chip-used">${usedSeat}号</span>` : ''}</button>`)
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
      const bluffGroup = h(`<div class="role-group" style="--team: var(--gold); --team-text: var(--on-gold)"><span class="role-group-head">🧪 伪装(不在场好角色,点选 3 个)</span></div>`)
      bluffPool.forEach((r) => {
        const on = draftBluffs.includes(r.id)
        const chip = h(`<button class="chip team-${r.team} ${on ? 'on' : ''}" title="${esc(r.ability)}">${esc(r.name)}</button>`)
        chip.onclick = () => {
          if (on) draftBluffs = draftBluffs.filter((x) => x !== r.id)
          else if (draftBluffs.length < 3) draftBluffs.push(r.id)
          paint(view)
        }
        bluffGroup.appendChild(chip)
      })
      box.appendChild(bluffGroup)
      // 认知覆盖由说书人显式选定:疯子以为自己是恶魔(还须指定假爪牙与 3 个假伪装)、酒鬼看到假镇民
      const fakeNeeded = Object.entries(draft).filter(([, rid]) => fakePools && fakePools[rid])
      // 疯子假伪装候选:好角色即可——允许与在场角色/真伪装相同(假身份不计算配板)
      const lunBluffPool = roles.filter((r) => bluffTeams.includes(r.team))
      fakeNeeded.forEach(([seat, rid]) => {
        if (draftFakes[seat] && !(fakePools[rid].includes(roleById[draftFakes[seat]]?.team))) delete draftFakes[seat]
        if (!draftLunMinions[seat]) draftLunMinions[seat] = []
        if (!draftLunBluffs[seat]) draftLunBluffs[seat] = []
        draftLunBluffs[seat] = draftLunBluffs[seat].filter((b) => lunBluffPool.some((r) => r.id === b))
      })
      const fakeOk = fakeNeeded.every(([seat, rid]) => draftFakes[seat]
        && (rid !== 'lunatic' || (draftLunMinions[seat].length >= 1 && draftLunBluffs[seat].length === 3)))
      if (fakeNeeded.length) {
        const fakeGroup = h(`<div class="role-group" style="--team: var(--gold); --team-text: var(--on-gold)"><span class="role-group-head">🧠 认知覆盖(说书人选定假身份${fakeOk ? '' : ' · 未选完'})</span></div>`)
        fakeNeeded.forEach(([seat, rid]) => {
          // 假身份做成框点选(再点已选中的框=清除);可与已发角色重复、不计算配板、不标已用
          const row = h(`<div class="st-fake"><span class="hint">${FAKE_LABEL[rid] || '认知覆盖'} · ${seat}号 看到:</span></div>`)
          roles.filter((r) => fakePools[rid].includes(r.team)).forEach((r) => {
            const on = draftFakes[seat] === r.id
            const chip = h(`<button class="chip team-${r.team} ${on ? 'on' : ''}" title="${esc(r.ability)}">${esc(r.name)}</button>`)
            chip.onclick = () => { draftFakes[seat] = on ? '' : r.id; paint(view) }
            row.appendChild(chip)
          })
          fakeGroup.appendChild(row)
          if (rid === 'lunatic') {
            const minRow = h(`<div class="st-fake"><span class="hint">以为爪牙是(点选座位):</span></div>`)
            for (let s = 1; s <= count; s++) {
              if (s === Number(seat)) continue
              const on = draftLunMinions[seat].includes(s)
              const chip = h(`<button class="chip ${on ? 'on' : ''}" data-lunmin="${seat}:${s}">${s}号</button>`)
              chip.onclick = () => {
                if (on) draftLunMinions[seat] = draftLunMinions[seat].filter((x) => x !== s)
                else draftLunMinions[seat] = [...draftLunMinions[seat], s]
                paint(view)
              }
              minRow.appendChild(chip)
            }
            fakeGroup.appendChild(minRow)
            const bluffRow = h(`<div class="st-fake"><span class="hint">疯子伪装(3):</span></div>`)
            lunBluffPool.forEach((r) => {
              const on = draftLunBluffs[seat].includes(r.id)
              const chip = h(`<button class="chip team-${r.team} ${on ? 'on' : ''}" data-lunbluff="${seat}:${r.id}" title="${esc(r.ability)}">${esc(r.name)}</button>`)
              chip.onclick = () => {
                if (on) draftLunBluffs[seat] = draftLunBluffs[seat].filter((x) => x !== r.id)
                else if (draftLunBluffs[seat].length < 3) draftLunBluffs[seat] = [...draftLunBluffs[seat], r.id]
                paint(view)
              }
              bluffRow.appendChild(chip)
            })
            fakeGroup.appendChild(bluffRow)
          }
        })
        box.appendChild(fakeGroup)
      }
      box.appendChild(h(`<div class="st-detail-actions">
        <button class="btn primary small" id="manual-confirm" ${full && ok && !hasDup && bluffOk && fakeOk ? '' : 'disabled'}>✅ 确认发身份</button>
        <button class="btn small ghost" id="manual-cancel">取消</button>
      </div>`))
      detail.replaceChildren(box)
      box.querySelectorAll('[data-gf]').forEach((b) => {
        b.onclick = () => { godfatherAdj = Number(b.dataset.gf); paint(view) }
      })
      document.getElementById('manual-confirm').onclick = () => act(() => {
        const assignments = Object.entries(draft).map(([seat, role]) => ({ seat: Number(seat), role }))
        const fakes = Object.entries(draftFakes)
          .filter(([seat]) => draft[seat] && fakePools && fakePools[draft[seat]] && draftFakes[seat])
          .map(([seat, role]) => ({ seat: Number(seat), role,
            ...(draft[seat] === 'lunatic'
              ? { minions: draftLunMinions[seat], bluffs: draftLunBluffs[seat] }
              : {}) }))
        return stApi('/api/assign/manual', { method: 'POST', body: JSON.stringify({ assignments, bluffs: draftBluffs, fakes }) })
          .then((v) => { manual = false; draft = {}; draftBluffs = []; draftFakes = {}; draftLunMinions = {}; draftLunBluffs = {}; selected = null; paint(v) })
          // 空座预发时状态仍是 lobby,直接以响应视图重绘(不等推送)
      })
      document.getElementById('manual-cancel').onclick = () => {
        manual = false; draft = {}; draftFakes = {}; draftLunMinions = {}; draftLunBluffs = {}; paint(view)
      }
    }

    // ---- 选中玩家详情条(夜晚/白天面板顶部复用) ----

    function markerRow(slot) {
      const ms = slot.markers || []
      const rc = slot.role_change
      const tc = slot.team_change
      return `<div class="st-markers"><span class="hint">标记:</span>
        ${Object.entries(MARKER_LABEL).map(([k, l]) => {
          if (k === 'role-change') // 角色转变带数据:选定后按钮显示变成的角色(无背景色),再点=清除
            return `<button class="chip ${rc ? 'on plain' : ''} marker-chip m-${k}" data-mk="${k}">${rc ? `角色转变→${esc(rc.name)}` : l}</button>`
          if (k === 'team-change') // 阵营转变带数据:选定后按钮显示新阵营(无背景色),再点=清除
            return `<button class="chip ${tc ? 'on plain' : ''} marker-chip m-${k}" data-mk="${k}">${tc ? `阵营转变→${tc === 'good' ? '善良' : '邪恶'}` : l}</button>`
          if (k === 'mad') // 疯狂带内容:选定后按钮显示疯狂宣称的角色(被疯狂者手机被告知)
            return `<button class="chip ${ms.includes(k) ? 'on plain' : ''} marker-chip m-${k}" data-mk="${k}">${ms.includes(k) ? `疯狂→${slot.mad_about ? esc(slot.mad_about.name) : '?'}` : l}</button>`
          return `<button class="chip ${ms.includes(k) ? 'on' : ''} marker-chip m-${k}" data-mk="${k}">${l}</button>`
        }).join('')}
      </div>
      ${rolePickSeat === slot.seat ? `<div class="st-fake"><span class="hint">变成哪个角色(点选):</span>
        ${roles.map((r) => `<button class="chip team-${r.team}" data-role-pick="${r.id}" title="${esc(r.ability)}">${esc(r.name)}</button>`).join('')}
      </div>` : ''}
      ${teamPickSeat === slot.seat ? `<div class="st-fake"><span class="hint">变成哪个阵营(点选):</span>
        <button class="chip tc-good" data-team-pick="good">善良</button>
        <button class="chip tc-evil" data-team-pick="evil">邪恶</button>
      </div>` : ''}
      ${madPickSeat === slot.seat ? `<div class="st-fake"><span class="hint">疯狂宣称哪个善良角色(点选):</span>
        ${roles.filter((r) => r.team === 'townsfolk' || r.team === 'outsider')
          .map((r) => `<button class="chip team-${r.team}" data-mad-about="${r.id}" title="${esc(r.ability)}">${esc(r.name)}</button>`).join('')}
      </div>` : ''}`
    }

    function selPDetailHtml(slot, p) {
      return `<div class="st-detail sel-strip ${p.alive ? '' : 'dead'}">
        <h3>座位 ${p.seat} · ${esc(p.name)}</h3>
        ${p.wish ? `<p class="hint">🙏 许愿:${esc(p.wish)}</p>` : ''}
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

    // 空座详情条(测试/控制):预发身份 + 完整状态栏(含生死/投票,以说书人标记为准)
    function emptySeatStrip(slot) {
      return `<div class="st-detail sel-strip ${slot.alive === false ? 'dead' : ''}">
        <h3>座位 ${slot.seat} · 空(预发)${slot.alive === false ? ' · ☠' : ''}</h3>
        ${slot.assigned_role
          ? `<span class="team-badge team-${slot.assigned_role.team}">${TEAM_LABEL[slot.assigned_role.team]} · ${esc(slot.assigned_role.name)}</span>`
          : '<p class="hint">未预发身份</p>'}
        ${fakeRow(slot)}
        ${markerRow(slot)}
        <div class="st-detail-actions">
          <button class="btn small" id="act-alive">${slot.alive === false ? '复活' : '☠ 标记死亡'}</button>
        </div>
        <p class="hint">标记/转变/生死可先行设定,玩家入座后自动继承</p>
      </div>`
    }

    function wireSelPDetail() {
      const aliveBtn = document.getElementById('act-alive')
      if (aliveBtn && selP) aliveBtn.onclick = () => act(() => stApi(`/api/player/${selP.id}/alive`, { method: 'POST' }))
      else if (aliveBtn && selSeat && selSeat.assigned_role) {
        aliveBtn.onclick = () => act(() => stApi(`/api/seat/${selSeat.seat}/alive`, { method: 'POST' })) // 空座生死(说书人标记为准)
      }
      const removeBtn = document.getElementById('act-remove')
      if (removeBtn && selP) armClick(removeBtn, `确认移除 ${selP.name}?`,
        () => act(() => stApi(`/api/player/${selP.id}/remove`, { method: 'POST' })))
      detail.querySelectorAll('.marker-chip').forEach((c) => {
        c.onclick = () => {
          // 角色转变带数据:未选时点开角色选择行,已选时再点=清除
          if (c.dataset.mk === 'role-change') {
            if (selSeat.role_change) {
              act(() => stApi('/api/marker', { method: 'POST', body: JSON.stringify({ seat: selSeat.seat, marker: 'role-change', on: false }) }))
            } else {
              rolePickSeat = selSeat.seat
              paint(view)
            }
            return
          }
          // 阵营转变带数据:未选时点开新阵营选择行,已选时再点=清除
          if (c.dataset.mk === 'team-change') {
            if (selSeat.team_change) {
              act(() => stApi('/api/marker', { method: 'POST', body: JSON.stringify({ seat: selSeat.seat, marker: 'team-change', on: false }) }))
            } else {
              teamPickSeat = selSeat.seat
              paint(view)
            }
            return
          }
          // 疯狂带数据:未选时点开善良角色选择行,已选时再点=清除(被疯狂者手机会被通知)
          if (c.dataset.mk === 'mad') {
            if ((selSeat.markers || []).includes('mad')) {
              act(() => stApi('/api/marker', { method: 'POST', body: JSON.stringify({ seat: selSeat.seat, marker: 'mad', on: false }) }))
            } else {
              madPickSeat = selSeat.seat
              paint(view)
            }
            return
          }
          act(() => stApi('/api/marker', {
            method: 'POST',
            body: JSON.stringify({ seat: selSeat.seat, marker: c.dataset.mk, on: !(selSeat.markers || []).includes(c.dataset.mk) }),
          }))
        }
      })
      detail.querySelectorAll('[data-role-pick]').forEach((b) => {
        b.onclick = () => {
          rolePickSeat = null
          act(() => stApi('/api/marker', { method: 'POST', body: JSON.stringify({ seat: selSeat.seat, marker: 'role-change', on: true, role: b.dataset.rolePick }) }))
        }
      })
      detail.querySelectorAll('[data-team-pick]').forEach((b) => {
        b.onclick = () => {
          teamPickSeat = null
          act(() => stApi('/api/marker', { method: 'POST', body: JSON.stringify({ seat: selSeat.seat, marker: 'team-change', on: true, team: b.dataset.teamPick }) }))
        }
      })
      detail.querySelectorAll('[data-mad-about]').forEach((b) => {
        b.onclick = () => {
          madPickSeat = null
          act(() => stApi('/api/marker', { method: 'POST', body: JSON.stringify({ seat: selSeat.seat, marker: 'mad', on: true, about: b.dataset.madAbout }) }))
        }
      })
    }

    // ---- 夜晚流程助手 ----

    function renderNightPanel(detail) {
      const strip = selP ? selPDetailHtml(selSeat, selP) : (selSeat && selSeat.assigned_role ? emptySeatStrip(selSeat) : '')
      const steps = night.steps
      const cur = steps[night.idx]
      let wake = []
      if (cur) {
        if (cur.key === 'minioninfo') wake = seats.filter((s) => s.player && s.player.role && s.player.role.team === 'minion')
        else if (cur.key === 'demoninfo') wake = seats.filter((s) => s.player && s.player.role && s.player.role.team === 'demon')
        else if (cur.fake_for != null) wake = seats.filter((s) => s.seat === cur.fake_for)
        else if (cur.traveler) wake = tList.filter((t) => t.role_id === cur.key && t.alive)
          .map((t) => ({ seat: t.id, traveler: true, player: { name: t.name, alive: t.alive } }))
        else if (cur.key !== 'dusk' && cur.key !== 'dawn') wake = seats.filter((s) => s.player && s.player.role && s.player.role.id === cur.key)
      }
      const wakeTxt = wake.length
        ? '唤醒:' + wake.map((s) => `${s.traveler ? '🎒 ' + esc(s.player.name) : s.seat + '号 ' + esc(s.player.name)}${s.player.alive ? '' : ' ☠'}`).join('、')
        : (cur && cur.key !== 'dusk' && cur.key !== 'dawn' && !cur.traveler ? '该角色不在场,此步可跳过' : '')
      // 认知覆盖步骤:按座位真实身份区分 🍺 酒鬼 / 🌙 疯子(图标不再一样)
      const realRoleAt = (seat) => {
        const s = seats.find((x) => x.seat === seat)
        if (!s) return null
        const r = s.player ? s.player.role : s.assigned_role
        return r ? r.id : null
      }
      const fakeLabel = (seat) => (realRoleAt(seat) === 'lunatic' ? '🌙 疯子' : '🍺 酒鬼')
      const fakeIcon = (seat) => (realRoleAt(seat) === 'lunatic' ? '🌙' : '🍺')
      const fakeNote = cur && cur.fake_for != null ? ` · ${fakeLabel(cur.fake_for)}扮演(${cur.fake_for}号)` : ''
      // 会面步:告诉爪牙谁是恶魔、谁是疯子 / 告诉恶魔谁是爪牙、谁是疯子(空座预发也列出)
      const seatTxt = (list) => list.map((d) => `${d.seat}号 ${d.name ? esc(d.name) : '空(预发)'}`).join('、')
      const lunRelTxt = (lunaticSeats && lunaticSeats.length)
        ? `<div class="step-seats">🌙 疯子:${seatTxt(lunaticSeats)}(他就是疯子,不是真恶魔)</div>`
        : ''
      const relationTxt = (cur && cur.key === 'minioninfo' && demonSeats && demonSeats.length)
        ? `<div class="step-seats">👉 恶魔:${seatTxt(demonSeats)}</div>
           <div class="step-seats">👥 爪牙同时醒来,彼此可见:${seatTxt(minionSeats)}</div>
           ${lunRelTxt}`
        : (cur && cur.key === 'demoninfo' && minionSeats && minionSeats.length)
          ? `<div class="step-seats">👉 爪牙:${seatTxt(minionSeats)}</div>${lunRelTxt}`
          : ''
      // 疯子步骤(或其扮演恶魔的附加步):说书人按选定信息演戏——假爪牙 + 假伪装
      const lunOf = (seat) => {
        const mins = (lunaticMinions && lunaticMinions[String(seat)]) || []
        const lbs = (lunaticBluffs && lunaticBluffs[String(seat)]) || []
        return `🌙 疯子(${seat}号):以为爪牙是 ${mins.length ? mins.map((s) => `${s}号`).join('、') : '未定'} · 给他的伪装 ${lbs.length ? lbs.map((r) => esc(r.name)).join(' · ') : '未定'}`
      }
      const lunStepTxt = (cur && cur.key === 'lunatic' && lunaticSeats && lunaticSeats.length)
        ? lunaticSeats.map((l) => `<div class="step-seats">${lunOf(l.seat)}</div>`).join('')
        : (cur && cur.fake_for != null && lunaticMinions && lunaticMinions[String(cur.fake_for)] != null
          ? `<div class="step-seats">${lunOf(cur.fake_for)}</div>`
          : '')
      // 恶魔会面步:顺带展示三个伪装,说书人告知恶魔
      const bluffTxt = (cur && cur.key === 'demoninfo' && bluffs && bluffs.length)
        ? `<p class="bluffs">🧪 告知恶魔三个伪装:${bluffs.map((r) => esc(r.name)).join(' · ')}</p>`
        : ''
      // 认知覆盖待定:发牌后说书人还没选定假身份的座位,先别让玩家看卡
      const pendingTxt = (fakesPending && fakesPending.length)
        ? `<div class="step-seats">⚠ 认知覆盖待定:${fakesPending.map((f) => `${f.seat}号 ${esc(f.role.name)}`).join(' · ')} — 选定假身份后再让玩家看卡</div>`
        : ''
      // 手机刀人(瓦釜雷鸣):恶魔/疯子在手机上的选择,说书人实时可见
      const killEntry = nightKills && nightKills[String(nightNo)]
      const DEMON_KEYS = ['imp', 'fang-gu', 'vigormortis']
      const killTxt = (cur && killEntry)
        ? (DEMON_KEYS.includes(cur.key) && !cur.fake_for && killEntry.seat != null
            ? `<div class="step-seats">😈 恶魔手机已选择刀杀:${killEntry.seat}号 · 天亮自动执行,走到此步前仍可改</div>`
            : (cur.key === 'lunatic' || (cur.fake_for != null && cur.fake_for === killEntry.lunatic_by))
              ? killEntry.lunatic_seat != null
                ? `<div class="step-seats">🩻 疯子手机选择(演戏,不执行):${killEntry.lunatic_seat}号</div>`
                : ''
              : '')
        : ''
      // 占卜师宿敌(红鲱鱼):说书人私下标记一名善良玩家(只有说书人知道),占卜师查他总被当恶魔
      const seatRoleOf = (s) => (s.player ? s.player.role : s.assigned_role)
      const ftSeat = seats.find((s) => seatRoleOf(s) && seatRoleOf(s).id === 'fortuneteller')?.seat
      const redBox = (cur && cur.key === 'fortuneteller' && ftSeat != null)
        ? `<div class="step-seats">🐟 宿敌(红鲱鱼):${fortunetellerRed != null ? `${fortunetellerRed}号 · 可改` : '未标记(占卜师查他总被当恶魔)'}
            <span class="red-pick">${seats.filter((s) => {
              const r = seatRoleOf(s)
              return r && s.seat !== ftSeat && (r.team === 'townsfolk' || r.team === 'outsider')
            }).map((s) => `<button class="chip small ${fortunetellerRed === s.seat ? 'on' : ''}" data-red="${s.seat}" title="${esc((s.player || {}).name || '空座预发')}">${s.seat}号</button>`).join('')}</span>
            ${fortunetellerRed != null ? '<button class="chip small ghost" data-red-clear="">清除</button>' : ''}
          </div>`
        : ''
      // 夜晚信息交互:该角色对应的玩家手机选择 + 说书人电子回复
      const choiceEntry = (cur && nightChoices && nightChoices[String(nightNo)])
        ? Object.entries(nightChoices[String(nightNo)])
          .find(([, c]) => c.role === cur.key)
        : null
      const choiceTxt = choiceEntry
        ? `<div class="step-seats">${choiceEntry[1].targets && choiceEntry[1].targets.length ? `🔮 手机选择:${choiceEntry[1].targets.map((t) => `${t}号`).join('、')}${choiceEntry[1].char ? ` → 变身:${esc((roleById[choiceEntry[1].char] || {}).name || choiceEntry[1].char)}` : ''}${choiceEntry[1].applied ? ' · ✅ 已变身' : ''}${choiceEntry[1].invalid ? ' · ❌ 所选角色已在场,未生效(麻脸巫婆不知情)' : ''}` : ''}${choiceEntry[1].reply ? `${choiceEntry[1].targets && choiceEntry[1].targets.length ? ' · ' : ''}已回复:${esc(choiceEntry[1].reply)}` : ''}</div>
           ${choiceEntry[1].char && choiceEntry[1].applied
             ? `<div class="step-seats"><button class="chip small ghost" id="transform-go">↩ 撤销变身(容错)</button></div>`
             : ''}
           <div class="step-seats">📩 回复该玩家:
             ${cur.key === 'fortuneteller'
               ? '<button class="chip small" data-reply="✅ 有恶魔">有恶魔</button><button class="chip small" data-reply="❌ 无恶魔">无恶魔</button>'
               : ''}
             <input class="input reply-input" id="reply-input" maxlength="100" placeholder="自定义信息">
             <button class="chip small primary" id="reply-go">发送</button>
           </div>`
        : ''
      // 麻脸巫婆创造恶魔:本夜死亡由说书人决定,恶魔手机选择不生效
      const arbTxt = (cur && killEntry && killEntry.arbitrary && DEMON_KEYS.includes(cur.key) && !cur.fake_for)
        ? '<div class="step-seats">⚠ 麻脸巫婆创造了恶魔:本夜死亡由说书人决定(恶魔手机选择不生效)</div>'
        : ''
      // 教父首夜信息:说书人告知在场的外来者角色(一键发送到教父手机,第二夜起才开放选人)
      const outsidersIn = seats.filter((s) => seatRoleOf(s) && seatRoleOf(s).team === 'outsider')
        .map((s) => seatRoleOf(s).name)
      const gfSeat = seats.find((s) => seatRoleOf(s) && seatRoleOf(s).id === 'godfather')?.seat
      const gfInfoTxt = outsidersIn.length ? `外来者:${outsidersIn.join('、')}` : '无外来者'
      const godfatherInfoBox = (cur && cur.key === 'godfather' && nightNo === 1 && gfSeat != null)
        ? `<div class="step-seats">👁 教父首夜信息:${gfInfoTxt}
            <button class="chip small" data-info="${gfSeat}" data-info-text="${esc(gfInfoTxt)}">📤 发送给教父</button>
            <input class="input reply-input" id="gf-custom" maxlength="100" placeholder="自定义信息">
            <button class="chip small primary" id="gf-send">发送</button>
          </div>`
        : ''
      // 寡妇:选自己 → 不告知任何善良玩家(官方规则);否则选一名善良玩家告知
      const wdSeat = seats.find((s) => seatRoleOf(s) && seatRoleOf(s).id === 'widow')?.seat
      const wdChoice = (wdSeat != null && nightChoices && nightChoices[String(nightNo)])
        ? nightChoices[String(nightNo)][String(wdSeat)]
        : null
      const wdSelf = wdChoice && wdChoice.targets && wdChoice.targets.includes(wdSeat)
      const widowAnnounce = (cur && cur.key === 'widow' && nightNo === 1)
        ? wdSelf
          ? '<div class="step-seats">🤫 寡妇选择了自己:不告知任何善良玩家(官方规则)</div>'
          : (wdChoice && wdChoice.targets && wdChoice.targets.length)
            ? `<div class="step-seats">📣 告知一名善良玩家「寡妇在场」:${seats.filter((s) => {
                const r = seatRoleOf(s)
                return r && (r.team === 'townsfolk' || r.team === 'outsider')
              }).map((s) => `<button class="chip small" data-announce="${s.seat}" title="${esc((s.player || {}).name || '')}">${s.seat}号</button>`).join('')}</div>`
            : '<div class="step-seats">⏳ 等寡妇选择毒人目标(选自己则跳过告知)</div>'
        : ''
      // 🗿 代操作:空座角色或说书人代玩家操作(便于测试人未齐开局)
      if (cur && cur.key !== opState.key) opState = { key: cur.key, pick: [], char: null }
      const opSeat = (() => {
        if (!cur || cur.fake_for != null) return null
        const isDemon = DEMON_KEYS.includes(cur.key)
        const isPick = nightActions && nightActions[cur.key]
        if (!isDemon && !isPick) return null
        const s = seats.find((x) => seatRoleOf(x) && seatRoleOf(x).id === cur.key)
        return s ? s.seat : null
      })()
      const opAct = (cur && nightActions && nightActions[cur.key]) || null
      const opBox = (cur && opSeat != null)
        ? `<div class="step-seats">🗿 代操作(${opSeat}号${(seats.find((s) => s.seat === opSeat) || {}).player ? '' : '空座'}):
            ${DEMON_KEYS.includes(cur.key)
              ? `<span class="red-pick">刀:${seats.filter((s) => s.player ? s.player.alive : s.assigned_role)
                  .map((s) => `<button class="chip small" data-op-kill="${s.seat}">${s.seat}号</button>`).join('')}</span>`
              : `<span class="red-pick">选:${seats.filter((s) => s.player || s.assigned_role)
                  .map((s) => `<button class="chip small ${opState.pick.includes(s.seat) ? 'on' : ''}" data-op-pick="${s.seat}">${s.seat}号</button>`).join('')}</span>
                 ${opAct && opAct.char
                   ? `<span class="red-pick">角色:${roles.filter((r) => !opAct.good_char || r.team === 'townsfolk' || r.team === 'outsider')
                       .map((r) => `<button class="chip small ${opState.char === r.id ? 'on' : ''}" data-op-char="${r.id}">${esc(r.name)}</button>`).join('')}</span>`
                   : ''}
                 <button class="chip small primary" id="op-go" ${opState.pick.length === (opAct ? opAct.count : 1) && (!opAct || !opAct.char || opState.char) ? '' : 'disabled'}>提交</button>`}
          </div>`
        : ''
      const box = h(`<div class="st-detail">
        ${strip}
        <div class="night-panel">
          <h3>🌙 第 ${nightNo} 夜 · 步骤 ${night.idx + 1}/${steps.length}</h3>
          ${pendingTxt}
          ${cur ? `<div class="step-card">
            <div class="step-name">${esc(cur.name)}${fakeNote}</div>
            ${wakeTxt ? `<div class="step-seats">${wakeTxt}</div>` : ''}
            ${relationTxt}
            ${lunStepTxt}
            ${killTxt}
            ${arbTxt}
            ${choiceTxt}
            ${godfatherInfoBox}
            ${widowAnnounce}
            ${opBox}
            ${redBox}
            <p class="step-hint">${esc(cur.hint)}</p>
            ${bluffTxt}
          </div>` : '<p class="hint">本夜没有步骤</p>'}
          <div class="step-list">
            ${steps.map((st, i) => `<button class="step-chip ${i < night.idx ? 'done' : ''} ${i === night.idx ? 'cur' : ''}"
                title="${esc(st.name)}${st.fake_for != null ? ` · ${fakeLabel(st.fake_for)}扮演(${st.fake_for}号)` : ''}">${i + 1} ${esc(st.name)}${st.fake_for != null ? ` ${fakeIcon(st.fake_for)}` : ''}</button>`).join('')}
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
      box.querySelectorAll('[data-red]').forEach((b) => {
        b.onclick = () => act(() => stApi('/api/fortuneteller/red', { method: 'POST', body: JSON.stringify({ seat: Number(b.dataset.red) }) }))
      })
      const redClear = box.querySelector('[data-red-clear]')
      if (redClear) redClear.onclick = () => act(() => stApi('/api/fortuneteller/red', { method: 'POST', body: JSON.stringify({ seat: null }) }))
      // 夜晚信息交互回复:快捷按钮直接发,自定义输入点发送
      box.querySelectorAll('[data-reply]').forEach((b) => {
        b.onclick = () => act(() => stApi('/api/night/reply', { method: 'POST', body: JSON.stringify({ seat: Number(choiceEntry[0]), text: b.dataset.reply }) }))
      })
      const replyGo = box.querySelector('#reply-go')
      if (replyGo) replyGo.onclick = () => {
        const v = (box.querySelector('#reply-input').value || '').trim()
        if (!v) return
        act(() => stApi('/api/night/reply', { method: 'POST', body: JSON.stringify({ seat: Number(choiceEntry[0]), text: v }) }))
      }
      // 教父首夜信息:一键发在场外来者列表,或自定义
      box.querySelectorAll('[data-info]').forEach((b) => {
        b.onclick = () => act(() => stApi('/api/night/reply', { method: 'POST', body: JSON.stringify({ seat: Number(b.dataset.info), text: b.dataset.infoText, role: 'godfather' }) }))
      })
      const gfSend = box.querySelector('#gf-send')
      if (gfSend) gfSend.onclick = () => {
        const v = (box.querySelector('#gf-custom').value || '').trim()
        if (!v) return
        act(() => stApi('/api/night/reply', { method: 'POST', body: JSON.stringify({ seat: gfSeat, text: v, role: 'godfather' }) }))
      }
      // 麻脸巫婆:说书人撤销已生效的变身(容错)
      const tgo = box.querySelector('#transform-go')
      if (tgo) tgo.onclick = () => act(() => stApi('/api/night/transform', { method: 'POST', body: JSON.stringify({ seat: Number(choiceEntry[0]) }) }))
      // 🗿 代操作(空座测试):刀人 / 选人 / 角色提交
      box.querySelectorAll('[data-op-kill]').forEach((b) => {
        b.onclick = () => act(() => stApi(`/api/seat/${opSeat}/kill`, { method: 'POST', body: JSON.stringify({ target: Number(b.dataset.opKill) }) }))
      })
      box.querySelectorAll('[data-op-pick]').forEach((b) => {
        b.onclick = () => {
          const s = Number(b.dataset.opPick)
          if (opState.pick.includes(s)) opState.pick = opState.pick.filter((x) => x !== s)
          else if (opState.pick.length < (opAct ? opAct.count : 1)) opState.pick = [...opState.pick, s]
          else return
          paint(view)
        }
      })
      box.querySelectorAll('[data-op-char]').forEach((b) => {
        b.onclick = () => { opState.char = opState.char === b.dataset.opChar ? null : b.dataset.opChar; paint(view) }
      })
      const opGo = box.querySelector('#op-go')
      if (opGo) opGo.onclick = () => act(() => stApi(`/api/seat/${opSeat}/choice`, {
        method: 'POST',
        body: JSON.stringify(opAct && opAct.char ? { targets: opState.pick, char: opState.char } : { targets: opState.pick }),
      }))
      // 寡妇:告知一名善良玩家寡妇在场
      box.querySelectorAll('[data-announce]').forEach((b) => {
        b.onclick = () => act(() => stApi('/api/night/reply', { method: 'POST', body: JSON.stringify({ seat: Number(b.dataset.announce), text: '⚠ 寡妇在场', role: 'widow-note' }) }))
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
      const strip = selP ? selPDetailHtml(selSeat, selP) : (selSeat && selSeat.assigned_role ? emptySeatStrip(selSeat) : '')
      const todays = nominations.filter((n) => n.day === dayNo)
      // 提名资格:每人每天只能发起一次提名(死者不能发起)、只能被提名一次(死者可被提名),可以提名自己;
      // 旅行者同样可以提名与被提名,被流放后离开小镇不能再被提名
      const nominatorToday = new Set(todays.map((n) => n.nominator))
      const nominatedToday = new Set(todays.map((n) => n.nominee))
      const fromOpts = seats.filter((s) => s.player)
        .map((s) => `<option value="${s.seat}" ${!s.player.alive || nominatorToday.has(s.seat) ? 'disabled' : ''}>${s.seat}号 · ${esc(s.player.name)}${s.player.alive ? '' : ' ☠'}${nominatorToday.has(s.seat) ? ' · 已提名过' : ''}</option>`).join('')
        + seats.filter((s) => !s.player && s.assigned_role)
          .map((s) => `<option value="${s.seat}" ${s.alive === false || nominatorToday.has(s.seat) ? 'disabled' : ''}>${s.seat}号 · 空座(${esc(s.assigned_role.name)})${s.alive === false ? ' ☠' : ''}</option>`).join('')
        + tList.filter((t) => t.alive && !t.exiled && !nominatorToday.has(t.id))
          .map((t) => `<option value="${t.id}">🎒 ${esc(t.name)}${t.role ? ' · ' + esc(t.role.name) : ' · 未指派'}${nominatorToday.has(t.id) ? ' · 已提名过' : ''}</option>`).join('')
      const toOpts = seats.filter((s) => s.player)
        .map((s) => `<option value="${s.seat}" ${nominatedToday.has(s.seat) ? 'disabled' : ''}>${s.seat}号 · ${esc(s.player.name)}${s.player.alive ? '' : ' ☠'}${nominatedToday.has(s.seat) ? ' · 已被提名' : ''}</option>`).join('')
        + seats.filter((s) => !s.player && s.assigned_role)
          .map((s) => `<option value="${s.seat}" ${nominatedToday.has(s.seat) ? 'disabled' : ''}>${s.seat}号 · 空座(${esc(s.assigned_role.name)})${s.alive === false ? ' ☠' : ''}${nominatedToday.has(s.seat) ? ' · 已被提名' : ''}</option>`).join('')
        + tList.filter((t) => !t.exiled && !nominatedToday.has(t.id))
          .map((t) => `<option value="${t.id}">🎒 ${esc(t.name)}${t.role ? ' · ' + esc(t.role.name) : ' · 未指派'}${t.alive ? '' : ' ☠'}${nominatedToday.has(t.id) ? ' · 已被提名' : ''}</option>`).join('')
      const hist = todays.length
        ? `<h4>今日提名</h4>` + todays.map((n) => `<div class="nom-row ${n.executed ? 'exec' : ''}">
            ${whoTxt(n.nominator, tNames)} 提名 ${whoTxt(n.nominee, tNames)}
            · 赞成 ${n.votes.length} 票 ${voteChips(n.votes, tNames)} ${n.executed ? (typeof n.nominee === 'string' ? '· 🏴 流放' : '· ⚔ 处决') : (n.passed ? '· ⚖ 待处决' : '· 未通过')}</div>`).join('')
        : '<p class="hint">今天还没有提名</p>'
      // 天黑预览:今天待处决的座位提名中,票数最多者将被处决;平票则无人处决
      const todaySeatNoms = todays.filter((n) => n.passed && typeof n.nominee === 'number')
      const endPreview = (() => {
        if (!todaySeatNoms.length) return ''
        const mx = Math.max(...todaySeatNoms.map((n) => n.votes.length))
        const top = todaySeatNoms.filter((n) => n.votes.length === mx)
        if (top.length === 1) return ` · 天黑将处决 ${whoTxt(top[0].nominee, tNames)}(${mx} 票)`
        return ` · 平票(${mx} 票),无人处决`
      })()
      const voting = current
        ? `<div class="vote-box">
            <p class="vote-title">🗳 ${whoTxt(current.nominator, tNames)} 提名 ${whoTxt(current.nominee, tNames)}</p>
            <p class="vote-line ${current.votes.length >= (nomIsTraveler ? exileQuorum : quorum) ? 'ok' : ''}">赞成 ${current.votes.length} 票 · ${nomIsTraveler ? `流放需 ≥${exileQuorum} 票(全体 ${totalPlayers} 人一半)` : `处决需 ≥${quorum} 票(存活玩家 ${aliveCount} 人,不含旅行者)`}</p>
            ${voteChips(current.votes, tNames)}
            <p class="hint">玩家可在手机上自行举手/发起提名,这里也可代记:点击环形座位记录举手,旅行者用下方横栏的 🗳;死者举手即交出唯一的死票(骷髅旁 🗳 消失),每人整局只有一票${nomIsTraveler ? ';流放表决不消耗死票,死者可自由支持' : ''}</p>
            <div class="st-detail-actions">
              <button class="btn small danger" id="nom-pass">${nomIsTraveler ? '🏴 流放(当场)' : '✅ 通过(待处决)'}</button>
              <button class="btn small ghost" id="nom-skip">${nomIsTraveler ? '❌ 未流放' : '❌ 未通过'}</button>
            </div>
            ${nomIsTraveler ? '' : '<p class="hint">通过只是上处决台(⚖ 待处决):天黑时当天待处决者中票数最多者被处决,平票无人处决</p>'}
          </div>`
        : dayStage === 'nom'
          ? `<div class="vote-box"><div class="nom-start">
              <select id="nom-from">${fromOpts}</select><span class="hint">提名</span>
              <select id="nom-to">${toOpts}</select>
              <button class="btn small primary" id="nom-go">发起提名</button>
            </div></div>`
          : ''
      // 白天子阶段切换(说书人控节奏):公聊私聊 ↔ 提名阶段
      const stageBox = `<div class="stage-switch">
        <button class="chip ${dayStage === 'talk' ? 'on' : ''}" data-stage="talk">💬 公聊私聊</button>
        <button class="chip ${dayStage === 'nom' ? 'on' : ''}" data-stage="nom">🗳 提名阶段</button>
      </div>`
      const talkBody = dayStage === 'talk'
        ? '<p class="hint">玩家正在公聊/私聊:准备好后切换「🗳 提名阶段」开放提名与投票</p>'
        : ''
      // 💬 私聊总览:说书人查看所有内容、可被邀请进群、可关闭/召回
      const stInvites = (stChats || []).filter((c) => !c.closed && (c.invites || []).some((i) => i.who === 'st'))
      const stChatsBox = (stChats || []).some((c) => !c.closed)
        ? `<div class="st-chats">
            <h4>💬 私聊 <button class="chip small ghost" id="chat-recall">🔔 召回全部</button></h4>
            ${stInvites.map((c) => `<p class="chat-invite">🙋 邀请说书人进群(${esc(stChatName(c.owner))}发起)
              <button class="chip small primary" data-st-inv="${c.id}" data-st-inv-y="1">✅ 接受</button>
              <button class="chip small ghost" data-st-inv="${c.id}" data-st-inv-y="0">❌ 拒绝</button></p>`).join('')}
            ${(stChats || []).filter((c) => !c.closed).map((c) => `<div class="st-chat-row ${(c.members || []).some((m) => m.who === 'st') ? 'mine' : ''}">
              <span class="chat-dot" style="background:${c.color}"></span>
              ${(c.members || []).map((m) => esc(m.name)).join('、')}${(c.members || []).some((m) => m.who === 'st') ? '<span class="hint">(你在群里)</span>' : ''}
              <button class="chip small" data-st-view="${c.id}">${stChatOpen === c.id ? '收起' : '查看'}</button>
              <button class="chip small ghost" data-st-close="${c.id}">关闭</button>
            </div>
            ${stChatOpen === c.id ? `<div class="st-chat-msgs">
              ${c.messages.length ? c.messages.map((m) => `<p class="chat-msg"><b>${esc(m.name)}</b>:${esc(m.text)}</p>`).join('') : '<p class="hint">暂无消息</p>'}
              ${(c.members || []).some((m) => m.who === 'st') ? `<div class="chat-input"><input class="input" id="st-chat-text" maxlength="500" placeholder="以说书人身份发言">
                <button class="btn small primary" id="st-chat-send">发送</button></div>` : '<p class="hint">(未入群,仅查看)</p>'}
            </div>` : ''}`).join('')}
          </div>`
        : ''
      const box = h(`<div class="st-detail">
        ${strip}
        <div class="day-panel">
          <h3>☀️ 第 ${dayNo} 天 · 存活 ${aliveCount} 人 · ${dayStage === 'nom' ? '🗳 提名阶段' : '💬 公聊私聊'}</h3>
          ${stageBox}
          ${talkBody}
          ${stChatsBox}
          ${voting}
          ${hist}
          <div class="st-detail-actions"><button class="btn small primary" id="day-end">🌙 天黑 → 第 ${nightNo + 1} 夜</button></div>
        </div>
      </div>`)
      detail.replaceChildren(box)
      wireSelPDetail()
      box.querySelectorAll('[data-stage]').forEach((b) => {
        b.onclick = () => act(() => stApi('/api/day/stage', { method: 'POST', body: JSON.stringify({ stage: b.dataset.stage }) }))
      })
      // 私聊总览操作
      const recallBtn = box.querySelector('#chat-recall')
      if (recallBtn) recallBtn.onclick = () => act(() => stApi('/api/chat-st/recall', { method: 'POST' }))
      box.querySelectorAll('[data-st-inv]').forEach((b) => {
        b.onclick = () => {
          if (b.dataset.stInvY === '1') stChatOpen = Number(b.dataset.stInv) // 接受后直接展开消息流
          act(() => stApi(`/api/chat-st/${b.dataset.stInv}/invite`, { method: 'POST', body: JSON.stringify({ accept: b.dataset.stInvY === '1' }) }))
        }
      })
      box.querySelectorAll('[data-st-view]').forEach((b) => {
        b.onclick = () => { stChatOpen = stChatOpen === Number(b.dataset.stView) ? null : Number(b.dataset.stView); paint(view) }
      })
      box.querySelectorAll('[data-st-close]').forEach((b) => {
        b.onclick = () => act(() => stApi(`/api/chat-st/${b.dataset.stClose}/close`, { method: 'POST' }))
      })
      const stSend = box.querySelector('#st-chat-send')
      if (stSend) stSend.onclick = () => {
        const v = (box.querySelector('#st-chat-text').value || '').trim()
        if (!v) return
        act(() => stApi(`/api/chat-st/${stChatOpen}/send`, { method: 'POST', body: JSON.stringify({ text: v }) }))
      }
      const go = document.getElementById('nom-go')
      if (go) go.onclick = () => {
        const parseTarget = (v) => (/^t\d+$/.test(v) ? v : Number(v)) // 旅行者 id 保持字符串
        const from = parseTarget(document.getElementById('nom-from').value)
        const to = parseTarget(document.getElementById('nom-to').value)
        act(() => stApi('/api/nomination', { method: 'POST', body: JSON.stringify({ nominator: from, nominee: to }) }))
      }
      const pass = document.getElementById('nom-pass')
      if (pass) armClick(pass, nomIsTraveler ? '🏴 确认流放?' : '✅ 确认通过?',
        () => act(() => stApi('/api/nomination/resolve', { method: 'POST', body: JSON.stringify({ passed: true }) })))
      const skip = document.getElementById('nom-skip')
      if (skip) skip.onclick = () => act(() => stApi('/api/nomination/resolve', { method: 'POST', body: JSON.stringify({ passed: false }) }))
      const end = document.getElementById('day-end')
      if (end) armClick(end, `确认天黑?${endPreview}`,
        () => act(() => stApi('/api/day/end', { method: 'POST' })))
    }

    // ---- 环形座位 ----
    document.getElementById('circle').appendChild(seatCircle(seats, {
      freeLabel: '空',
      draftBadge: (s) => {
        // 手动模式显示草稿;开局后已入座玩家的真实角色也显示(玩家坐下徽章不能消失);
        // 空座上的预发身份同样显示。徽章按阵营配色
        const badgeOf = (rid) => ({ name: (FAKE_ICON[rid] || '') + roleById[rid].name, team: roleById[rid].team })
        if (manual && draft[s.seat] && roleById[draft[s.seat]]) return badgeOf(draft[s.seat])
        if (s.player && s.player.role && roleById[s.player.role.id]) return badgeOf(s.player.role.id)
        if (seat_roles && seat_roles[s.seat] && roleById[seat_roles[s.seat]]) {
          return badgeOf(seat_roles[s.seat])
        }
        return null
      },
      voted: (s) => status === 'playing' && phase === 'day' && current && s.player && current.votes.includes(s.seat),
      bubble: (s) => {
        const c = (stChats || []).find((x) => !x.closed && (x.members || []).some((m) => String(m.who) === String(s.seat)))
        return c ? c.color : null
      },
      centerBubble: () => {
        const c = (stChats || []).find((x) => !x.closed && (x.members || []).some((m) => String(m.who) === 'st'))
        return c ? c.color : null
      },
      centerHanged: phase === 'night' && nightNo === 1,
      markers: (s) => [...(s.markers || []), ...(fortunetellerRed === s.seat ? ['redherring'] : [])], // 🐟 占卜师宿敌(仅说书人可见)
      clickSeat: (s) => {
        // 投票进行中:点座位 = 记录举手/放下(空座有预发角色同样可投,按座位级生死)
        if (status === 'playing' && phase === 'day' && current && (s.player || s.assigned_role)) {
          act(() => stApi('/api/nomination/vote', { method: 'POST', body: JSON.stringify({ seat: s.seat }) }))
          return
        }
        selected = s.seat
        paint(view)
      },
    }))

    // ---- 旅行者横栏:添加 / 指派角色 / 举手投票 / 生死 / 流放 ----
    const tadd = document.getElementById('t-add')
    if (tadd) tadd.onclick = async () => {
      const input = document.getElementById('t-add-name')
      const name = (input.value || '').trim()
      if (!name) {
        err.textContent = '请填写旅行者名字'
        err.style.display = ''
        return
      }
      try {
        const st = await stApi('/api/traveler/add', { method: 'POST', body: JSON.stringify({ name }) })
        travelerPick = st.travelers[st.travelers.length - 1].id // 添加后直接打开指派面板
        travelerAlign = 'good'
        paint(st)
      } catch (e) {
        err.textContent = e.message
        err.style.display = ''
      }
    }
    document.querySelectorAll('[data-t-assign]').forEach((b) => {
      b.onclick = () => {
        travelerPick = b.dataset.tAssign
        const cur = tList.find((x) => x.id === travelerPick)
        travelerAlign = (cur && cur.align) || 'good'
        paint(view)
      }
    })
    document.querySelectorAll('[data-t-vote]').forEach((b) => {
      b.onclick = () => act(() => stApi('/api/nomination/vote', { method: 'POST', body: JSON.stringify({ seat: b.dataset.tVote }) }))
    })
    document.querySelectorAll('[data-t-alive]').forEach((b) => {
      b.onclick = () => act(() => stApi('/api/traveler/alive', { method: 'POST', body: JSON.stringify({ id: b.dataset.tAlive }) }))
    })
    document.querySelectorAll('[data-t-exile]').forEach((b) => {
      const t = tList.find((x) => x.id === b.dataset.tExile)
      if (!t) return
      const exiling = !t.exiled
      const doExile = () => act(() => stApi('/api/traveler/exile', { method: 'POST', body: JSON.stringify({ id: b.dataset.tExile, exiled: exiling }) }))
      if (exiling) armClick(b, `🏴 确认流放 ${t.name}?`, doExile) // 流放=离场,两步确认;撤销一步即可
      else b.onclick = doExile
    })

    // ---- 旅行者指派面板:先选阵营(官方:绝大多数给善良),再点角色 ----
    function renderTravelerPicker(detail) {
      const t = tList.find((x) => x.id === travelerPick)
      if (!t) { travelerPick = null; paint(view); return }
      const rec = travelerRec && travelerRec.length ? travelerRec : (traveler_roles || []).map((r) => r.id)
      const recSet = new Set(rec)
      const others = (traveler_roles || []).filter((r) => !recSet.has(r.id))
      const alignOf = t.role_id ? t.align : travelerAlign
      const roleChip = (r) => `<button class="chip team-traveler" data-t-role="${r.id}" title="${esc(r.ability)}">${esc(r.name)}</button>`
      detail.replaceChildren(h(`<div class="st-detail">
        <h3>🎒 指派旅行者 · ${esc(t.name)}</h3>
        <p class="hint">阵营只有说书人和旅行者本人知道(角色公开);邪恶旅行者会得知恶魔是谁</p>
        <div class="st-fake"><span class="hint">阵营:</span>
          <button class="chip ${alignOf === 'good' ? 'on' : ''}" data-t-align="good">善良</button>
          <button class="chip ${alignOf === 'evil' ? 'on' : ''}" data-t-align="evil">邪恶</button>
        </div>
        ${rec.length ? `<div class="st-fake"><span class="hint">本板推荐:</span>${rec.map((rid) => tById[rid] ? roleChip(tById[rid]) : '').join('')}</div>` : ''}
        ${others.length ? `<div class="st-fake"><span class="hint">其他旅行者:</span>${others.map(roleChip).join('')}</div>` : ''}
        <p class="hint">${t.role ? `当前:${esc(t.role.name)}(${t.align === 'evil' ? '邪恶' : '善良'}) — 点角色可改派` : '点角色完成指派'}</p>
      </div>`))
      detail.querySelectorAll('[data-t-align]').forEach((b) => {
        b.onclick = () => {
          const align = b.dataset.tAlign
          if (t.role_id) {
            act(() => stApi('/api/traveler/assign', { method: 'POST', body: JSON.stringify({ id: t.id, role: t.role_id, align }) }))
          } else {
            travelerAlign = align
            paint(view)
          }
        }
      })
      detail.querySelectorAll('[data-t-role]').forEach((b) => {
        b.onclick = () => act(() => stApi('/api/traveler/assign', {
          method: 'POST',
          body: JSON.stringify({ id: t.id, role: b.dataset.tRole, align: alignOf }),
        }))
      })
    }

    // ---- 选中玩家详情 ----
    const detail = document.getElementById('detail')
    // 认知覆盖:疯子/酒鬼座位由说书人标记「玩家看到哪个假角色」,真实身份只有说书人可见。
    // 疯子额外由说书人选定:以为谁是爪牙(不一定是真的)+ 3 个伪装(不一定是恶魔的真伪装)
    const bluffTeamList = script === 'trouble-brewing' ? ['townsfolk'] : ['townsfolk', 'outsider']
    // 假伪装候选:好角色即可,允许与在场角色相同(假身份不计算配板)
    const fakeBluffPool = roles.filter((r) => bluffTeamList.includes(r.team))
    const fakeRow = (slot) => {
      const real = slot.player ? slot.player.role : slot.assigned_role
      if (!real || !fakePools || !fakePools[real.id]) return ''
      const cur = slot.fake_role
      // 假身份做成框点选(再点已选中的框=清除);可与已发角色重复
      const head = `<div class="st-fake"><span class="hint">${FAKE_LABEL[real.id] || '认知覆盖'} 看到:</span>
        <button class="chip ghost ${!cur ? 'on' : ''}" data-fake-chip="">真实身份(${esc(real.name)})</button>
        ${roles.filter((r) => fakePools[real.id].includes(r.team)).map((r) =>
          `<button class="chip team-${r.team} ${cur && cur.id === r.id ? 'on' : ''}" data-fake-chip="${r.id}" title="${esc(r.ability)}">${esc(r.name)}</button>`).join('')}</div>`
      if (real.id !== 'lunatic') return head
      const seatKey = String(slot.seat)
      const mins = (lunaticMinions && lunaticMinions[seatKey]) || []
      const lbs = ((lunaticBluffs && lunaticBluffs[seatKey]) || []).map((r) => r.id)
      const minRow = `<div class="st-fake"><span class="hint">以为爪牙是(点选):</span>${Array.from({ length: count }, (_, i) => i + 1)
        .filter((s) => s !== slot.seat)
        .map((s) => `<button class="chip ${mins.includes(s) ? 'on' : ''}" data-min-chip="${s}">${s}号</button>`).join('')}</div>`
      const selOf = (i) => `<select data-lb="${i}"><option value="">-</option>
        ${(lbs[i] && !fakeBluffPool.some((r) => r.id === lbs[i])
          ? [{ id: lbs[i], name: roleById[lbs[i]] ? roleById[lbs[i]].name : lbs[i] }] : [])
          .concat(fakeBluffPool).map((r) =>
            `<option value="${r.id}" ${lbs[i] === r.id ? 'selected' : ''}>${esc(r.name)}</option>`).join('')}</select>`
      const bluffRow = `<div class="st-fake"><span class="hint">疯子伪装(3):</span>${selOf(0)}${selOf(1)}${selOf(2)}</div>`
      return head + minRow + bluffRow
    }
    if (manual) {
      renderManualPicker(detail, selSeat)
    } else if (travelerPick) {
      renderTravelerPicker(detail)
    } else if (status === 'playing' && phase === 'night') {
      renderNightPanel(detail) // 夜晚流程助手(顶部含选中玩家条)
    } else if (status === 'playing' && phase === 'day') {
      renderDayPanel(detail) // 白天提名投票(顶部含选中玩家条)
    } else if (selP) {
      detail.replaceChildren(h(selPDetailHtml(selSeat, selP)))
      wireSelPDetail()
    } else if (selSeat && selSeat.assigned_role) {
      detail.replaceChildren(h(emptySeatStrip(selSeat)))
      wireSelPDetail()  // 状态栏(标记/转变)对空座同样可用
    } else {
      detail.replaceChildren(h('<p class="hint">点击环形座位查看/操作玩家</p>'))
    }
    const fakeChips = document.querySelectorAll('[data-fake-chip]')
    if (fakeChips.length) {
      const real = selSeat.player ? selSeat.player.role : selSeat.assigned_role
      // 疯子详情:改动任何一项都提交(未填全的字段不带上 → 后端保留已存值)
      const submitFake = (role) => {
        const body = { seat: selSeat.seat, role }
        if (role && real && real.id === 'lunatic') {
          const minVals = [...document.querySelectorAll('[data-min-chip].on')]
            .map((c) => Number(c.dataset.minChip))
          const lbVals = [...document.querySelectorAll('[data-lb]')].map((s) => s.value)
          if (minVals.length) body.minions = minVals
          if (lbVals.length === 3 && lbVals.every((v) => v !== '')) body.bluffs = lbVals
        }
        act(() => stApi('/api/fake', { method: 'POST', body: JSON.stringify(body) }))
      }
      fakeChips.forEach((c) => {
        c.onclick = () => {
          const curRole = selSeat.fake_role && selSeat.fake_role.id
          const next = c.dataset.fakeChip || null
          // 再点已选中的框 = 清除认知覆盖
          submitFake(curRole && curRole === next ? null : next)
        }
      })
      document.querySelectorAll('[data-min-chip]').forEach((c) => {
        c.onclick = () => {
          c.classList.toggle('on')
          const curRole = selSeat.fake_role && selSeat.fake_role.id
          if (curRole) submitFake(curRole)
        }
      })
      document.querySelectorAll('[data-lb]').forEach((s) => {
        s.onchange = () => {
          const curRole = selSeat.fake_role && selSeat.fake_role.id
          if (curRole) submitFake(curRole)
        }
      })
    }

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
      if (willClear && !configArm) { // 两步确认(页内提示,不弹系统框):3 秒内再点才执行
        configArm = true
        err.textContent = '再次确认:修改配置会清空所有座位和角色分配'
        err.style.display = ''
        setTimeout(() => { configArm = false }, 3000)
        return
      }
      configArm = false
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
        // 进入手动模式时载入已预发的身份与已定的认知覆盖,便于微调;退出则清空草稿
        draft = manual && seat_roles
          ? Object.fromEntries(Object.entries(seat_roles).map(([s, r]) => [Number(s), r]))
          : {}
        draftFakes = {}
        draftLunMinions = {}
        draftLunBluffs = {}
        if (manual) {
          seats.forEach((s) => { if (s.fake_role) draftFakes[s.seat] = s.fake_role.id })
          Object.entries(lunaticMinions || {}).forEach(([s, ms]) => { draftLunMinions[Number(s)] = ms })
          Object.entries(lunaticBluffs || {}).forEach(([s, bs]) => { draftLunBluffs[Number(s)] = bs.map((r) => r.id) })
        }
        paint(view)
      }
    }
    document.getElementById('dec').onclick = () => doConfig(script, count - 1)
    document.getElementById('inc').onclick = () => doConfig(script, count + 1)
    document.querySelectorAll('.sentinel-chip').forEach((b) => {
      b.onclick = () => act(() => stApi('/api/sentinel', { method: 'POST', body: JSON.stringify({ value: Number(b.dataset.sentinel) }) }))
    })
    document.querySelectorAll('.fabled-chip').forEach((b) => {
      b.onclick = () => act(() => stApi('/api/fabled', { method: 'POST', body: JSON.stringify({ id: b.dataset.fabled, on: !(fabled || []).some((x) => x.id === b.dataset.fabled) }) }))
    })
    const roomInput = document.getElementById('room-code')
    const applyRoom = () => {
      const v = roomInput.value.trim()
      if (!/^\d{4}$/.test(v)) {
        err.textContent = '房间号需为 4 位数字'
        err.style.display = ''
        roomInput.value = roomCode
        return
      }
      act(() => stApi('/api/room', { method: 'POST', body: JSON.stringify({ code: v }) }))
    }
    roomInput.onchange = applyRoom
    document.getElementById('room-random').onclick = () => {
      roomInput.value = String(Math.floor(Math.random() * 10000)).padStart(4, '0')
      applyRoom()
    }

    // ---- 分配 / 重置 / 读档 ----
    document.getElementById('assign-btn').onclick = () => act(() => stApi('/api/assign', { method: 'POST' }))
    const startBtn = document.getElementById('start-btn')
    if (startBtn) startBtn.onclick = () => act(() => stApi('/api/start', { method: 'POST' }))
    document.getElementById('reset-btn').onclick = null
    armClick(document.getElementById('reset-btn'), '⚠ 确认重置本局?', () => act(() => stApi('/api/reset', { method: 'POST' })))
    document.getElementById('load-btn').onclick = null
    armClick(document.getElementById('load-btn'), '⚠ 确认读档?', () => act(() => stApi('/api/load', { method: 'POST' })))
    document.querySelectorAll('[data-st-archive]').forEach((b) => {
      b.onclick = () => { stArchiveOpen = stArchiveOpen === Number(b.dataset.stArchive) ? null : Number(b.dataset.stArchive); paint(view) }
    })
    // 💬 说书人私聊徽章:点击直达对应群
    const stChatBadgeBtn = document.getElementById('st-chat-badge')
    if (stChatBadgeBtn) stChatBadgeBtn.onclick = () => {
      const target = (stChats || []).find((c) => !c.closed && (c.invites || []).some((i) => i.who === 'st'))
        || (stChats || []).find((c) => !c.closed && (c.members || []).some((m) => m.who === 'st'))
      stChatOpen = target ? target.id : null
      selected = null
      paint(view)
    }

    // ---- 结算:宣布游戏结束 + 判定获胜方(可撤销),终局后进入独立复盘视图 ----
    const endBtn = document.getElementById('end-btn')
    if (endBtn) endBtn.onclick = () => { endPick = true; paint(view) }
    const endCancel = document.getElementById('end-cancel')
    if (endCancel) endCancel.onclick = () => { endPick = false; paint(view) }
    document.querySelectorAll('[data-end]').forEach((b) => {
      b.onclick = () => { endPick = false; act(() => stApi('/api/end', { method: 'POST', body: JSON.stringify({ winner: b.dataset.end }) })) }
    })
    const endUndo = document.getElementById('end-undo')
    if (endUndo) endUndo.onclick = () => act(() => stApi('/api/end', { method: 'POST', body: JSON.stringify({ winner: null }) }))
    const endReview = document.getElementById('end-review')
    if (endReview) endReview.onclick = () => { reviewMode = true; paint(view) }
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
