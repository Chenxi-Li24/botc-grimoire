import { mount } from '@vue/test-utils'
import { ref, shallowRef } from 'vue'
import { beforeEach, expect, it, vi } from 'vitest'
import PlayerPage from '../src/pages/PlayerPage.vue'
import { usePlayerView } from '../src/composables/usePlayerView.js'
import {
  makeDayPlayerView,
  makeFinishedPlayerView,
  makeLobbyPlayerView,
  makeNightPlayerView,
  makePlayerView,
} from './fixtures/playerView.js'

vi.mock('../src/composables/usePlayerView.js', () => ({ usePlayerView: vi.fn() }))

let currentView

beforeEach(() => {
  currentView = shallowRef(null)
  sessionStorage.clear()
  usePlayerView.mockReturnValue({ view: currentView, connectionStatus: ref('connected') })
})

it('welcomes a newly joined player before the board and reveals their private role with a flip', async () => {
  currentView.value = makeLobbyPlayerView()
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })
  expect(wrapper.get('[data-player-welcome]').text()).toContain('鸦木布拉夫镇')
  await wrapper.get('[data-welcome-enter]').trigger('click')
  expect(wrapper.find('[data-player-welcome]').exists()).toBe(false)
  currentView.value = makePlayerView()
  await wrapper.vm.$nextTick()
  expect(wrapper.get('[data-identity-reveal]').text()).not.toContain('厨师')
  await wrapper.get('[data-identity-flip]').trigger('click')
  expect(wrapper.get('[data-identity-reveal]').text()).toContain('厨师')
  expect(wrapper.get('[data-identity-reveal]').text()).toContain('你得知相邻邪恶玩家对数')
  await wrapper.get('[data-identity-enter]').trigger('click')
  expect(wrapper.find('[data-identity-reveal]').exists()).toBe(false)
  expect(wrapper.get('.public-board').exists()).toBe(true)
  wrapper.unmount()
  const revisit = mount(PlayerPage, { props: { playerId: 'p1' } })
  expect(revisit.find('[data-player-welcome]').exists()).toBe(false)
  expect(revisit.find('[data-identity-reveal]').exists()).toBe(false)
  revisit.unmount()
})

it('shows the storyteller clocktower scene only when the first night ends', async () => {
  sessionStorage.setItem('botc_welcome_p1', '1')
  sessionStorage.setItem('botc_role_seen_p1', '1')
  currentView.value = makePlayerView({ phase: 'night', night_no: 1 })
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })
  expect(wrapper.find('[data-opening-intro]').exists()).toBe(false)
  currentView.value = makeDayPlayerView()
  await wrapper.vm.$nextTick()
  expect(wrapper.get('[data-opening-intro]').text()).toContain('说书人被吊死在钟楼之上')
  await wrapper.get('[data-opening-skip]').trigger('click')
  expect(wrapper.find('[data-opening-intro]').exists()).toBe(false)
  wrapper.unmount()
  const revisit = mount(PlayerPage, { props: { playerId: 'p1' } })
  expect(revisit.find('[data-opening-intro]').exists()).toBe(false)
  revisit.unmount()
})

it('moves keyboard focus into each private ceremony step', async () => {
  currentView.value = makePlayerView()
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' }, attachTo: document.body })
  await wrapper.vm.$nextTick()
  expect(document.activeElement).toBe(wrapper.get('[data-welcome-enter]').element)
  await wrapper.get('[data-welcome-enter]').trigger('click')
  await wrapper.vm.$nextTick()
  expect(document.activeElement).toBe(wrapper.get('[data-identity-flip]').element)
  await wrapper.get('[data-identity-flip]').trigger('click')
  await wrapper.vm.$nextTick()
  expect(document.activeElement).toBe(wrapper.get('[data-identity-enter]').element)
  wrapper.unmount()
})

