import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PlayerResult from '../src/components/player/PlayerResult.vue'
import { makeFinishedPlayerView } from './fixtures/playerView.js'

it('shows win state and switches to the grouped review', async () => {
  const wrapper = mount(PlayerResult, {
    props: { view: makeFinishedPlayerView({ result: { ...makeFinishedPlayerView().result, winner: 'good' } }) },
  })

  expect(wrapper.text()).toContain('你赢了')
  expect(wrapper.text()).toContain('善良阵营获胜')
  expect(wrapper.text()).toContain('1号 阿青：厨师')
  expect(wrapper.text()).toContain('🎒 阿旅：替罪羊（邪恶）')
  await wrapper.get('[data-result-tab="review"]').trigger('click')
  expect(wrapper.text()).toContain('第 1 夜')
  expect(wrapper.text()).toContain('信息错误')
  expect(wrapper.text()).toContain('中毒')
})

it('uses traveler alignment and role-team changes to compute loss state', () => {
  const traveler = makeFinishedPlayerView({
    me: { id: 'p1', name: '阿旅', seat: null, alive: true },
    traveler: { id: 't1', name: '阿旅', align: 'evil', alive: true, role: { name: '替罪羊' } },
  })
  expect(mount(PlayerResult, { props: { view: traveler } }).text()).toContain('你输了')

  const changed = makeFinishedPlayerView({ team_changed: 'evil' })
  expect(mount(PlayerResult, { props: { view: changed } }).text()).toContain('你输了')
})

it('shows a clear empty review state for legacy games', async () => {
  const wrapper = mount(PlayerResult, {
    props: { view: makeFinishedPlayerView({ review: { has_data: false, groups: [] } }) },
  })
  await wrapper.get('[data-result-tab="review"]').trigger('click')
  expect(wrapper.text()).toContain('本局没有可用的复盘记录')
})
