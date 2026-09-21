import { mount } from '@vue/test-utils'
import { nextTick, ref, shallowRef } from 'vue'
import { expect, it, vi } from 'vitest'
import ContextPanel from '../src/components/storyteller/ContextPanel.vue'
import StorytellerHeader from '../src/components/storyteller/StorytellerHeader.vue'
import StorytellerLiveView from '../src/components/storyteller/StorytellerLiveView.vue'
import { makeStorytellerDayView } from './fixtures/storytellerView.js'

const view = makeStorytellerDayView({
  travelers: [
    { id: 't1', name: '旅人甲', role_id: null, align: 'good', alive: true, exiled: false },
    { id: 't2', name: '旅人乙', role_id: 'beggar', align: 'evil', alive: false, exiled: true },
    { id: 't3', name: '旅人丙', role_id: 'beggar', align: 'good', alive: true, exiled: false },
  ],
  traveler_roles: [
    { id: 'apprentice', name: '学徒', ability: '获得能力' },
    { id: 'beggar', name: '乞丐', ability: '获得信息' },
  ],
  traveler_recommended: ['apprentice'],
})

const liveService = {
  addTraveler: vi.fn().mockResolvedValue({ status: 'playing' }),
  assignTraveler: vi.fn().mockResolvedValue({ status: 'playing' }),
  setTravelerExile: vi.fn().mockResolvedValue({ status: 'playing' }),
  toggleTravelerAlive: vi.fn().mockResolvedValue({ status: 'playing' }),
}
vi.mock('../src/composables/useStorytellerView.js', () => ({
  useStorytellerView: () => ({ view: shallowRef(view), connectionStatus: ref('connected') }),
}))
vi.mock('../src/services/storyteller.js', () => ({
  createStorytellerService: () => liveService,
}))

function mountTravelers(connected = true) {
  return mount(ContextPanel, {
    props: { view, selectedSeat: null, adminTab: 'travelers', connected },
  })
}

it('manages a traveler from the native context panel', async () => {
  const wrapper = mountTravelers()
  expect(wrapper.text()).toContain('旅人甲')
  expect(wrapper.text()).toContain('乞丐')
  await wrapper.get('[data-traveler-name]').setValue('  迟到玩家  ')
  await wrapper.get('form').trigger('submit')
  expect(wrapper.emitted('add-traveler')).toEqual([['迟到玩家']])

  await wrapper.get('[data-traveler-select="t1"]').trigger('click')
  expect(wrapper.text()).toContain('学徒')
  await wrapper.get('[data-traveler-align="evil"]').trigger('click')
  await wrapper.get('[data-traveler-role="apprentice"]').trigger('click')
  expect(wrapper.emitted('assign-traveler')).toEqual([[{ id: 't1', role: 'apprentice', align: 'evil' }]])
  await wrapper.get('[data-traveler-alive="t3"]').trigger('click')
  expect(wrapper.emitted('toggle-traveler-alive')).toEqual([['t3']])
})

it('requires confirmation for exile but reverses it directly', async () => {
  const wrapper = mountTravelers()
  const exile = wrapper.get('[data-traveler-exile="t1"]')
  await exile.trigger('click')
  expect(wrapper.emitted('set-traveler-exile')).toBeUndefined()
  await exile.trigger('click')
  expect(wrapper.emitted('set-traveler-exile')).toEqual([[{ id: 't1', exiled: true }]])
  await wrapper.get('[data-traveler-exile="t2"]').trigger('click')
  expect(wrapper.emitted('set-traveler-exile')[1]).toEqual([{ id: 't2', exiled: false }])
})

it('blocks traveler changes offline and rejects a blank name', async () => {
  const offline = mountTravelers(false)
  expect(offline.get('[data-traveler-add]').attributes('disabled')).toBeDefined()
  expect(offline.get('[data-traveler-alive="t1"]').attributes('disabled')).toBeDefined()
  const online = mountTravelers()
  await online.get('[data-traveler-name]').setValue('   ')
  await online.get('form').trigger('submit')
  await nextTick()
  expect(online.emitted('add-traveler')).toBeUndefined()
})

it('opens traveler administration from the storyteller header', async () => {
  const wrapper = mount(StorytellerHeader, {
    props: { view, connectionStatus: 'connected' },
  })
  await wrapper.get('[data-open-travelers]').trigger('click')
  expect(wrapper.emitted('open-travelers')).toEqual([[]])
})

it('routes traveler actions through the live storyteller command boundary', async () => {
  liveService.addTraveler.mockClear()
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('[data-open-travelers]').trigger('click')
  await wrapper.get('[data-traveler-name]').setValue('新旅行者')
  await wrapper.get('form').trigger('submit')
  await vi.waitFor(() => expect(liveService.addTraveler).toHaveBeenCalledWith('新旅行者'))
})
