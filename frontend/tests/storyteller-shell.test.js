import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import GameControlPanel from '../src/components/storyteller/GameControlPanel.vue'
import StorytellerHeader from '../src/components/storyteller/StorytellerHeader.vue'
import StorytellerShell from '../src/components/storyteller/StorytellerShell.vue'
import { getPhaseLabel } from '../src/presentation/storyteller.js'
import { lobbyView } from './fixtures/storytellerView.js'

describe('storyteller phase labels', () => {
  it('describes lobby, night, and nomination states', () => {
    expect(getPhaseLabel(lobbyView)).toBe('等待开局')
    expect(getPhaseLabel({ ...lobbyView, status: 'playing', phase: 'night', night_no: 2 }))
      .toBe('第 2 夜')
    expect(getPhaseLabel({ ...lobbyView, status: 'playing', phase: 'day', day_no: 1,
      day_stage: 'nom' })).toBe('第 1 天 · 提名')
  })
})

it('renders the four stable desktop shell regions', () => {
  const wrapper = mount(StorytellerShell, {
    slots: { header: 'header', controls: 'controls', board: 'board', context: 'context' },
  })
  expect(wrapper.get('[data-shell-header]').text()).toBe('header')
  expect(wrapper.get('[data-shell-controls]').text()).toBe('controls')
  expect(wrapper.get('[data-shell-board]').text()).toBe('board')
  expect(wrapper.get('[data-shell-context]').text()).toBe('context')
})

it('shows global state and preserves the complete console escape hatch', () => {
  const wrapper = mount(StorytellerHeader, {
    props: { view: lobbyView, connectionStatus: 'connected' },
  })
  expect(wrapper.text()).toContain('2468')
  expect(wrapper.text()).toContain('暗流涌动')
  expect(wrapper.text()).toContain('等待开局')
  expect(wrapper.text()).toContain('已连接')
  expect(wrapper.get('a').attributes('href')).toBe('/legacy/#/storyteller')
})

it('exposes focused lobby setup controls in the Vue preview', () => {
  const wrapper = mount(GameControlPanel, {
    props: { view: lobbyView, connected: true, pending: [] },
  })
  expect(wrapper.text()).toContain('开局设置')
  expect(wrapper.text()).toContain('暗流涌动')
  expect(wrapper.text()).toContain('手动发身份')
  expect(wrapper.text()).toContain('随机分配角色')
})
