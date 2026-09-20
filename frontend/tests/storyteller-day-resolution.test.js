import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import DayResolution from '../src/components/storyteller/day/DayResolution.vue'
import NominationHistory from '../src/components/storyteller/day/NominationHistory.vue'
import { activeNomination, makeStorytellerDayView } from './fixtures/storytellerView.js'

it('requires two clicks to pass or fail a nomination', async () => {
  const wrapper = mount(DayResolution, {
    props: { view: makeStorytellerDayView({ current: activeNomination([1, 2, 3]) }), connected: true },
  })
  await wrapper.get('[data-resolve-pass] button').trigger('click')
  expect(wrapper.emitted('resolve-nomination')).toBeUndefined()
  await wrapper.get('[data-resolve-pass] button').trigger('click')
  expect(wrapper.emitted('resolve-nomination')).toEqual([[true]])
})

it('rearms end-day confirmation after an unresolved-nomination error', async () => {
  const wrapper = mount(DayResolution, {
    props: { view: makeStorytellerDayView({ current: activeNomination([]) }), connected: true, pending: [] },
  })
  await wrapper.get('[data-end-day] button').trigger('click')
  expect(wrapper.get('[data-end-day] button').text()).toContain('确认结束')
  await wrapper.setProps({ pending: ['day:end'] })
  await wrapper.setProps({ pending: [], error: { key: 'day:end', message: '先结算当前提名' } })
  expect(wrapper.text()).toContain('先结算当前提名')
  expect(wrapper.get('[data-end-day] button').text()).toContain('结束白天')
})

it('requires confirmation before ending the day', async () => {
  const wrapper = mount(DayResolution, {
    props: { view: makeStorytellerDayView({ current: null }), connected: true, pending: [] },
  })
  await wrapper.get('[data-end-day] button').trigger('click')
  await wrapper.get('[data-end-day] button').trigger('click')
  expect(wrapper.emitted('end-day')).toEqual([[]])
})

it('shows unique execution leaders, ties, exile, and grouped history', () => {
  const nominations = [
    { day: 1, nominator: 1, nominee: 2, votes: [1, 2, 3], passed: true, executed: false },
    { day: 1, nominator: 3, nominee: 't1', votes: [1, 2, 3, 4], passed: true, executed: true },
    { day: 2, nominator: 4, nominee: 5, votes: [], passed: false, executed: false },
  ]
  const leaderView = makeStorytellerDayView({ current: null, nominations })
  const resolution = mount(DayResolution, { props: { view: leaderView, connected: true } })
  expect(resolution.text()).toContain('2号 小白')
  expect(resolution.text()).toContain('3 票')

  const history = mount(NominationHistory, { props: { view: leaderView } })
  expect(history.text()).toContain('第 1 天')
  expect(history.text()).toContain('第 2 天')
  expect(history.text()).toContain('已流放')
  expect(history.text()).toContain('未通过')

  const tied = mount(DayResolution, {
    props: {
      view: makeStorytellerDayView({
        current: null,
        nominations: [...nominations, { day: 1, nominator: 5, nominee: 3, votes: [1, 2, 3], passed: true, executed: false }],
      }),
      connected: true,
    },
  })
  expect(tied.text()).toContain('平票')
  expect(tied.text()).toContain('无人处决')
})
