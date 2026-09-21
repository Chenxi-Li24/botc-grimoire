import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PlayerBoard from '../src/components/player/PlayerBoard.vue'
import { makePlayerView } from './fixtures/playerView.js'

it('renders public participants without exposing another seat private role', () => {
  const view = makePlayerView({
    seats: [
      { seat: 1, player: { name: '阿青', alive: true }, is_me: true },
      { seat: 2, player: { name: '小白', alive: false, role: { name: '小恶魔' } }, dead_vote_left: true },
    ],
    travelers_public: [{ id: 't2', name: '阿旅', alive: true, role: { name: '替罪羊' } }],
  })
  const wrapper = mount(PlayerBoard, { props: { view } })

  expect(wrapper.text()).toContain('小白')
  expect(wrapper.text()).toContain('替罪羊')
  expect(wrapper.text()).not.toContain('小恶魔')
  expect(wrapper.get('[data-seat="2"]').classes()).toContain('is-dead')
  expect(wrapper.get('[data-seat="2"]').text()).toContain('死票')
  expect(wrapper.find('img[src^="/role-icons/"]').exists()).toBe(false)
  expect(wrapper.get('[data-seat="2"]').classes().some((name) => name.startsWith('team-'))).toBe(false)
})

it('emits numeric seat and traveler ids as distinct participant values', async () => {
  const wrapper = mount(PlayerBoard, {
    props: {
      view: makePlayerView({
        travelers_public: [{ id: 't2', name: '阿旅', alive: true, role: { name: '替罪羊' } }],
      }),
    },
  })

  await wrapper.get('[data-seat="2"]').trigger('click')
  await wrapper.get('[data-traveler="t2"]').trigger('click')
  expect(wrapper.emitted('select-participant')).toEqual([[2], ['t2']])
})

it('places seats clockwise around the town square', () => {
  const view = makePlayerView({
    seats: [1, 2, 3, 4].map((seat) => ({
      seat,
      player: { id: `p${seat}`, name: `玩家${seat}`, alive: true },
    })),
  })
  const wrapper = mount(PlayerBoard, { props: { view } })
  const positions = [
    [50, 14],
    [86, 50],
    [50, 86],
    [14, 50],
  ]

  positions.forEach(([x, y], index) => {
    const seat = wrapper.get(`[data-seat="${index + 1}"]`)
    expect(seat.element.style.getPropertyValue('--seat-x')).toBe(`${x}%`)
    expect(seat.element.style.getPropertyValue('--seat-y')).toBe(`${y}%`)
  })
})

it('allows an unclaimed offline seat in private inference mode and labels guesses as personal', async () => {
  const wrapper = mount(PlayerBoard, {
    props: { view: makePlayerView({
      seats: [{ seat: 1, player: null }, { seat: 2, player: { name: '乙', alive: true } }],
      inference: { current: [{ target: 1, category: 'role', data: { role: 'chef' } }] },
      script_roles: [{ id: 'chef', name: '厨师' }],
    }), inferenceMode: true },
  })
  expect(wrapper.get('[data-seat="1"]').attributes('disabled')).toBeUndefined()
  expect(wrapper.get('[data-seat="1"]').text()).toContain('我的推测：厨师')
  await wrapper.get('[data-seat="1"]').trigger('click')
  expect(wrapper.emitted('select-participant')).toEqual([[1]])
})
