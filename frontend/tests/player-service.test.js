import { beforeEach, expect, it, vi } from 'vitest'
import { api } from '../src/services/api.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
  api.mockResolvedValue({ ok: true })
})

it('maps player commands without coercing traveler ids', async () => {
  const { createPlayerService } = await import('../src/services/player.js')
  const service = createPlayerService('p/1')

  await service.sit(2)
  await service.setWish('chef')
  await service.joinTraveler()
  await service.nominate('t2')
  await service.vote()
  await service.submitNightAction({ step_id: 'n1', targets: [3] })

  expect(api.mock.calls).toEqual([
    ['/api/player/p%2F1/sit', { method: 'POST', body: JSON.stringify({ seat: 2 }) }],
    ['/api/player/p%2F1/wish', { method: 'POST', body: JSON.stringify({ wish: 'chef' }) }],
    ['/api/player/p%2F1/traveler', { method: 'POST' }],
    ['/api/player/p%2F1/nominate', { method: 'POST', body: JSON.stringify({ nominee: 't2' }) }],
    ['/api/player/p%2F1/vote', { method: 'POST' }],
    ['/api/player/p%2F1/night-action', {
      method: 'POST',
      body: JSON.stringify({ step_id: 'n1', targets: [3] }),
    }],
  ])
})

it('maps every private chat command with encoded player identity', async () => {
  const { createPlayerService } = await import('../src/services/player.js')
  const service = createPlayerService('p/1')

  await service.createChat([2, 't3'])
  await service.respondInvite('chat 1', true)
  await service.requestChat('chat 1')
  await service.inviteMore('chat 1', ['t3'])
  await service.approveRequest('chat 1', 't3', false)
  await service.sendChat('chat 1', '你好')
  await service.leaveChat('chat 1')
  await service.closeChat('chat 1')

  expect(api.mock.calls).toEqual([
    ['/api/chat/create?player_id=p%2F1', { method: 'POST', body: JSON.stringify({ invitees: [2, 't3'] }) }],
    ['/api/chat/chat%201/invite?player_id=p%2F1', { method: 'POST', body: JSON.stringify({ accept: true }) }],
    ['/api/chat/chat%201/request?player_id=p%2F1', { method: 'POST' }],
    ['/api/chat/chat%201/invite-more?player_id=p%2F1', { method: 'POST', body: JSON.stringify({ invitees: ['t3'] }) }],
    ['/api/chat/chat%201/approve?player_id=p%2F1', { method: 'POST', body: JSON.stringify({ who: 't3', approve: false }) }],
    ['/api/chat/chat%201/send?player_id=p%2F1', { method: 'POST', body: JSON.stringify({ text: '你好' }) }],
    ['/api/chat/chat%201/leave?player_id=p%2F1', { method: 'POST' }],
    ['/api/chat/chat%201/close?player_id=p%2F1', { method: 'POST' }],
  ])
})
