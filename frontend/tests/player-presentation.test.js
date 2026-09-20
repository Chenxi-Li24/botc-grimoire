import { expect, it } from 'vitest'

it('labels seats and traveler ids without numeric coercion', async () => {
  const { participantLabel } = await import('../src/presentation/player.js')
  const seats = [
    { seat: 1, player: { name: '阿青' } },
    { seat: 2, assigned_role: { name: '厨师' } },
  ]
  const travelers = [{ id: 't2', name: '阿旅' }]

  expect(participantLabel(1, seats, travelers)).toBe('1号 阿青')
  expect(participantLabel(2, seats, travelers)).toBe('2号 厨师')
  expect(participantLabel('t2', seats, travelers)).toBe('🎒 阿旅')
  expect(participantLabel('2', seats, travelers)).toBe('2')
})

it('formats public team and phase labels', async () => {
  const { phaseLabel, teamLabel } = await import('../src/presentation/player.js')

  expect(teamLabel('townsfolk')).toBe('镇民')
  expect(teamLabel('evil')).toBe('邪恶')
  expect(teamLabel('custom')).toBe('custom')
  expect(phaseLabel({ status: 'lobby' })).toBe('等待开局')
  expect(phaseLabel({ status: 'playing', phase: 'night', night_no: 2 })).toBe('第 2 夜')
  expect(phaseLabel({ status: 'playing', phase: 'day', day_no: 3, day_stage: 'nom' })).toBe('第 3 天 · 提名')
})

it('groups deaths and nominations by day without mutating projections', async () => {
  const { groupDeaths, groupNominations } = await import('../src/presentation/player.js')
  const deaths = [
    { seat: 't2', day: 2, name: '阿旅' },
    { seat: 1, day: 1, name: '阿青' },
    { seat: 3, day: 2, name: '小白' },
  ]
  const nominations = [
    { day: 2, nominator: 't2', nominee: 3 },
    { day: 1, nominator: 1, nominee: 2 },
  ]
  const deathsBefore = structuredClone(deaths)
  const nominationsBefore = structuredClone(nominations)

  expect(groupDeaths(deaths)).toEqual([
    { day: 1, items: [deaths[1]] },
    { day: 2, items: [deaths[2], deaths[0]] },
  ])
  expect(groupNominations(nominations)).toEqual([
    { day: 1, items: [nominations[1]] },
    { day: 2, items: [nominations[0]] },
  ])
  expect(deaths).toEqual(deathsBefore)
  expect(nominations).toEqual(nominationsBefore)
})
