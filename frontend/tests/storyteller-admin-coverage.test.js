import { mount, shallowMount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import StorytellerHeader from '../src/components/storyteller/StorytellerHeader.vue'
import GameControlPanel from '../src/components/storyteller/GameControlPanel.vue'
import ContextPanel from '../src/components/storyteller/ContextPanel.vue'
import JoinPanel from '../src/components/storyteller/JoinPanel.vue'
import { lobbyView, makeStorytellerDayView } from './fixtures/storytellerView.js'

it('offers native administration in lobby, day, night, and ended states', () => {
  const day = makeStorytellerDayView()
  const states = [
    lobbyView,
    day,
    { ...day, phase: 'night' },
    { ...day, winner: 'good' },
  ]
  for (const view of states) {
    const header = mount(StorytellerHeader, { props: { view, connectionStatus: 'connected' } })
    const controls = mount(GameControlPanel, { props: { view, connected: true, night: { workflow: null } } })
    expect(header.find('a[href^="/legacy"]').exists()).toBe(false)
    expect(controls.find('a[href^="/legacy"]').exists()).toBe(false)
    expect(header.find('[data-open-session]').exists()).toBe(true)
    expect(header.find('[data-open-join]').exists()).toBe(true)
    if (view.status === 'playing') {
      expect(header.find('[data-open-seats]').exists()).toBe(true)
      expect(header.find('[data-open-travelers]').exists()).toBe(true)
      expect(header.find('[data-open-chats]').exists()).toBe(true)
      expect(header.find('[data-open-end]').exists()).toBe(true)
    }
    if (view.winner) expect(header.find('[data-open-review]').exists()).toBe(true)
  }
})

it('opens the join codes during a running night instead of the night task', async () => {
  const view = { ...makeStorytellerDayView(), phase: 'night' }
  const header = mount(StorytellerHeader, { props: { view, connectionStatus: 'connected' } })
  await header.get('[data-open-join]').trigger('click')
  expect(header.emitted('open-join')).toEqual([[]])

  const context = shallowMount(ContextPanel, {
    props: { view, night: { workflow: {} }, adminTab: 'join' },
  })
  expect(context.findComponent(JoinPanel).exists()).toBe(true)
})

it('exposes a compact administration menu for narrow screens', async () => {
  const header = mount(StorytellerHeader, {
    props: { view: makeStorytellerDayView(), connectionStatus: 'connected' },
  })
  expect(header.get('[data-open-admin-menu]').attributes('aria-expanded')).toBe('false')
  await header.get('[data-open-admin-menu]').trigger('click')
  expect(header.get('[data-open-admin-menu]').attributes('aria-expanded')).toBe('true')
  expect(header.get('[data-admin-actions]').classes()).toContain('is-open')
  await header.get('[data-open-chats]').trigger('click')
  expect(header.emitted('open-chats')).toEqual([[]])
  expect(header.get('[data-open-admin-menu]').attributes('aria-expanded')).toBe('false')
})
