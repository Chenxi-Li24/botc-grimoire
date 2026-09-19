import { mount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import AdvancedSettings from '../src/components/storyteller/AdvancedSettings.vue'
import ConfirmAction from '../src/components/storyteller/ConfirmAction.vue'
import GameControlPanel from '../src/components/storyteller/GameControlPanel.vue'
import RoleAssignmentControls from '../src/components/storyteller/RoleAssignmentControls.vue'
import SetupControls from '../src/components/storyteller/SetupControls.vue'
import StartControl from '../src/components/storyteller/StartControl.vue'
import { lobbyView } from './fixtures/storytellerView.js'

const buttonWithText = (wrapper, text) => wrapper.findAll('button').find((button) => button.text().includes(text))

it('requires two actions before applying a destructive configuration', async () => {
  const wrapper = mount(SetupControls, {
    props: { view: lobbyView, connected: true, pending: [] },
  })
  await buttonWithText(wrapper, '＋').trigger('click')
  await buttonWithText(wrapper, '应用新配置').trigger('click')
  expect(wrapper.emitted('configure')).toBeUndefined()
  expect(wrapper.text()).toContain('会清空所有座位和角色分配')
  await buttonWithText(wrapper, '再次确认并清空座位').trigger('click')
  expect(wrapper.emitted('configure')).toEqual([[{ script: 'trouble-brewing', playerCount: 7 }]])
})

it('disarms confirmation when its summary changes', async () => {
  const wrapper = mount(ConfirmAction, {
    props: { label: '执行', confirmLabel: '再次确认', summary: '原操作' },
  })
  await wrapper.get('button').trigger('click')
  expect(wrapper.get('button').text()).toBe('再次确认')
  await wrapper.setProps({ summary: '新操作' })
  expect(wrapper.get('button').text()).toBe('执行')
})

it('requires confirmation before random assignment starts the first night', async () => {
  const wrapper = mount(RoleAssignmentControls, {
    props: { view: lobbyView, connected: true, pending: [], manualActive: false },
  })
  await buttonWithText(wrapper, '随机分配角色').trigger('click')
  expect(wrapper.emitted('assign-random')).toBeUndefined()
  expect(wrapper.text()).toContain('立即发牌并进入第一夜')
  await buttonWithText(wrapper, '确认发牌并进入第一夜').trigger('click')
  expect(wrapper.emitted('assign-random')).toEqual([[]])
})

it('shows the Sentinel-adjusted composition before random assignment', async () => {
  const wrapper = mount(RoleAssignmentControls, {
    props: { view: { ...lobbyView, sentinel: 1 }, connected: true, pending: [], manualActive: false },
  })
  await buttonWithText(wrapper, '随机分配角色').trigger('click')
  expect(wrapper.text()).toContain('镇民2 / 外来者2 / 爪牙1 / 恶魔1')
})

it('emits Sentinel and fabled changes independently', async () => {
  const wrapper = mount(AdvancedSettings, {
    props: { view: lobbyView, connected: true, pending: [] },
  })
  await wrapper.get('summary').trigger('click')
  await buttonWithText(wrapper, '+1 外来者').trigger('click')
  await buttonWithText(wrapper, '天使').trigger('click')
  expect(wrapper.emitted('set-sentinel')).toEqual([[1]])
  expect(wrapper.emitted('toggle-fabled')).toEqual([[{ id: 'angel', on: true }]])
})

it('shows forced start only for a fully assigned partial lobby', async () => {
  const wrapper = mount(StartControl, { props: { connected: true, pending: [] } })
  expect(wrapper.text()).toContain('迟到玩家')
  await wrapper.get('button').trigger('click')
  expect(wrapper.emitted('start')).toEqual([[]])
})

it('turns lobby mutations into a read-only summary after play begins', () => {
  const wrapper = mount(GameControlPanel, {
    props: { view: { ...lobbyView, status: 'playing', phase: 'night', night_no: 1 } },
  })
  expect(wrapper.text()).toContain('大厅配置已锁定')
  expect(wrapper.text()).toContain('完整控制台')
  expect(wrapper.text()).not.toContain('随机分配角色')
})
