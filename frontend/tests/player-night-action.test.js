import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PlayerNightAction from '../src/components/player/PlayerNightAction.vue'
import { makeNightPlayerView } from './fixtures/playerView.js'

it('drops an unsent draft when the current step changes', async () => {
  const wrapper = mount(PlayerNightAction, {
    props: { view: makeNightPlayerView('step-1'), connected: true, pending: [] },
  })
  await wrapper.get('[data-target="2"]').trigger('click')
  expect(wrapper.get('[data-target="2"]').classes()).toContain('on')

  await wrapper.setProps({ view: makeNightPlayerView('step-2') })

  expect(wrapper.get('[data-target="2"]').classes()).not.toContain('on')
  expect(wrapper.get('[data-submit-night]').attributes('disabled')).toBeDefined()
})

it('submits only the projected current player step', async () => {
  const wrapper = mount(PlayerNightAction, {
    props: { view: makeNightPlayerView('step-1'), connected: true, pending: [] },
  })

  await wrapper.get('[data-target="2"]').trigger('click')
  await wrapper.get('[data-submit-night]').trigger('click')

  expect(wrapper.emitted('submit')).toEqual([[
    { step_id: 'step-1', selected_seats: [2] },
  ]])
})

it('hydrates existing values and requires a projected character choice', async () => {
  const view = makeNightPlayerView('step-1')
  view.night_workflow.prompt = {
    ...view.night_workflow.prompt,
    character_id: 'cerenovus',
    required_fields: ['targets', 'character'],
    values: { targets: [2], character: 'chef' },
    character_candidates: [
      { id: 'chef', name: '厨师', team: 'townsfolk' },
      { id: 'empath', name: '共情者', team: 'townsfolk' },
    ],
  }
  const wrapper = mount(PlayerNightAction, {
    props: { view, connected: true, pending: [] },
  })

  expect(wrapper.get('[data-target="2"]').classes()).toContain('on')
  expect(wrapper.get('[data-character]').element.value).toBe('chef')
  await wrapper.get('[data-submit-night]').trigger('click')
  expect(wrapper.emitted('submit')[0][0]).toEqual({
    step_id: 'step-1', selected_seats: [2], character_id: 'chef',
  })
})

it('shows only projected messages and private context', () => {
  const view = makeNightPlayerView('step-1', {
    my_mad: { role: { name: '厨师' } },
    night_workflow: {
      night_no: 2,
      prompt: null,
      deliveries: [{ id: 'd1', delivered_result: '有恶魔', retracted: false }],
      lunatic_choices: [{ lunatic_seat: 4, target_seats: [2] }],
    },
    grimoire: {
      seats: [{ seat: 2, name: '小白', role: { name: '小恶魔' } }],
      travelers: [],
    },
  })
  const wrapper = mount(PlayerNightAction, {
    props: { view, connected: true, pending: [] },
  })

  expect(wrapper.text()).toContain('有恶魔')
  expect(wrapper.text()).toContain('疯子 4号选择了 2号')
  expect(wrapper.text()).toContain('必须声称自己是「厨师」')
  expect(wrapper.text()).not.toContain('小恶魔')
})

it('closes the choice after receipt while keeping widow grimoire visible', () => {
  const view = makeNightPlayerView('step-1')
  view.night_workflow.prompt = null
  view.night_workflow.receipt = { step_id: 'step-1' }
  view.night_workflow.widow_grimoire = {
    seats: [{ seat: 2, name: '小白', real_character: '酒鬼', perceived_character: '厨师' }],
  }
  const wrapper = mount(PlayerNightAction, {
    props: { view, connected: true, pending: [] },
  })
  expect(wrapper.text()).toContain('说书人已收到')
  expect(wrapper.text()).toContain('真实：酒鬼')
  expect(wrapper.text()).toContain('自认：厨师')
  expect(wrapper.find('[data-submit-night]').exists()).toBe(false)
})

it('labels remembered information by the original night', () => {
  const view = makeNightPlayerView('step-1')
  view.night_workflow.prompt = null
  view.night_workflow.deliveries = [
    { id: 'old', night_no: 2, delivered_result: 3, retracted: false },
  ]
  const wrapper = mount(PlayerNightAction, { props: { view, connected: true, pending: [] } })
  expect(wrapper.text()).toContain('第 2 夜：3')
})
