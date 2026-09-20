const TEAM_LABELS = {
  townsfolk: '镇民',
  outsider: '外来者',
  minion: '爪牙',
  demon: '恶魔',
  traveler: '旅行者',
  good: '善良',
  evil: '邪恶',
}

const DAY_STAGE_LABELS = {
  talk: '公聊',
  nom: '提名',
  vote: '投票',
}

export function participantLabel(id, seats = [], travelers = []) {
  if (typeof id === 'number') {
    const seat = seats.find((item) => item.seat === id)
    const name = seat?.player?.name || seat?.name || seat?.assigned_role?.name
    return name ? `${id}号 ${name}` : `${id}号`
  }

  const traveler = travelers.find((item) => item.id === id)
  return traveler ? `🎒 ${traveler.name}` : String(id ?? '')
}

export function teamLabel(team) {
  return TEAM_LABELS[team] || team || '未知'
}

export function phaseLabel(view) {
  if (view?.status !== 'playing') return '等待开局'
  if (view.phase === 'night') return `第 ${view.night_no} 夜`
  if (view.phase === 'day') {
    const stage = DAY_STAGE_LABELS[view.day_stage]
    return `第 ${view.day_no} 天${stage ? ` · ${stage}` : ''}`
  }
  return '游戏进行中'
}

function groupByDay(items, sortItems) {
  const groups = new Map()
  for (const item of items || []) {
    const day = item.day
    if (!groups.has(day)) groups.set(day, [])
    groups.get(day).push(item)
  }

  return [...groups.entries()]
    .sort(([left], [right]) => Number(left) - Number(right))
    .map(([day, groupedItems]) => ({
      day,
      items: sortItems ? [...groupedItems].sort(sortItems) : [...groupedItems],
    }))
}

export function groupDeaths(deaths) {
  return groupByDay(deaths, (left, right) => String(left.seat).localeCompare(String(right.seat)))
}

export function groupNominations(nominations) {
  return groupByDay(nominations)
}
