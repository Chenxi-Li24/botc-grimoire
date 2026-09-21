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
} from './fixtures/playerView.js'

vi.mock('../src/composables/usePlayerView.js', () => ({ usePlayerView: vi.fn() }))

let currentView

beforeEach(() => {
  currentView = shallowRef(null)
  usePlayerView.mockReturnValue({ view: currentView, connectionStatus: ref('connected') })
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
