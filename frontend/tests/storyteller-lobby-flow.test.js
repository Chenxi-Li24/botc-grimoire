import { mount } from '@vue/test-utils'
import { computed, nextTick, ref, shallowRef } from 'vue'
import { beforeEach, expect, it, vi } from 'vitest'
import StorytellerLiveView from '../src/components/storyteller/StorytellerLiveView.vue'
import { lobbyView } from './fixtures/storytellerView.js'

let liveView
let connectionStatus
const service = {
  configure: vi.fn(), assignRandom: vi.fn(), assignManual: vi.fn(),
  setSentinel: vi.fn(), toggleFabled: vi.fn(), start: vi.fn(),
}

vi.mock('../src/composables/useStorytellerView.js', () => ({
  useStorytellerView: vi.fn(() => ({ view: liveView, connectionStatus })),
}))
vi.mock('../src/services/storyteller.js', () => ({
  createStorytellerService: vi.fn(() => service),
}))

beforeEach(() => {
  vi.clearAllMocks()
  liveView = shallowRef(lobbyView)
  connectionStatus = ref('connected')
  Object.values(service).forEach((method) => method.mockResolvedValue({ status: 'lobby' }))
})

const buttonWithText = (wrapper, text) => wrapper.findAll('button').find((button) => button.text().includes(text))

it('opens manual mode, previews a role on an empty seat, and cancels without a request', async () => {
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await buttonWithText(wrapper, '手动发身份').trigger('click')
  await wrapper.get('[data-seat="3"]').trigger('click')
  await buttonWithText(wrapper, '图书管理员').trigger('click')

  expect(wrapper.get('[data-seat="3"]').text()).toContain('图书管理员')
  expect(wrapper.get('[data-seat="3"]').text()).toContain('草稿')
  await buttonWithText(wrapper, '放弃草稿').trigger('click')
  expect(service.assignManual).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain('玩家加入')
})

it('keeps the draft visible but disables confirmation while reconnecting', async () => {
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await buttonWithText(wrapper, '手动发身份').trigger('click')
  connectionStatus.value = 'reconnecting'
  await nextTick()
  expect(buttonWithText(wrapper, '确认发身份').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).toContain('手动发身份')
})

it('submits a complete manual draft and exits manual mode after acknowledgement', async () => {
  const extraRoles = [
    { id: 'bluff-a', name: '伪装甲', team: 'townsfolk' },
    { id: 'bluff-b', name: '伪装乙', team: 'townsfolk' },
    { id: 'bluff-c', name: '伪装丙', team: 'townsfolk' },
  ]
  const assignedView = {
    ...lobbyView,
    roles: [...lobbyView.roles, ...extraRoles],
    seat_roles: {
      1: 'washerwoman', 2: 'imp', 3: 'librarian',
      4: 'drunk', 5: 'poisoner', 6: 'investigator',
    },
    seats: lobbyView.seats.map((seat) => seat.seat === 4
      ? { ...seat, assigned_role: lobbyView.roles.find((role) => role.id === 'drunk'),
          fake_role: lobbyView.roles.find((role) => role.id === 'washerwoman') }
      : seat),
    bluffs: extraRoles,
  }
  liveView.value = assignedView
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await buttonWithText(wrapper, '手动发身份').trigger('click')
  await buttonWithText(wrapper, '确认发身份').trigger('click')

  expect(service.assignManual).toHaveBeenCalledWith(expect.objectContaining({
    assignments: expect.arrayContaining([{ seat: 2, role: 'imp' }]),
    bluffs: ['bluff-a', 'bluff-b', 'bluff-c'],
    fakes: [{ seat: 4, role: 'washerwoman' }],
  }))
  await vi.waitFor(() => expect(wrapper.text()).toContain('玩家加入'))
})

it('does not overwrite a faster server projection when a command resolves later', async () => {
  let finish
  service.setSentinel.mockImplementation(() => new Promise((resolve) => { finish = resolve }))
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('summary').trigger('click')
  await buttonWithText(wrapper, '+1 外来者').trigger('click')
  liveView.value = { ...lobbyView, sentinel: 1 }
  await nextTick()
  finish({ ...lobbyView, sentinel: 0 })
  await nextTick()
  expect(wrapper.findAll('button').find((button) => button.text() === '+1 外来者').attributes('aria-pressed')).toBe('true')
})

it('removes lobby mutations after the server enters play', async () => {
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  liveView.value = { ...lobbyView, status: 'playing', phase: 'night', night_no: 1 }
  await nextTick()
  expect(wrapper.text()).toContain('大厅配置已锁定')
  expect(wrapper.text()).not.toContain('随机分配角色')
})
