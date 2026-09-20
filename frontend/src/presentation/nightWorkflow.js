export const NIGHT_STATUS_LABELS = {
  current: '当前',
  upcoming: '待执行',
  completed: '已完成',
  skipped: '已跳过',
  undone: '已撤销',
}

export const NIGHT_TRIGGER_LABELS = {
  special: '流程步骤',
  traveler: '旅行者行动',
  normal: '常规行动',
  'first-night': '首夜行动',
  'start-knowing': '立即获得信息',
  death: '死亡触发',
  created: '本夜新建角色',
}

export const OUTCOME_LABELS = {
  secret_death: '确认死亡（天亮公开）',
  no_death: '不死亡',
  delayed: '延后裁定',
  redirected: '转移到其他目标',
  transformation: '发生角色变化',
  choice_only: '仅记录选择',
}

export const EFFECT_STATE_LABELS = {
  active: '生效中',
  suspended: '暂时失效',
  ended: '已结束',
}

export const EFFECT_TRIGGER_LABELS = {
  source_inactive: '来源暂时失去能力',
  source_active: '来源能力恢复',
  source_lost: '来源永久失去能力',
  source_death: '来源死亡',
  next_choice: '下一次选择',
  dusk: '黄昏到期',
  dawn: '天亮',
  game_end: '游戏结束',
}

export const NIGHT_ERROR_LABELS = {
  stale_id: '这条记录已经变化，请根据最新魔典重新操作',
  stale_step: '夜晚顺序已经变化，请重新选择步骤',
  empty_queue: '本夜没有可执行步骤',
  at_start: '已经是本夜第一步',
  invalid_direction: '夜晚导航方向无效',
  missing_step: '尚未指定夜晚步骤',
  expired_force_token: '强制继续确认已过期，请重新检查遗漏项',
  invalid_target_count: '选择的人数不符合该角色要求',
  duplicate_targets: '不能重复选择同一个座位',
  invalid_target: '目标座位无效',
  empty_target: '目标座位还没有配置角色',
  self_target_forbidden: '该角色不能选择自己',
  target_must_be_alive: '该行动只能选择存活玩家',
  missing_targets: '还没有选择目标',
  arbitrary_death_unavailable: '本夜没有可用的麻脸巫婆任意死亡',
  outcome_conflict: '这项结果已经裁定',
  undo_conflict: '无法完整撤销依赖链，状态未发生变化',
  invalid_command: '当前操作不符合夜晚规则',
}

export function nightStatusLabel(status) {
  return NIGHT_STATUS_LABELS[status] || status || '未知状态'
}

export function nightTriggerLabel(trigger) {
  return NIGHT_TRIGGER_LABELS[trigger] || trigger || '夜晚行动'
}

export function outcomeLabel(resolution) {
  return OUTCOME_LABELS[resolution] || resolution || '待裁定'
}

export function effectStateLabel(state) {
  return EFFECT_STATE_LABELS[state] || state || '未知状态'
}

export function effectTransitionLabel(transition) {
  if (!transition) return ''
  const trigger = EFFECT_TRIGGER_LABELS[transition.trigger] || transition.reason
  return `${effectStateLabel(transition.from)} → ${effectStateLabel(transition.to)}${trigger ? ` · ${trigger}` : ''}`
}

export function nightErrorMessage(error) {
  if (!error) return ''
  return NIGHT_ERROR_LABELS[error.code] || error.message || '夜晚操作失败'
}

export function nightStepSummary(step) {
  if (!step) return '本夜没有待处理任务'
  const actor = step.actor_seat ? `${step.actor_seat} 号` : '全体流程'
  return `${actor} · ${step.name || step.character_id} · ${nightTriggerLabel(step.trigger)}`
}

export function seatContextLabel(seat) {
  if (!seat) return ''
  return seat.claimed_by ? `${seat.seat} 号` : `${seat.seat} 号 · 线下/未领取`
}
