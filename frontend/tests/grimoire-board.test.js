import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import GrimoireBoard from '../src/components/storyteller/GrimoireBoard.vue'
import { lobbyView } from './fixtures/storytellerView.js'

it('lays out every seat and emits the selected seat number', async () => {
  const wrapper = mount(GrimoireBoard, {
    props: { seats: lobbyView.seats, selectedSeat: null },
  })

  expect(wrapper.findAll('[data-seat]')).toHaveLength(6)
  expect(wrapper.get('[data-seat="1"]').attributes('aria-label')).toBe('1号 · 阿青')
  expect(wrapper.get('[data-seat="3"]').attributes('aria-label')).toBe('3号 · 空座')
  await wrapper.get('[data-seat="1"]').trigger('click')
  expect(wrapper.emitted('select-seat')).toEqual([[1]])
  expect(wrapper.get('[data-seat="2"]').attributes('style')).toContain('--seat-x:')
  expect(wrapper.get('[data-seat="2"]').attributes('style')).toContain('--seat-y:')
})

it('names death and markers instead of relying on color alone', () => {
  const seats = lobbyView.seats.map((seat) => seat.seat === 1
    ? { ...seat, markers: ['poisoned'], player: { ...seat.player, alive: false } }
    : seat)
  const wrapper = mount(GrimoireBoard, { props: { seats, selectedSeat: 1 } })
  const selected = wrapper.get('[data-seat="1"]')

  expect(selected.text()).toContain('死亡')
  expect(selected.text()).toContain('中毒')
  expect(selected.classes()).toContain('is-selected')
})
