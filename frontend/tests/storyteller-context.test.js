import { mount } from '@vue/test-utils'
import { nextTick, ref, shallowRef } from 'vue'
import { beforeEach, expect, it, vi } from 'vitest'
import ContextPanel from '../src/components/storyteller/ContextPanel.vue'
import StorytellerLiveView from '../src/components/storyteller/StorytellerLiveView.vue'
import { lobbyView } from './fixtures/storytellerView.js'

let liveView

vi.mock('../src/composables/useStorytellerView.js', () => ({
  useStorytellerView: vi.fn(() => ({
    view: liveView,
    connectionStatus: ref('connected'),
  })),
}))

beforeEach(() => {
  liveView = shallowRef(lobbyView)
})

it('shows join information when no player is selected', () => {
  const wrapper = mount(ContextPanel, { props: { view: lobbyView, selectedSeat: null } })
  expect(wrapper.text()).toContain('2468')
  expect(wrapper.text()).toContain('已入座 2/6')
  expect(wrapper.get('img').attributes('src')).toBe('/api/qr')
})

it('prioritizes selected-player details and can clear the selection', async () => {
  const view = {
    ...lobbyView,
    seats: lobbyView.seats.map((seat) => seat.seat === 1
      ? { ...seat, markers: ['poisoned'], player: { ...seat.player, alive: false } }
      : seat),
  }
  const wrapper = mount(ContextPanel, { props: { view, selectedSeat: 1 } })

  expect(wrapper.text()).toContain('阿青')
  expect(wrapper.text()).toContain('洗衣妇')
  expect(wrapper.text()).toContain('镇民')
  expect(wrapper.text()).toContain('死亡')
  expect(wrapper.text()).toContain('中毒')
  expect(wrapper.find('img').exists()).toBe(false)
  await wrapper.get('[data-clear-selection]').trigger('click')
  expect(wrapper.emitted('clear-selection')).toEqual([[]])
})

it('drops stale selected-player details after a server update removes that player', async () => {
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('[data-seat="1"]').trigger('click')
  expect(wrapper.text()).toContain('洗衣妇')

  liveView.value = {
    ...lobbyView,
    seats: lobbyView.seats.map((seat) => seat.seat === 1 ? { ...seat, player: null } : seat),
  }
  await nextTick()

  expect(wrapper.text()).toContain('玩家加入')
  expect(wrapper.text()).not.toContain('洗衣妇')
})
