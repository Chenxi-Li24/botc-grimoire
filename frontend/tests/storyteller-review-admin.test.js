import { mount } from '@vue/test-utils'
import { nextTick, ref, shallowRef } from 'vue'
import { expect, it, vi } from 'vitest'
import ContextPanel from '../src/components/storyteller/ContextPanel.vue'
import StorytellerHeader from '../src/components/storyteller/StorytellerHeader.vue'
import GameControlPanel from '../src/components/storyteller/GameControlPanel.vue'
import StorytellerLiveView from '../src/components/storyteller/StorytellerLiveView.vue'
import ReviewPanel from '../src/components/storyteller/ReviewPanel.vue'
import { makeStorytellerDayView } from './fixtures/storytellerView.js'

const view = makeStorytellerDayView({
  review: {
    has_data: true,
    groups: [{ label: '第1夜', phase: 'night', items: [
      { text: '厨师得知信息', wrong: false, mark: { seat: 1, night: 1 } },
      { text: '恶魔选择玩家', wrong: false, mark: null },
    ] }],
  },
})
let liveView
const liveService = {
  setWinner: vi.fn().mockResolvedValue({ status: 'playing' }),
  markReview: vi.fn().mockResolvedValue({ status: 'playing' }),
}
vi.mock('../src/composables/useStorytellerView.js', () => ({
  useStorytellerView: () => ({ view: liveView, connectionStatus: ref('connected') }),
}))
vi.mock('../src/services/storyteller.js', () => ({
  createStorytellerService: () => liveService,
}))

it('requires confirmation before declaring the winning side', async () => {
  const wrapper = mount(ContextPanel, { props: { view, adminTab: 'end', connected: true } })
  await wrapper.get('[data-end-good]').trigger('click')
  expect(wrapper.emitted('set-winner')).toBeUndefined()
  await wrapper.get('[data-end-good]').trigger('click')
  expect(wrapper.emitted('set-winner')).toEqual([['good']])
})

it('can undo an announced result without closing the grimoire', async () => {
  const wrapper = mount(ContextPanel, {
    props: { view: { ...view, winner: 'evil' }, adminTab: 'end', connected: true },
  })
  expect(wrapper.text()).toContain('邪恶')
  await wrapper.get('[data-end-undo]').trigger('click')
  expect(wrapper.emitted('set-winner')).toBeUndefined()
  await wrapper.get('[data-end-undo]').trigger('click')
  expect(wrapper.emitted('set-winner')).toEqual([[null]])
})

it('marks a review reply wrong, then restores it and returns to the grimoire', async () => {
  const wrapper = mount(ReviewPanel, { props: { view, connected: true } })
  expect(wrapper.text()).toContain('第1夜')
  expect(wrapper.text()).toContain('厨师得知信息')
  await wrapper.get('[data-review-mark="1:1"]').trigger('click')
  expect(wrapper.emitted('mark-review')).toEqual([[{ seat: 1, night: 1, wrong: true }]])
  await wrapper.setProps({ view: {
    ...view,
    review: { ...view.review, groups: [{ ...view.review.groups[0], items: [
      { text: '厨师得知信息', wrong: true, mark: { seat: 1, night: 1 } },
    ] }] },
  } })
  await wrapper.get('[data-review-mark="1:1"]').trigger('click')
  expect(wrapper.emitted('mark-review')[1]).toEqual([{ seat: 1, night: 1, wrong: false }])
  await wrapper.get('[data-review-back]').trigger('click')
  expect(wrapper.emitted('back')).toEqual([[]])
})

it('shows an empty review state and blocks mark actions offline', () => {
  const empty = mount(ReviewPanel, { props: { view: { ...view, review: { has_data: false, groups: [] } }, connected: true } })
  expect(empty.text()).toContain('没有可用的复盘记录')
  const offline = mount(ReviewPanel, { props: { view, connected: false } })
  expect(offline.get('[data-review-mark="1:1"]').attributes('disabled')).toBeDefined()
})

it('opens the native end and review views from the header', async () => {
  const wrapper = mount(StorytellerHeader, { props: { view: { ...view, winner: 'good' }, connectionStatus: 'connected' } })
  await wrapper.get('[data-open-end]').trigger('click')
  await wrapper.get('[data-open-review]').trigger('click')
  expect(wrapper.emitted('open-end')).toEqual([[]])
  expect(wrapper.emitted('open-review')).toEqual([[]])
})

it('replaces day controls with the announced result after the game ends', () => {
  const wrapper = mount(GameControlPanel, { props: { view: { ...view, winner: 'good' }, connected: true } })
  expect(wrapper.text()).toContain('善良阵营获胜')
  expect(wrapper.find('[data-day-stage="nom"]').exists()).toBe(false)
})

it('keeps result and review in the Vue page while the server view remains authoritative', async () => {
  liveView = shallowRef(view)
  liveService.setWinner.mockClear()
  liveService.markReview.mockClear()
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('[data-open-end]').trigger('click')
  await wrapper.get('[data-end-good]').trigger('click')
  await wrapper.get('[data-end-good]').trigger('click')
  await vi.waitFor(() => expect(liveService.setWinner).toHaveBeenCalledWith('good'))
  liveView.value = { ...view, winner: 'good' }
  await nextTick()
  await wrapper.get('[data-open-review]').trigger('click')
  expect(wrapper.find('[data-review-panel]').exists()).toBe(true)
  await wrapper.get('[data-review-mark="1:1"]').trigger('click')
  await vi.waitFor(() => expect(liveService.markReview).toHaveBeenCalledWith(1, 1, true))
  await wrapper.get('[data-review-back]').trigger('click')
  expect(wrapper.find('[data-review-panel]').exists()).toBe(false)
  expect(wrapper.find('[data-seat="1"]').exists()).toBe(true)
})
