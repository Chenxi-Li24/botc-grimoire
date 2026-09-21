import { mount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import SetupControls from '../src/components/storyteller/SetupControls.vue'
import BalloonistTaskCard from '../src/components/storyteller/night/BalloonistTaskCard.vue'
import PlayerPage from '../src/pages/PlayerPage.vue'
import { lobbyView } from './fixtures/storytellerView.js'
import { makeNightPlayerView } from './fixtures/playerView.js'
import { usePlayerView } from '../src/composables/usePlayerView.js'
import { ref, shallowRef } from 'vue'

vi.mock('../src/composables/usePlayerView.js', () => ({ usePlayerView: vi.fn() }))

const click = (wrapper, text) => wrapper.findAll('button').find((button) => button.text().includes(text))?.trigger('click')

it('requires Balloonist version and outsider delta in setup confirmation', async () => {
  const view = {
    ...lobbyView,
    scripts: [...lobbyView.scripts, {
      id: 'wafu-leiming', name: '瓦釜雷鸣', en: 'Wafu', min: 7, max: 15, has_balloonist: true,
    }],
  }
  const wrapper = mount(SetupControls, { props: { view, connected: true, pending: [] } })
  await wrapper.get('select').setValue('wafu-leiming')
  expect(wrapper.text()).toContain('气球驾驶员规则')
  expect(wrapper.text()).toContain('请选择新版或旧版')
  await click(wrapper, '应用新配置')
  expect(wrapper.emitted('configure')).toBeUndefined()
  await wrapper.get('[data-balloonist-version]').setValue('new')
  await wrapper.get('[data-balloonist-delta]').setValue('0')
  await click(wrapper, '应用新配置')
  expect(wrapper.text()).toContain('新版')
  expect(wrapper.text()).toContain('外来者 +0')
  await click(wrapper, '再次确认并清空座位')
  expect(wrapper.emitted('configure')?.[0]?.[0]).toMatchObject({
    script: 'wafu-leiming', balloonistVersion: 'new', balloonistOutsiderDelta: 0,
  })
})

it('shows Balloonist preview and storyteller-only history before sending', async () => {
  const execute = vi.fn(async () => ({ result: {
    night_no: 2, target_label: '2号', real_type: 'outsider',
    registered_type: 'demon', registration_reason: 'recluse_registration',
    impairments: [], truthful: true,
  } }))
  const wrapper = mount(BalloonistTaskCard, { props: {
    view: {
      balloonist_version: 'new', balloonist_context: { previous_type: 'townsfolk',
        candidates: [{ target: 2, target_label: '2号', real_role: 'recluse',
          real_type: 'outsider', allowed_types: ['outsider', 'minion', 'demon'] }] },
      roles: [{ id: 'imp', name: '小恶魔', team: 'demon' }],
      balloonist_history: [],
    },
    step: { id: 'night:2:balloonist', actor_seat: 1 },
    connected: true, pending: [], execute,
  } })
  await wrapper.get('[data-balloonist-target]').setValue('2')
  await wrapper.get('[data-balloonist-registration]').setValue('demon')
  await wrapper.get('[data-balloonist-role]').setValue('imp')
  await click(wrapper, '确认预览')
  expect(wrapper.text()).toContain('真实类型')
  expect(wrapper.text()).toContain('登记类型')
  await click(wrapper, '发送给玩家')
  expect(execute.mock.calls.map(([payload]) => payload.action)).toEqual(['preview', 'send'])
})

it('shows only a player’s sent targets and retraction notice', () => {
  usePlayerView.mockReturnValue({
    view: shallowRef(makeNightPlayerView('step-1', { balloonist_history: [
      { night_no: 1, target: 2, target_label: '2号', retracted: true },
      { night_no: 2, target: 't1', target_label: '旅行者 阿青（t1）', retracted: false },
    ] })),
    connectionStatus: ref('connected'),
  })
  const wrapper = mount(PlayerPage, { props: { playerId: 'p1' } })
  expect(wrapper.text()).toContain('第 1 夜：2号')
  expect(wrapper.text()).toContain('已撤回')
  expect(wrapper.text()).toContain('第 2 夜：旅行者 阿青（t1）')
  expect(wrapper.text()).not.toContain('登记类型')
})
