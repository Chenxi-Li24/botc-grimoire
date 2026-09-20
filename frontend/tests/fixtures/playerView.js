export function makePlayerView(overrides = {}) {
  return {
    status: 'playing',
    script: '暗流涌动',
    player_count: 5,
    composition: [3, 0, 1, 1],
    sentinel: false,
    fabled: [],
    phase: 'night',
    night_no: 1,
    day_no: 0,
    day_stage: null,
    room_code: '2468',
    me: {
      id: 'p1',
      name: '阿青',
      seat: 1,
      alive: true,
      role: { id: 'chef', name: '厨师', en: 'Chef', team: 'townsfolk', ability: '你得知相邻邪恶玩家对数。' },
    },
    seats: [
      { seat: 1, player: { id: 'p1', name: '阿青', seat: 1, alive: true }, is_me: true },
      { seat: 2, player: { id: 'p2', name: '小白', seat: 2, alive: true } },
      { seat: 3, player: null },
      { seat: 4, player: null },
      { seat: 5, player: null },
    ],
    travelers_public: [],
    nominations: [],
    current: null,
    ...overrides,
  }
}

export function makeLobbyPlayerView(overrides = {}) {
  return makePlayerView({
    status: 'lobby',
    phase: null,
    night_no: 0,
    me: { id: 'p1', name: '阿青', seat: null, alive: true },
    seats: [
      { seat: 1, player: { id: 'p2', name: '小白', seat: 1, alive: true } },
      { seat: 2, player: null },
      { seat: 3, player: null },
      { seat: 4, player: null },
      { seat: 5, player: null },
    ],
    ...overrides,
  })
}
