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
  }
}
