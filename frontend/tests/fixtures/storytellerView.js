const player = (id, name, seat, role) => ({
  id, name, seat, alive: true, role, markers: [],
})

export const lobbyView = {
  status: 'lobby',
  script: 'trouble-brewing',
  player_count: 6,
  scripts: [
    { id: 'trouble-brewing', name: '暗流涌动', en: 'Trouble Brewing', min: 5, max: 15 },
  ],
  seats: [
    { seat: 1, player: player('p1', '阿青', 1, { id: 'washerwoman', name: '洗衣妇', team: 'townsfolk' }), dead_vote_left: true },
    { seat: 2, player: player('p2', '小白', 2, { id: 'imp', name: '小恶魔', team: 'demon' }), dead_vote_left: true },
    { seat: 3, player: null, dead_vote_left: true },
    { seat: 4, player: null, dead_vote_left: true },
    { seat: 5, player: null, dead_vote_left: true },
    { seat: 6, player: null, dead_vote_left: true },
  ],
  roles: [
    { id: 'washerwoman', name: '洗衣妇', team: 'townsfolk', ability: '得知两名玩家之一是某镇民。' },
    { id: 'librarian', name: '图书管理员', team: 'townsfolk', ability: '得知两名玩家之一是某外来者。' },
    { id: 'investigator', name: '调查员', team: 'townsfolk', ability: '得知两名玩家之一是某爪牙。' },
    { id: 'drunk', name: '酒鬼', team: 'outsider', ability: '不知道自己是酒鬼。' },
    { id: 'lunatic', name: '疯子', team: 'outsider', ability: '以为自己是恶魔。' },
    { id: 'poisoner', name: '投毒者', team: 'minion', ability: '每夜选择一名玩家中毒。' },
    { id: 'godfather', name: '教父', team: 'minion', ability: '调整外来者数量。' },
    { id: 'imp', name: '小恶魔', team: 'demon', ability: '每夜选择一名玩家死亡。' },
  ],
  composition: [3, 1, 1, 1],
  adjust_roles: { godfather: [-1, 1, 0, 0] },
  seat_roles: {},
  phase: null,
  night_no: 0,
  day_no: 0,
  day_stage: 'talk',
  night: null,
  nominations: [],
  current: null,
  alive_count: 2,
  quorum: 1,
  can_start: false,
  bluffs: [],
  demon_seats: [],
  minion_seats: [],
  sentinel: 0,
  saved_at: null,
  fake_pools: { drunk: ['townsfolk'], lunatic: ['demon'] },
  lunatic_seats: [],
  lunatic_minions: {},
  lunatic_bluffs: {},
  fakes_pending: false,
  room_code: '2468',
  travelers: [],
  traveler_roles: [],
  traveler_recommended: [],
  total_players: 2,
  exile_quorum: 1,
  players: [],
  night_kills: [],
  fortuneteller_red: null,
  night_choices: {},
  night_actions: {},
  winner: null,
  fabled: [],
  fabled_pool: [
    { id: 'angel', name: '天使', ability: '保护新玩家。' },
    { id: 'djinn', name: '灯神', ability: '说明特殊规则。' },
  ],
  chats: [],
}

export const activeNomination = (votes = []) => ({
  nominator: 1,
  nominee: 2,
  votes,
})

export function makeStorytellerDayView(overrides = {}) {
  const role = (id, name, team = 'townsfolk') => ({ id, name, team })
  const seated = (id, name, seat, assignedRole, alive = true, deadVoteUsed = false) => ({
    id,
    name,
    seat,
    alive,
    dead_vote_used: deadVoteUsed,
    role: assignedRole,
    markers: [],
  })

  const view = {
    ...structuredClone(lobbyView),
    status: 'playing',
    phase: 'day',
    night_no: 1,
    day_no: 1,
    day_stage: 'nom',
    seats: [
      { seat: 1, player: seated('p1', '阿青', 1, role('chef', '厨师')), dead_vote_left: true },
      { seat: 2, player: seated('p2', '小白', 2, role('empath', '共情者')), dead_vote_left: true },
      { seat: 3, player: seated('p3', '阿紫', 3, role('monk', '僧侣')), dead_vote_left: true },
      { seat: 4, player: seated('p4', '阿金', 4, role('soldier', '士兵')), dead_vote_left: true },
      { seat: 5, player: null, assigned_role: role('mayor', '镇长'), alive: true, dead_vote_left: true },
      { seat: 6, player: seated('p6', '阿灰', 6, role('recluse', '隐士', 'outsider'), false), dead_vote_left: true },
    ],
    travelers: [
      { id: 't1', name: '旅人甲', alive: true, exiled: false, dead_vote_used: false, alignment: 'good' },
      { id: 't2', name: '旅人乙', alive: false, exiled: true, dead_vote_used: true, alignment: 'evil' },
    ],
    alive_count: 5,
    total_players: 8,
    quorum: 3,
    exile_quorum: 4,
    current: activeNomination([1, 2]),
    nominations: [],
    deaths: [],
  }

  return { ...view, ...overrides }
}
