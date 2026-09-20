import { api } from './api.js'

const playerPath = (id, suffix) => `/api/player/${encodeURIComponent(id)}${suffix}`

const post = (path, body) => api(path, {
  method: 'POST',
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
})

export function createPlayerService(playerId) {
  const withId = (suffix) => playerPath(playerId, suffix)
  const chat = (cid, suffix) => `/api/chat/${encodeURIComponent(cid)}${suffix}?player_id=${encodeURIComponent(playerId)}`

  return {
    sit: (seat) => post(withId('/sit'), { seat }),
    setWish: (wish) => post(withId('/wish'), { wish }),
    joinTraveler: () => post(withId('/traveler')),
    nominate: (nominee) => post(withId('/nominate'), { nominee }),
    vote: () => post(withId('/vote')),
    submitNightAction: (payload) => post(withId('/night-action'), payload),
    createChat: (invitees) => post(`/api/chat/create?player_id=${encodeURIComponent(playerId)}`, { invitees }),
    respondInvite: (cid, accept) => post(chat(cid, '/invite'), { accept }),
    requestChat: (cid) => post(chat(cid, '/request')),
    inviteMore: (cid, invitees) => post(chat(cid, '/invite-more'), { invitees }),
    approveRequest: (cid, who, approve) => post(chat(cid, '/approve'), { who, approve }),
    sendChat: (cid, text) => post(chat(cid, '/send'), { text }),
    leaveChat: (cid) => post(chat(cid, '/leave')),
    closeChat: (cid) => post(chat(cid, '/close')),
  }
}
