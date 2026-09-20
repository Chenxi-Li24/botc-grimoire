import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PlayerLobby from '../src/components/player/PlayerLobby.vue'
import { makeLobbyPlayerView } from './fixtures/playerView.js'

it('keeps identity hidden before start and emits an empty seat choice', async () => {
  const wrapper = mount(PlayerLobby, {
    props: { view: makeLobbyPlayerView(), connected: true, pending: [] },
  })

  expect(wrapper.text()).not.toContain('厨师')
  expect(wrapper.get('[data-seat="1"]').attributes('disabled')).toBeDefined()
  await wrapper.get('[data-seat="2"]').trigger('click')
  expect(wrapper.emitted('sit')).toEqual([[2]])
})

it('emits preset, custom, clear-wish and late traveler commands', async () => {
  const wrapper = mount(PlayerLobby, {
    props: {
      view: makeLobbyPlayerView({ me_wish: '善良' }),
      connected: true,
      pending: [],
    },
  })

  await wrapper.get('[data-wish="邪恶"]').trigger('click')
  expect(wrapper.emitted('wish')).toContainEqual(['邪恶'])
  await wrapper.get('[data-custom-wish]').setValue('想玩信息角色')
  await wrapper.get('[data-save-wish]').trigger('click')
  expect(wrapper.emitted('wish')).toContainEqual(['想玩信息角色'])
  await wrapper.get('[data-clear-wish]').trigger('click')
  expect(wrapper.emitted('wish')).toContainEqual([null])

  await wrapper.setProps({ view: makeLobbyPlayerView({ status: 'playing', phase: 'night' }) })
  await wrapper.get('[data-traveler]').trigger('click')
  expect(wrapper.emitted('traveler')).toHaveLength(1)
})

it('disables lobby commands while disconnected or pending', () => {
  const wrapper = mount(PlayerLobby, {
    props: { view: makeLobbyPlayerView(), connected: false, pending: ['sit'] },
  })

  expect(wrapper.get('[data-seat="2"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-wish="善良"]').attributes('disabled')).toBeDefined()
})
