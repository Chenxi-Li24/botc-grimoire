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
