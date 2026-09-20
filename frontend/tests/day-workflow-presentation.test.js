import { expect, it } from 'vitest'
import {
  canVote,
  currentVoteSummary,
  dayParticipants,
  executionStanding,
} from '../src/presentation/dayWorkflow.js'
import { makeStorytellerDayView } from './fixtures/storytellerView.js'

it('keeps seat ids numeric and traveler ids textual without mutating the view', () => {
  const view = makeStorytellerDayView()
  const frozen = structuredClone(view)

  expect(dayParticipants(view).map(({ id }) => id)).toEqual([1, 2, 3, 4, 5, 6, 't1', 't2'])
  expect(view).toEqual(frozen)
})

it('computes the active threshold and traveler exile threshold', () => {
  const view = makeStorytellerDayView()
  expect(currentVoteSummary(view)).toEqual({ votes: 2, quorum: 3, passes: false })

  const travelerVote = makeStorytellerDayView({
    current: { nominator: 1, nominee: 't1', votes: [1, 2, 3, 4] },
  })
  expect(currentVoteSummary(travelerVote)).toEqual({ votes: 4, quorum: 4, passes: true })
})

it('allows living and unused dead votes but rejects spent dead votes', () => {
  const view = makeStorytellerDayView()
  expect(canVote(dayParticipants(view).find(({ id }) => id === 1), view)).toBe(true)
  expect(canVote(dayParticipants(view).find(({ id }) => id === 6), view)).toBe(true)
  expect(canVote(dayParticipants(view).find(({ id }) => id === 't2'), view)).toBe(false)
})

it('reports a unique execution leader, ties, and no pending execution', () => {
  const passed = [
    { day: 1, nominee: 2, votes: [1, 2, 3], passed: true, executed: false },
    { day: 1, nominee: 3, votes: [1, 2], passed: true, executed: false },
    { day: 1, nominee: 't1', votes: [1, 2, 3, 4], passed: true, executed: true },
    { day: 2, nominee: 4, votes: [1, 2, 3, 4], passed: true, executed: false },
  ]
  expect(executionStanding(makeStorytellerDayView({ nominations: passed }))).toEqual({
    state: 'leader', nominee: 2, votes: 3,
  })

  expect(executionStanding(makeStorytellerDayView({
    nominations: [...passed, { day: 1, nominee: 5, votes: [1, 2, 3], passed: true, executed: false }],
  }))).toEqual({ state: 'tie', nominees: [2, 5], votes: 3 })

  expect(executionStanding(makeStorytellerDayView({ nominations: [] }))).toEqual({ state: 'none' })
})
