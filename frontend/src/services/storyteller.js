import { api } from './api.js'

export function createStorytellerService(password) {
  const command = (path, body) => api(path, {
    method: 'POST',
    headers: { 'X-Storyteller-Password': password },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })

  return {
    configure: (script, playerCount) => command('/api/config', {
      script,
      player_count: playerCount,
    }),
    assignRandom: () => command('/api/assign'),
    assignManual: (draft) => command('/api/assign/manual', draft),
    setSentinel: (value) => command('/api/sentinel', { value }),
    toggleFabled: (id, on) => command('/api/fabled', { id, on }),
    start: () => command('/api/start'),
    navigate: (payload) => command('/api/night/step', payload),
    selectNightTargets: (payload) => command('/api/night/select', payload),
    resolveOutcome: (payload) => command('/api/night/outcome', payload),
    deliverInformation: (payload) => command('/api/night/information', payload),
    applyNightEffect: (payload) => command('/api/night/effect', payload),
    confirmPitHag: (payload) => command('/api/night/pit-hag', payload),
    undoNightEvent: (payload) => command('/api/night/undo', payload),
    setDayStage: (stage) => command('/api/day/stage', { stage }),
    startNomination: (nominator, nominee) => command('/api/nomination', { nominator, nominee }),
    toggleVote: (seat) => command('/api/nomination/vote', { seat }),
    resolveNomination: (passed) => command('/api/nomination/resolve', { passed }),
    endDay: () => command('/api/day/end'),
    addTraveler: (name) => command('/api/traveler/add', { name }),
    assignTraveler: (id, role, align) => command('/api/traveler/assign', { id, role, align }),
    setTravelerExile: (id, exiled) => command('/api/traveler/exile', { id, exiled }),
    toggleTravelerAlive: (id) => command('/api/traveler/alive', { id }),
  }
}
