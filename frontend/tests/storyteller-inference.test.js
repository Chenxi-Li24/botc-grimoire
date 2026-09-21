import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PlayerDetailPanel from '../src/components/storyteller/PlayerDetailPanel.vue'

it('shows each player deduction as read-only and separate from real seat state', () => {
  const wrapper = mount(PlayerDetailPanel, {
    props: {
      seat: { seat: 2, player: { name: '乙', alive: true }, markers: [] },
      view: {
        roles: [{ id: 'chef', name: '厨师', team: 'townsfolk' }], seats: [],
        player_inferences: [{ name: '甲', player_id: 'a', events: [
          { seq: 1, target: 2, category: 'role', operation: 'set', data: { role: 'chef' }, recorded_at: 1, day_no: 1 },
        ], current: [{ seq: 1, target: 2, category: 'role', data: { role: 'chef' } }] }],
      },
    },
  })
  expect(wrapper.get('[data-storyteller-inferences]').text()).toContain('甲')
  expect(wrapper.get('[data-storyteller-inferences]').text()).toContain('厨师')
  expect(wrapper.get('[data-storyteller-inferences]').text()).toContain('玩家推测')
  expect(wrapper.find('[data-storyteller-inferences] button').exists()).toBe(false)
})
