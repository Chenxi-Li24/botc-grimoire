import { beforeEach, expect, it, vi } from 'vitest'
import { createStorytellerService } from '../src/services/storyteller.js'
import { api } from '../src/services/api.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
  api.mockResolvedValue({ status: 'lobby' })
})

it('sends authenticated configuration and assignment payloads', async () => {
  const service = createStorytellerService('secret')
  await service.configure('trouble-brewing', 7)
  await service.assignManual({ assignments: [], bluffs: [], fakes: [] })

  expect(api).toHaveBeenNthCalledWith(1, '/api/config', {
    method: 'POST',
    headers: { 'X-Storyteller-Password': 'secret' },
    body: JSON.stringify({ script: 'trouble-brewing', player_count: 7 }),
  })
  expect(api).toHaveBeenNthCalledWith(2, '/api/assign/manual', {
    method: 'POST',
    headers: { 'X-Storyteller-Password': 'secret' },
    body: JSON.stringify({ assignments: [], bluffs: [], fakes: [] }),
  })
})

it('uses every existing lobby endpoint without inventing request bodies', async () => {
  const service = createStorytellerService('secret')
  await service.assignRandom()
  await service.setSentinel(-1)
  await service.toggleFabled('angel', true)
  await service.start()

  expect(api.mock.calls.map(([path]) => path)).toEqual([
    '/api/assign', '/api/sentinel', '/api/fabled', '/api/start',
  ])
  expect(api.mock.calls[0][1]).not.toHaveProperty('body')
  expect(JSON.parse(api.mock.calls[1][1].body)).toEqual({ value: -1 })
  expect(JSON.parse(api.mock.calls[2][1].body)).toEqual({ id: 'angel', on: true })
  expect(api.mock.calls[3][1]).not.toHaveProperty('body')
})

it('preserves backend errors for the initiating panel', async () => {
  api.mockRejectedValueOnce(new Error('本局已开始，不能修改配置'))
  const service = createStorytellerService('secret')
  await expect(service.configure('trouble-brewing', 6))
    .rejects.toThrow('本局已开始，不能修改配置')
})

it('maps every daytime command and preserves traveler participant ids', async () => {
  const service = createStorytellerService('secret')
  await service.setDayStage('nom')
  await service.startNomination(2, 't1')
  await service.toggleVote('t1')
  await service.resolveNomination(true)
  await service.endDay()

  expect(api.mock.calls.map(([path]) => path)).toEqual([
    '/api/day/stage',
    '/api/nomination',
    '/api/nomination/vote',
    '/api/nomination/resolve',
    '/api/day/end',
  ])
  expect(JSON.parse(api.mock.calls[0][1].body)).toEqual({ stage: 'nom' })
  expect(JSON.parse(api.mock.calls[1][1].body)).toEqual({ nominator: 2, nominee: 't1' })
  expect(JSON.parse(api.mock.calls[2][1].body)).toEqual({ seat: 't1' })
  expect(JSON.parse(api.mock.calls[3][1].body)).toEqual({ passed: true })
  expect(api.mock.calls[4][1]).not.toHaveProperty('body')
})

it('sends traveler administration with the existing REST payloads', async () => {
  const service = createStorytellerService('secret')
  await service.addTraveler('迟到玩家')
  await service.assignTraveler('t1', 'apprentice', 'evil')
  await service.toggleTravelerAlive('t1')
  await service.setTravelerExile('t1', true)

  expect(api.mock.calls.map(([path]) => path)).toEqual([
    '/api/traveler/add', '/api/traveler/assign', '/api/traveler/alive', '/api/traveler/exile',
  ])
  expect(api.mock.calls.map(([, options]) => JSON.parse(options.body))).toEqual([
    { name: '迟到玩家' }, { id: 't1', role: 'apprentice', align: 'evil' },
    { id: 't1' }, { id: 't1', exiled: true },
  ])
})

it('sends storyteller chat commands to the existing REST endpoints', async () => {
  const service = createStorytellerService('secret')
  await service.answerChatInvite(2, true)
  await service.sendStorytellerChat(2, '晚上见')
  await service.leaveStorytellerChat(2)
  await service.closeStorytellerChat(2)
  await service.recallChats()

  expect(api.mock.calls.map(([path]) => path)).toEqual([
    '/api/chat-st/2/invite', '/api/chat-st/2/send', '/api/chat-st/2/leave',
    '/api/chat-st/2/close', '/api/chat-st/recall',
  ])
  expect(JSON.parse(api.mock.calls[0][1].body)).toEqual({ accept: true })
  expect(JSON.parse(api.mock.calls[1][1].body)).toEqual({ text: '晚上见' })
  expect(api.mock.calls.slice(2).every(([, options]) => !('body' in options))).toBe(true)
})

it('keeps seat and session administration payloads compatible', async () => {
  const service = createStorytellerService('secret')
  await service.setRoom('1024')
  await service.setFake({ seat: 5, role: 'chef' })
  await service.setMarker({ seat: 5, marker: 'poisoned', on: true })
  await service.setRedHerring(5)
  await service.toggleSeatAlive(5)
  await service.togglePlayerAlive('p1')
  await service.removePlayer('p1')
  await service.loadSave()
  await service.resetGame()

  expect(api.mock.calls.map(([path]) => path)).toEqual([
    '/api/room', '/api/fake', '/api/marker', '/api/fortuneteller/red',
    '/api/seat/5/alive', '/api/player/p1/alive', '/api/player/p1/remove', '/api/load', '/api/reset',
  ])
  expect(api.mock.calls.slice(0, 4).map(([, options]) => JSON.parse(options.body))).toEqual([
    { code: '1024' }, { seat: 5, role: 'chef' },
    { seat: 5, marker: 'poisoned', on: true }, { seat: 5 },
  ])
  expect(api.mock.calls.slice(4).every(([, options]) => !('body' in options))).toBe(true)
})

it('announces winner and marks review replies using the existing contract', async () => {
  const service = createStorytellerService('secret')
  await service.setWinner('good')
  await service.setWinner(null)
  await service.markReview(1, 2, true)

  expect(api.mock.calls.map(([path]) => path)).toEqual(['/api/end', '/api/end', '/api/review/mark'])
  expect(api.mock.calls.map(([, options]) => JSON.parse(options.body))).toEqual([
    { winner: 'good' }, { winner: null }, { seat: 1, night: 2, wrong: true },
  ])
})
