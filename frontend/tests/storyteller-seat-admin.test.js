import { mount } from '@vue/test-utils'
import { ref, shallowRef } from 'vue'
import { expect, it, vi } from 'vitest'
import ContextPanel from '../src/components/storyteller/ContextPanel.vue'
import StorytellerLiveView from '../src/components/storyteller/StorytellerLiveView.vue'
import { makeStorytellerDayView } from './fixtures/storytellerView.js'

const view = makeStorytellerDayView({
  roles: [
    { id: 'chef', name: '厨师', team: 'townsfolk' },
    { id: 'drunk', name: '酒鬼', team: 'outsider' },
    { id: 'imp', name: '小恶魔', team: 'demon' },
    { id: 'mayor', name: '镇长', team: 'townsfolk' },
    { id: 'investigator', name: '调查员', team: 'townsfolk' },
  ],
})
const liveService = {
  setRoom: vi.fn().mockResolvedValue({ status: 'playing' }),
  toggleSeatAlive: vi.fn().mockResolvedValue({ status: 'playing' }),
}
vi.mock('../src/composables/useStorytellerView.js', () => ({
  useStorytellerView: () => ({ view: shallowRef(view), connectionStatus: ref('connected') }),
}))
vi.mock('../src/services/storyteller.js', () => ({
  createStorytellerService: () => liveService,
}))

it('allows an unclaimed assigned seat to change life and markers', async () => {
  const wrapper = mount(ContextPanel, { props: { view, selectedSeat: 5, connected: true } })
  expect(wrapper.text()).toContain('线下/未领取')
  expect(wrapper.text()).toContain('镇长')
  await wrapper.get('[data-seat-alive]').trigger('click')
  expect(wrapper.emitted('toggle-seat-alive')).toEqual([[5]])
  await wrapper.get('[data-seat-marker="poisoned"]').trigger('click')
  expect(wrapper.emitted('set-marker')).toEqual([[{ seat: 5, marker: 'poisoned', on: true }]])
})

it('supports role, team, and madness markers with typed payloads', async () => {
  const wrapper = mount(ContextPanel, { props: { view, selectedSeat: 1, connected: true } })
  await wrapper.get('[data-seat-marker="role-change"]').trigger('click')
  await wrapper.get('[data-seat-role="imp"]').trigger('click')
  await wrapper.get('[data-seat-marker="team-change"]').trigger('click')
  await wrapper.get('[data-seat-team="evil"]').trigger('click')
  await wrapper.get('[data-seat-marker="mad"]').trigger('click')
  await wrapper.get('[data-seat-mad="chef"]').trigger('click')
  expect(wrapper.emitted('set-marker')).toEqual([
    [{ seat: 1, marker: 'role-change', on: true, role: 'imp' }],
    [{ seat: 1, marker: 'team-change', on: true, team: 'evil' }],
    [{ seat: 1, marker: 'mad', on: true, about: 'chef' }],
  ])
})

it('changes a claimed player life and requires confirmation before removing account', async () => {
  const wrapper = mount(ContextPanel, { props: { view, selectedSeat: 1, connected: true } })
  await wrapper.get('[data-seat-alive]').trigger('click')
  expect(wrapper.emitted('toggle-player-alive')).toEqual([['p1']])
  await wrapper.get('[data-seat-remove]').trigger('click')
  expect(wrapper.emitted('remove-player')).toBeUndefined()
  await wrapper.get('[data-seat-remove]').trigger('click')
  expect(wrapper.emitted('remove-player')).toEqual([['p1']])
})

it('sets a drunk fake identity and the fortune teller red herring', async () => {
  const drunkView = {
    ...view,
    seats: view.seats.map((slot) => slot.seat === 5
      ? { ...slot, assigned_role: { id: 'drunk', name: '酒鬼', team: 'outsider' } }
      : slot),
  }
  const wrapper = mount(ContextPanel, { props: { view: drunkView, selectedSeat: 5, connected: true } })
  await wrapper.get('[data-seat-fake="chef"]').trigger('click')
  expect(wrapper.emitted('set-seat-fake')).toEqual([[{ seat: 5, role: 'chef' }]])
  await wrapper.get('[data-seat-red]').trigger('click')
  expect(wrapper.emitted('set-red-herring')).toEqual([[5]])
})

it('blocks seat writes while disconnected', () => {
  const wrapper = mount(ContextPanel, { props: { view, selectedSeat: 5, connected: false } })
  expect(wrapper.get('[data-seat-alive]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-seat-marker="poisoned"]').attributes('disabled')).toBeDefined()
})

it('keeps seat administration accessible during night without replacing the night workflow by default', () => {
  const wrapper = mount(ContextPanel, {
    props: { view: { ...view, phase: 'night' }, selectedSeat: 5, adminTab: 'seats', night: {}, connected: true },
  })
  expect(wrapper.text()).toContain('线下/未领取')
  expect(wrapper.find('[data-seat-alive]').exists()).toBe(true)
})

it('shows when a sourced status began and how it ended', () => {
  const historyView = {
    ...view,
    seats: view.seats.map((slot) => slot.seat === 5 ? {
      ...slot,
      effect_history: [{
        id: 'e1', type: 'poisoned', source_seat: 2, source_character: 'poisoner',
        started_at: '2026-09-21T19:00:00Z', expected_end: 'next_dusk', state: 'ended',
        transitions: [
          { at: '2026-09-21T19:00:00Z', to: 'active', reason: 'applied' },
          { at: '2026-09-21T20:00:00Z', to: 'ended', reason: 'reached_dusk' },
        ],
      }],
    } : slot),
  }
  const wrapper = mount(ContextPanel, { props: { view: historyView, selectedSeat: 5 } })
  expect(wrapper.text()).toContain('2026-09-21T19:00:00Z')
  expect(wrapper.text()).toContain('2号')
  expect(wrapper.text()).toContain('2026-09-21T20:00:00Z')
  expect(wrapper.text()).toContain('已结束')
  expect(wrapper.text()).not.toContain('持续中')
})

it('routes room and unclaimed-seat commands through the live page', async () => {
  liveService.setRoom.mockClear()
  liveService.toggleSeatAlive.mockClear()
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('[data-open-session]').trigger('click')
  await wrapper.get('[data-room-code]').setValue('1024')
  await wrapper.get('[data-room-apply]').trigger('click')
  await vi.waitFor(() => expect(liveService.setRoom).toHaveBeenCalledWith('1024'))
  await wrapper.get('[data-seat="5"]').trigger('click')
  await wrapper.get('[data-seat-alive]').trigger('click')
  await vi.waitFor(() => expect(liveService.toggleSeatAlive).toHaveBeenCalledWith(5))
})

it('sends the lunatic fake demon with chosen minions and three bluffs', async () => {
  const lunaticView = {
    ...view,
    fake_pools: { lunatic: ['demon'] },
    seats: view.seats.map((slot) => slot.seat === 5 ? {
      ...slot, assigned_role: { id: 'lunatic', name: '疯子', team: 'outsider' },
    } : slot),
  }
  const wrapper = mount(ContextPanel, { props: { view: lunaticView, selectedSeat: 5, connected: true } })
  await wrapper.get('[data-fake-minion="2"]').trigger('click')
  for (const role of ['chef', 'mayor', 'investigator']) {
    await wrapper.get(`[data-fake-bluff="${role}"]`).trigger('click')
  }
  await wrapper.get('[data-seat-fake="imp"]').trigger('click')
  expect(wrapper.emitted('set-seat-fake')).toEqual([[
    { seat: 5, role: 'imp', minions: [2], bluffs: ['chef', 'mayor', 'investigator'] },
  ]])
})
