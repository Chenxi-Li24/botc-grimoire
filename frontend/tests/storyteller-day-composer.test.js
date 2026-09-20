import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import DayControlPanel from '../src/components/storyteller/day/DayControlPanel.vue'
import NominationComposer from '../src/components/storyteller/day/NominationComposer.vue'
import { makeStorytellerDayView } from './fixtures/storytellerView.js'

it('switches between talk and nomination stages', async () => {
  const wrapper = mount(DayControlPanel, {
    props: { view: makeStorytellerDayView({ day_stage: 'talk', current: null }), connected: true },
  })
  await wrapper.get('[data-day-stage="nom"]').trigger('click')
  expect(wrapper.emitted('set-stage')).toEqual([['nom']])
})

it('submits a numeric nominator and traveler nominee without coercing ids', async () => {
  const wrapper = mount(NominationComposer, {
    props: { view: makeStorytellerDayView({ current: null }), connected: true },
  })
  await wrapper.get('[data-nominator="2"]').trigger('click')
  await wrapper.get('[data-nominee="t1"]').trigger('click')
  await wrapper.get('[data-confirm-nomination]').trigger('click')
  expect(wrapper.emitted('start-nomination')).toEqual([[{ nominator: 2, nominee: 't1' }]])
})

it('preserves the existing rule that a participant may nominate themself', async () => {
  const wrapper = mount(NominationComposer, {
    props: { view: makeStorytellerDayView({ current: null }), connected: true },
  })
  await wrapper.get('[data-nominator="2"]').trigger('click')
  await wrapper.get('[data-nominee="2"]').trigger('click')
  await wrapper.get('[data-confirm-nomination]').trigger('click')
  expect(wrapper.emitted('start-nomination')).toEqual([[{ nominator: 2, nominee: 2 }]])
})

it('disables dead or spent nominators, prior nominations, and exiled traveler nominees', () => {
  const view = makeStorytellerDayView({
    current: null,
    nominations: [
      { day: 1, nominator: 2, nominee: 3, votes: [], passed: false, executed: false },
    ],
  })
  const wrapper = mount(NominationComposer, { props: { view, connected: true } })

  expect(wrapper.get('[data-nominator="6"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-nominator="2"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-nominee="3"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-nominee="t2"]').attributes('disabled')).toBeDefined()
})

it('disables commands while disconnected', () => {
  const wrapper = mount(NominationComposer, {
    props: { view: makeStorytellerDayView({ current: null }), connected: false },
  })
  expect(wrapper.get('[data-nominator="1"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-confirm-nomination]').attributes('disabled')).toBeDefined()
})

it('keeps a failed draft and clears it only after a successful pending cycle', async () => {
  const wrapper = mount(NominationComposer, {
    props: { view: makeStorytellerDayView({ current: null }), connected: true, busy: false },
  })
  await wrapper.get('[data-nominator="1"]').trigger('click')
  await wrapper.get('[data-nominee="2"]').trigger('click')
  await wrapper.get('[data-confirm-nomination]').trigger('click')
  await wrapper.setProps({ error: new Error('今天已经提名过') })
  expect(wrapper.text()).toContain('今天已经提名过')
  expect(wrapper.get('[data-nominator="1"]').classes()).toContain('selected')

  await wrapper.setProps({ error: null, busy: true })
  await wrapper.setProps({ busy: false })
  expect(wrapper.get('[data-nominator="1"]').classes()).not.toContain('selected')
})
