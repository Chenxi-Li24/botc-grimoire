export const TEAM_ORDER = [
  ['townsfolk', '镇民'],
  ['outsider', '外来者'],
  ['minion', '爪牙'],
  ['demon', '恶魔'],
]

const TEAM_INDEX = Object.fromEntries(TEAM_ORDER.map(([team], index) => [team, index]))

export function roleMap(view) {
  return Object.fromEntries((view.roles || []).map((role) => [role.id, role]))
}

export function expectedComposition(view, assignments, godfatherAdjustment = 1) {
  const expected = [...(view.composition || [0, 0, 0, 0])]
  const pickedRoles = [...new Set(Object.values(assignments))]

  for (const roleId of pickedRoles) {
    let adjustment = view.adjust_roles?.[roleId]
    if (roleId === 'godfather' && adjustment) {
      adjustment = [-godfatherAdjustment, godfatherAdjustment, 0, 0]
    }
    adjustment?.forEach((delta, index) => { expected[index] += delta })
  }

  if (view.sentinel === 1 || view.sentinel === -1) {
    expected[1] += view.sentinel
    expected[0] -= view.sentinel
  }
  if (expected[1] < 0) {
    expected[0] += expected[1]
    expected[1] = 0
  }
  return expected
}

export function selectedComposition(view, assignments) {
  const roles = roleMap(view)
  const counts = [0, 0, 0, 0]
  Object.values(assignments).forEach((roleId) => {
    const index = TEAM_INDEX[roles[roleId]?.team]
    if (index !== undefined) counts[index] += 1
  })
  return counts
}

export function eligibleBluffRoles(view, assignments) {
  const allowedTeams = view.script === 'trouble-brewing'
    ? ['townsfolk']
    : ['townsfolk', 'outsider']
  const assigned = new Set(Object.values(assignments))
  return (view.roles || []).filter((role) => allowedTeams.includes(role.team) && !assigned.has(role.id))
}

export function eligibleFakeRoles(view, realRoleId) {
  const teams = view.fake_pools?.[realRoleId] || []
  return (view.roles || []).filter((role) => teams.includes(role.team))
}

export function manualAssignmentSummary(view, draft) {
  const roleIds = Object.values(draft.assignments)
  const duplicates = roleIds.filter((roleId, index) => roleIds.indexOf(roleId) !== index)
  const selected = selectedComposition(view, draft.assignments)
  const expected = expectedComposition(view, draft.assignments, draft.godfatherAdjustment)
  const hardErrors = []
  const warnings = []

  if (Object.keys(draft.assignments).length !== view.player_count) {
    hardErrors.push(`还需分配 ${view.player_count - Object.keys(draft.assignments).length} 个座位`)
  }
  if (duplicates.length) hardErrors.push('角色不能重复')
  if (selected[3] !== 1) hardErrors.push('必须且只能有 1 名恶魔')
  if (selected[2] < 1) hardErrors.push('至少需要 1 名爪牙')
  if (selected.some((count, index) => count !== expected[index])) {
    warnings.push('当前阵营配比与参考配比不同，请说书人确认')
  }

  const bluffPool = new Set(eligibleBluffRoles(view, draft.assignments).map((role) => role.id))
  if (draft.bluffs.length !== 3 || new Set(draft.bluffs).size !== draft.bluffs.length) {
    hardErrors.push('恶魔伪装需要 3 个不重复角色')
  } else if (draft.bluffs.some((roleId) => !bluffPool.has(roleId))) {
    hardErrors.push('恶魔伪装必须是未在场的可选好角色')
  }

  Object.entries(draft.assignments).forEach(([seat, realRoleId]) => {
    const fakePool = new Set(eligibleFakeRoles(view, realRoleId).map((role) => role.id))
    if (!fakePool.size) return
    if (!fakePool.has(draft.fakes[seat])) {
      hardErrors.push(`${seat}号的认知覆盖尚未完成`)
    }
    if (realRoleId === 'lunatic') {
      const minions = draft.lunaticMinions[seat] || []
      const lunaticBluffs = draft.lunaticBluffs[seat] || []
      if (!minions.length || minions.some((target) => target === Number(seat))) {
        hardErrors.push(`${seat}号疯子至少需要一个其他座位作为假爪牙`)
      }
      const allowed = new Set((view.roles || [])
        .filter((role) => (view.script === 'trouble-brewing' ? role.team === 'townsfolk' : ['townsfolk', 'outsider'].includes(role.team)))
        .map((role) => role.id))
      if (lunaticBluffs.length !== 3 || new Set(lunaticBluffs).size !== 3
          || lunaticBluffs.some((roleId) => !allowed.has(roleId))) {
        hardErrors.push(`${seat}号疯子需要 3 个不重复的好人伪装`)
      }
    }
  })

  return {
    assignedCount: Object.keys(draft.assignments).length,
    selected,
    expected,
    hardErrors: [...new Set(hardErrors)],
    warnings,
    valid: hardErrors.length === 0,
  }
}

export function manualAssignmentPayload(draft) {
  const assignments = Object.entries(draft.assignments)
    .map(([seat, role]) => ({ seat: Number(seat), role }))
    .sort((left, right) => left.seat - right.seat)
  const fakes = Object.entries(draft.fakes)
    .filter(([seat, role]) => draft.assignments[seat] && role)
    .map(([seat, role]) => ({
      seat: Number(seat),
      role,
      ...(draft.assignments[seat] === 'lunatic'
        ? {
            minions: [...(draft.lunaticMinions[seat] || [])],
            bluffs: [...(draft.lunaticBluffs[seat] || [])],
          }
        : {}),
    }))
    .sort((left, right) => left.seat - right.seat)

  return { assignments, bluffs: [...draft.bluffs], fakes }
}
