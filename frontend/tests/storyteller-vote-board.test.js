import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import DayControlPanel from '../src/components/storyteller/day/DayControlPanel.vue'
import VoteBoard from '../src/components/storyteller/day/VoteBoard.vue'
import { activeNomination, makeStorytellerDayView } from './fixtures/storytellerView.js'

it('renders vote state directly from concurrent projection updates', async () => {
  const wrapper = mount(DayControlPanel, {
    props: { view: makeStorytellerDayView({ current: activeNomination([]) }), connected: true },
  })
  expect(wrapper.get('[data-voter="2"]').classes()).not.toContain('on')
  await wrapper.setProps({ view: makeStorytellerDayView({ current: activeNomination([2]) }) })
  expect(wrapper.get('[data-voter="2"]').classes()).toContain('on')
})

it('enables living and unused dead votes while disabling spent or exiled voters', async () => {
  const view = makeStorytellerDayView({
    current: activeNomination([]),
    seats: makeStorytellerDayView().seats.map((slot) => (
      slot.seat === 4
        ? { ...slot, player: { ...slot.player, alive: false, dead_vote_used: true }, dead_vote_left: undefined }
        : slot
    )),
  })
  const wrapper = mount(VoteBoard, { props: { view, connected: true, pending: [] } })

  expect(wrapper.get('[data-voter="1"]').attributes('disabled')).toBeUndefined()
  expect(wrapper.get('[data-voter="6"]').attributes('disabled')).toBeUndefined()
  expect(wrapper.get('[data-voter="4"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-voter="t1"]').attributes('disabled')).toBeUndefined()
  expect(wrapper.get('[data-voter="t2"]').attributes('disabled')).toBeDefined()

  await wrapper.setProps({ view: { ...view, current: activeNomination([4]) } })
  expect(wrapper.get('[data-voter="4"]').classes()).toContain('on')
  expect(wrapper.get('[data-voter="4"]').attributes('disabled')).toBeUndefined()
})

it('uses the current quorum and emits mixed participant ids unchanged', async () => {
  const wrapper = mount(VoteBoard, {
    props: { view: makeStorytellerDayView({ current: activeNomination([1, 2]) }), connected: true, pending: [] },
  })
  expect(wrapper.get('[data-vote-summary]').text()).toContain('2 / 3')
  expect(wrapper.get('[data-vote-summary]').classes()).toContain('below')

  await wrapper.get('[data-voter="t1"]').trigger('click')
  expect(wrapper.emitted('toggle-vote')).toEqual([['t1']])

  await wrapper.setProps({ view: makeStorytellerDayView({ current: activeNomination([1, 2, 3]) }) })
  expect(wrapper.get('[data-vote-summary]').classes()).toContain('reached')
})
