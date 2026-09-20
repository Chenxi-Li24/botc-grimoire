import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PlayerDayAction from '../src/components/player/PlayerDayAction.vue'
import { makeDayPlayerView } from './fixtures/playerView.js'

it('nominates a traveler without coercing its id', async () => {
  const wrapper = mount(PlayerDayAction, {
    props: {
      view: makeDayPlayerView({
        travelers_public: [{ id: 't1', name: '阿旅', alive: true, exiled: false }],
      }),
      connected: true,
      pending: [],
    },
  })

  await wrapper.get('[data-nominee="t1"]').trigger('click')
  expect(wrapper.emitted('nominate')).toBeUndefined()
  await wrapper.get('[data-confirm-nomination]').trigger('click')
  expect(wrapper.emitted('nominate')).toEqual([['t1']])
})

it('nominates a numeric seat and respects a public-board selection', async () => {
  const wrapper = mount(PlayerDayAction, {
    props: {
      view: makeDayPlayerView(), connected: true, pending: [], selectedParticipant: 2,
    },
  })

  expect(wrapper.text()).toContain('2号 小白')
  await wrapper.get('[data-confirm-nomination]').trigger('click')
  expect(wrapper.emitted('nominate')).toEqual([[2]])
})

it('votes immediately when alive and toggles an existing vote', async () => {
  const current = { nominator: 2, nominee: 1, votes: [] }
  const wrapper = mount(PlayerDayAction, {
    props: { view: makeDayPlayerView({ current }), connected: true, pending: [] },
  })

  await wrapper.get('[data-vote]').trigger('click')
  expect(wrapper.emitted('vote')).toHaveLength(1)

  await wrapper.setProps({ view: makeDayPlayerView({ current: { ...current, votes: [1] } }) })
  expect(wrapper.get('[data-vote]').text()).toContain('放下')
})

it('requires confirmation before spending the only dead vote', async () => {
  const view = makeDayPlayerView({
    me: { id: 'p1', name: '阿青', seat: 1, alive: false, dead_vote_used: false },
    current: { nominator: 2, nominee: 1, votes: [] },
  })
  const wrapper = mount(PlayerDayAction, {
    props: { view, connected: true, pending: [] },
  })

  await wrapper.get('[data-vote]').trigger('click')
  expect(wrapper.emitted('vote')).toBeUndefined()
  expect(wrapper.get('[data-vote]').text()).toContain('确认交出死票')
  await wrapper.get('[data-vote]').trigger('click')
  expect(wrapper.emitted('vote')).toHaveLength(1)
})

it('explains why nomination controls are unavailable', () => {
  const wrapper = mount(PlayerDayAction, {
    props: { view: makeDayPlayerView({ day_stage: 'talk' }), connected: true, pending: [] },
  })
  expect(wrapper.text()).toContain('说书人开启提名阶段后才能操作')
  expect(wrapper.find('[data-confirm-nomination]').exists()).toBe(false)
})
