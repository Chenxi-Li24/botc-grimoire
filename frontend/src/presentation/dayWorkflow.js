import { participantLabel } from './player.js'

function seatRole(slot) {
  return slot?.player?.role || slot?.assigned_role || null
}

function seatAlive(slot) {
  if (slot?.player) return slot.player.alive !== false
  return slot?.alive !== false
}

function seatDeadVoteLeft(slot) {
  if (seatAlive(slot)) return true
  if (slot?.dead_vote_left === true) return true
  return slot?.player?.dead_vote_used === false
}

export function dayParticipants(view) {
  const seats = (view?.seats || [])
    .filter((slot) => seatRole(slot))
    .map((slot) => ({
      id: slot.seat,
      type: 'seat',
      label: participantLabel(slot.seat, view.seats, view.travelers),
      alive: seatAlive(slot),
      deadVoteLeft: seatDeadVoteLeft(slot),
      exiled: false,
    }))

  const travelers = (view?.travelers || []).map((traveler) => ({
    id: traveler.id,
    type: 'traveler',
    label: participantLabel(traveler.id, view.seats, view.travelers),
    alive: traveler.alive !== false,
    deadVoteLeft: traveler.dead_vote_used !== true,
    exiled: traveler.exiled === true,
  }))

  return [...seats, ...travelers]
}

export function canVote(participant, view) {
  const resolved = typeof participant === 'object'
    ? participant
    : dayParticipants(view).find(({ id }) => id === participant)
  if (!resolved || resolved.exiled) return false
  return resolved.alive || resolved.deadVoteLeft
}

export function currentVoteSummary(view) {
  const votes = view?.current?.votes?.length || 0
  const quorum = typeof view?.current?.nominee === 'string'
    ? (view?.exile_quorum || 0)
    : (view?.quorum || 0)
  return { votes, quorum, passes: votes >= quorum }
}

export function executionStanding(view) {
  const candidates = (view?.nominations || []).filter((nomination) => (
    nomination.day === view?.day_no
    && nomination.passed
    && typeof nomination.nominee === 'number'
  ))
  if (!candidates.length) return { state: 'none' }

  const votes = Math.max(...candidates.map((nomination) => nomination.votes?.length || 0))
  const leaders = candidates.filter((nomination) => (nomination.votes?.length || 0) === votes)
  if (leaders.length === 1) {
    return { state: 'leader', nominee: leaders[0].nominee, votes }
  }
  return { state: 'tie', nominees: leaders.map(({ nominee }) => nominee), votes }
}
