// Only imported by the storyteller page. Audio files are locally bundled CC0 works.
export const BGM_TRACKS = {
  night: { label: '夜晚', src: '/bgm/night.ogg' },
  day: { label: '白天', src: '/bgm/day.mp3' },
  vote: { label: '投票', src: '/bgm/vote.ogg' },
  'private-chat': { label: '私聊', src: '/bgm/private-chat.ogg' },
  'public-chat': { label: '公聊', src: '/bgm/public-chat.mp3' },
  execution: { label: '处决', src: '/bgm/execution.ogg' },
  replay: { label: '复盘', src: '/bgm/replay.ogg' },
  victory: { label: '获胜', src: '/bgm/victory.wav' },
}

export function sceneForView(view, reviewOpen = false) {
  if (view?.winner) return reviewOpen ? 'replay' : 'victory'
  if (view?.phase === 'night') return 'night'
  if (view?.phase === 'day') {
    if (view.day_stage === 'nom') {
      if (view.current) return 'vote'
      const last = view.nominations?.at(-1)
      if (last?.day === view.day_no && last.executed) return 'execution'
      return 'vote'
    }
    if (view.chats?.some((chat) => !chat.closed)) return 'private-chat'
    return 'public-chat'
  }
  return 'day'
}
