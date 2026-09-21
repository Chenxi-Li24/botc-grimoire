import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import SeatNode from '../src/components/storyteller/SeatNode.vue'
import PlayerDetailPanel from '../src/components/storyteller/PlayerDetailPanel.vue'
import { makeStorytellerDayView } from './fixtures/storytellerView.js'

const lunatic = { id: 'lunatic', name: '疯子', team: 'outsider' }
const imp = { id: 'imp', name: '小恶魔', team: 'demon' }

it('shows perceived identity and real identity on storyteller seat without changing real team', () => {
  const wrapper = mount(SeatNode, {
    props: { seat: { seat: 7, player: null, assigned_role: lunatic, fake_role: imp, red_herring: true }, position: {} },
  })
  expect(wrapper.text()).toContain('他以为：小恶魔')
  expect(wrapper.text()).toContain('🌙 疯子')
  expect(wrapper.text()).toContain('🎯 宿敌')
  expect(wrapper.classes()).toContain('team-outsider')
  expect(wrapper.attributes('aria-label')).toContain('真实身份 疯子')
  expect(wrapper.attributes('aria-label')).toContain('他以为 小恶魔')
})

it('uses the actual changed alignment for the seat ring, never the perceived role', () => {
  const wrapper = mount(SeatNode, {
    props: { seat: { seat: 7, player: null, assigned_role: lunatic, fake_role: imp, team_change: 'evil' }, position: {} },
  })
  expect(wrapper.classes()).toContain('team-evil')
  expect(wrapper.classes()).not.toContain('team-demon')
})

it('warns that an unset lunatic perception is unknown', () => {
  const wrapper = mount(SeatNode, {
    props: { seat: { seat: 7, player: null, assigned_role: lunatic }, position: {} },
  })
  expect(wrapper.text()).toContain('待配置认知')
  expect(wrapper.text()).not.toContain('他以为')
})

it('uses a claimed player avatar and falls back to the role icon with descriptive alt text', async () => {
  const withAvatar = mount(SeatNode, {
    props: { seat: { seat: 1, player: { name: '阿青', role: imp, avatar_url: '/avatars/a.png' } }, position: {} },
  })
  expect(withAvatar.get('img').attributes('src')).toBe('/avatars/a.png')
  expect(withAvatar.get('img').attributes('alt')).toContain('阿青')
  await withAvatar.get('img').trigger('error')
  expect(withAvatar.get('img').attributes('src')).toContain('imp')
  const fallback = mount(SeatNode, {
    props: { seat: { seat: 2, player: { name: '小白', role: imp } }, position: {} },
  })
  expect(fallback.get('img').attributes('src')).toContain('imp')
  expect(fallback.get('img').attributes('alt')).toContain('小恶魔')
})

it('shows current effects before subjective notes and filters three audit categories by night', async () => {
  const base = makeStorytellerDayView()
  const seat = {
    ...base.seats[4], assigned_role: lunatic, fake_role: imp, red_herring: true,
    effects: [{ id: 'effect-1', type: 'poisoned', state: 'active', started_at: 'night:2',
      source_seat: 2, source_character: 'poisoner', expected_end: 'next_dusk' }],
    audit: { complete: false, events: [
      { id: 'a1', category: 'status', kind: 'poisoned', phase: 'night', number: 2, state: 'active', source_event: 'ev-1' },
      { id: 'a2', category: 'information', kind: 'delivery', phase: 'night', number: 2,
        state: 'withdrawn', delivered_result: '4号是恶魔', claims: [{ label: '判断', truthful: false }],
        registrations: [{ seat: 4, as: 'demon' }], effect_snapshot: ['poisoned'],
        corrections: [{ id: 'correction-1', reason: '登记更正', claims: [{ label: '判断', truthful: true }] }],
        source_event: 'ev-2' },
      { id: 'a3', category: 'action', kind: 'outcome', phase: 'night', number: 3,
        role_snapshot: 'lunatic', selected_seats: [4], affected_seats: [], state: 'pending', source_event: 'ev-3' },
    ] },
  }
  const view = { ...base, seats: base.seats.map((item) => item.seat === 5 ? seat : item) }
  const wrapper = mount(PlayerDetailPanel, { props: { seat, view } })
  expect(wrapper.get('[data-current-status]').text()).toContain('中毒')
  expect(wrapper.get('[data-current-status]').text()).toContain('2号')
  expect(wrapper.text()).toContain('🎯 宿敌')
  expect(wrapper.find('[data-current-status]').element.compareDocumentPosition(wrapper.find('[data-storyteller-inferences]').element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(wrapper.get('[data-audit-category="information"]').text()).toContain('4号是恶魔')
  expect(wrapper.get('[data-audit-category="information"]').text()).toContain('已撤回')
  expect(wrapper.get('[data-audit-category="information"]').text()).toContain('登记更正')
  expect(wrapper.get('[data-audit-category="information"]').text()).toContain('4号')
  expect(wrapper.get('[data-audit-category="action"]').text()).toContain('选择：4号')
  await wrapper.get('[data-audit-round]').setValue('night:2')
  expect(wrapper.find('[data-audit-category="action"]').exists()).toBe(false)
  expect(wrapper.find('[data-audit-category="information"]').exists()).toBe(true)
  await wrapper.get('[data-audit-filter]').setValue('status')
  expect(wrapper.find('[data-audit-category="information"]').exists()).toBe(false)
})

it('distinguishes an unsent draft from a missing old record', () => {
  const base = makeStorytellerDayView()
  const seat = { ...base.seats[4], audit: { complete: false, events: [
    { id: 'draft-1', category: 'information', kind: 'draft', phase: 'night', number: 2,
      selected_seats: [3], state: 'unsent' },
  ] } }
  const wrapper = mount(PlayerDetailPanel, { props: { seat, view: base } })
  expect(wrapper.get('[data-audit-category="information"]').text()).toContain('未发送')
  expect(wrapper.get('[data-audit-category="information"]').text()).toContain('3号')
  expect(wrapper.text()).not.toContain('无历史记录')
})

it('marks old seats without evidence as missing history', () => {
  const base = makeStorytellerDayView()
  const wrapper = mount(PlayerDetailPanel, { props: { seat: base.seats[4], view: base } })
  expect(wrapper.text()).toContain('无历史记录')
  expect(wrapper.text()).not.toContain('未发送')
})
