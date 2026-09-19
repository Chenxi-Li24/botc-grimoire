export function getPhaseLabel(view) {
  if (view.status !== 'playing') return '等待开局'
  if (view.phase === 'night') return `第 ${view.night_no} 夜`
  if (view.phase === 'day') {
    const stage = { talk: '公聊', nom: '提名', vote: '投票' }[view.day_stage] || '白天'
    return `第 ${view.day_no} 天 · ${stage}`
  }
  return '游戏进行中'
}

export function getScriptName(view) {
  return view.scripts?.find((script) => script.id === view.script)?.name || view.script || '未选择板子'
}