it('still plays an unseen first-dawn scene when reconnecting directly on day one', async () => {
  sessionStorage.setItem('botc_welcome_p1', '1')
  sessionStorage.setItem('botc_role_seen_p1', '1')
  currentView.value = makeDayPlayerView()
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })
  await wrapper.vm.$nextTick()
  expect(wrapper.get('[data-opening-intro]').text()).toContain('说书人被吊死在钟楼之上')
  wrapper.unmount()
})

it('waits for the role ceremony before starting the first-dawn scene timer', async () => {
  vi.useFakeTimers()
  try {
    currentView.value = makeDayPlayerView()
    const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })
    expect(wrapper.find('[data-player-welcome]').exists()).toBe(true)
    expect(wrapper.find('[data-opening-intro]').exists()).toBe(false)
    vi.advanceTimersByTime(3500)
    await wrapper.get('[data-welcome-enter]').trigger('click')
    await wrapper.get('[data-identity-flip]').trigger('click')
    await wrapper.get('[data-identity-enter]').trigger('click')
    expect(wrapper.get('[data-opening-intro]').text()).toContain('说书人被吊死在钟楼之上')
    wrapper.unmount()
  } finally {
    vi.useRealTimers()
  }
})

it('plays the first lights-out scene after identity reveal, never behind it', async () => {
  currentView.value = makeLobbyPlayerView()
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })
  await wrapper.get('[data-welcome-enter]').trigger('click')
  currentView.value = makePlayerView({ phase: 'night', night_no: 1 })
  await wrapper.vm.$nextTick()
  expect(wrapper.get('[data-identity-reveal]').exists()).toBe(true)
  expect(wrapper.find('[data-scene-transition]').exists()).toBe(false)
  await wrapper.get('[data-identity-flip]').trigger('click')
  await wrapper.get('[data-identity-enter]').trigger('click')
  expect(wrapper.get('[data-scene-transition="night"]').text()).toContain('灯光熄灭')
  wrapper.unmount()
})

const states = {
  lobby: () => makeLobbyPlayerView(),
  night: () => makeNightPlayerView(),
  day: () => makeDayPlayerView(),
  finished: () => makeFinishedPlayerView(),
}

it.each(Object.entries(states))('renders %s entirely in Vue without a legacy link', async (state, createView) => {
  currentView.value = createView()
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })

  expect(wrapper.find('[data-player-page]').exists()).toBe(true)
  expect(wrapper.find('a[href^="/legacy"]').exists()).toBe(false)
  if (state === 'finished') expect(wrapper.find('[data-player-result]').exists()).toBe(true)
})

it('keeps the loading state inside the Vue player route', () => {
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })
  expect(wrapper.get('[data-player-page]').text()).toContain('正在连接房间')
})

it('switches the player shell phase when the server moves from night to day', async () => {
  currentView.value = makeNightPlayerView()
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })
  expect(wrapper.get('.player-shell').attributes('data-phase')).toBe('night')

  currentView.value = makeDayPlayerView()
  await wrapper.vm.$nextTick()
  expect(wrapper.get('.player-shell').attributes('data-phase')).toBe('day')
})

it('passes the nomination stage through to the player chat pause state', () => {
  currentView.value = makeDayPlayerView({
    chat: {
      who: '1', my_chat: null, invites: [], chats_public: [],
    },
  })
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })

  expect(wrapper.text()).toContain('提名阶段暂停私聊')
  expect(wrapper.get('[data-chat-new]').attributes('disabled')).toBeDefined()
})

it('offers account binding to guests and private history only to account players', async () => {
  currentView.value = makeLobbyPlayerView()
  const guest = mount(PlayerPage, { props: { playerId: 'p1' } })
  expect(guest.find('[data-open-account]').exists()).toBe(true)
  expect(guest.find('[data-open-history]').exists()).toBe(false)
  await guest.get('[data-open-account]').trigger('click')
  expect(guest.emitted('account')).toEqual([[]])
  guest.unmount()
  const member = mount(PlayerPage, { props: { playerId: 'p1', account: 'Alice' } })
  expect(member.find('[data-open-history]').exists()).toBe(true)
  expect(member.find('[data-open-account]').exists()).toBe(false)
  member.unmount()
})
