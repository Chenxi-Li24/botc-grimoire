import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import ContextPanel from '../src/components/storyteller/ContextPanel.vue'
import StorytellerHeader from '../src/components/storyteller/StorytellerHeader.vue'
import { lobbyView } from './fixtures/storytellerView.js'

it('validates a four-digit room number before sending the change', async () => {
  const wrapper = mount(ContextPanel, { props: { view: lobbyView, adminTab: 'session', connected: true } })
  await wrapper.get('[data-room-code]').setValue('12')
  await wrapper.get('[data-room-apply]').trigger('click')
  expect(wrapper.emitted('set-room')).toBeUndefined()
  await wrapper.get('[data-room-code]').setValue('1024')
  await wrapper.get('[data-room-apply]').trigger('click')
  expect(wrapper.emitted('set-room')).toEqual([['1024']])
})

it('requires two clicks for load and reset, and disables writes offline', async () => {
  const wrapper = mount(ContextPanel, { props: { view: lobbyView, adminTab: 'session', connected: true } })
  await wrapper.get('[data-session-load]').trigger('click')
  expect(wrapper.emitted('load-save')).toBeUndefined()
  await wrapper.get('[data-session-load]').trigger('click')
  expect(wrapper.emitted('load-save')).toEqual([[]])
  await wrapper.get('[data-session-reset]').trigger('click')
  expect(wrapper.emitted('reset-game')).toBeUndefined()
  await wrapper.get('[data-session-reset]').trigger('click')
  expect(wrapper.emitted('reset-game')).toEqual([[]])
  const offline = mount(ContextPanel, { props: { view: lobbyView, adminTab: 'session', connected: false } })
  expect(offline.get('[data-session-reset]').attributes('disabled')).toBeDefined()
})

it('opens session administration from the storyteller header', async () => {
  const wrapper = mount(StorytellerHeader, { props: { view: lobbyView, connectionStatus: 'connected' } })
  await wrapper.get('[data-open-session]').trigger('click')
  expect(wrapper.emitted('open-session')).toEqual([[]])
})
