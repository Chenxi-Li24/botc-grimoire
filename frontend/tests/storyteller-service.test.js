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
