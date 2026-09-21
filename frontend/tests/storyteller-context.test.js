import { mount } from '@vue/test-utils'
import { nextTick, ref, shallowRef } from 'vue'
import { beforeEach, expect, it, vi } from 'vitest'
import ContextPanel from '../src/components/storyteller/ContextPanel.vue'
import StorytellerLiveView from '../src/components/storyteller/StorytellerLiveView.vue'
import { lobbyView } from './fixtures/storytellerView.js'

let liveView

vi.mock('../src/composables/useStorytellerView.js', () => ({
  useStorytellerView: vi.fn(() => ({
    view: liveView,
    connectionStatus: ref('connected'),
  })),
}))

beforeEach(() => {
  liveView = shallowRef(lobbyView)
})

function nightView(currentStepId = 's1') {
  const first = {
    id: 's1', actor_seat: 1, character_id: 'imp', name: '小恶魔',
    status: currentStepId === 's1' ? 'current' : 'completed',
    trigger: 'normal', required_fields: ['targets'], source: { ability_character: 'imp' },
  }
  const second = {
    id: 's2', actor_seat: 2, character_id: 'snakecharmer', name: '舞蛇人',
    status: currentStepId === 's2' ? 'current' : 'upcoming',
    trigger: 'normal', required_fields: ['targets'], source: { ability_character: 'snakecharmer' },
  }
  return {
    ...lobbyView,
    status: 'playing', phase: 'night', night_no: 2,
    roles: [...lobbyView.roles, { id: 'snakecharmer', name: '舞蛇人', team: 'townsfolk', selection: { players: 1 } }],
    night_workflow: {
      night_no: 2, current_step_id: currentStepId,
      steps: [first, second], current_task: currentStepId === 's1' ? first : second,
      outcomes: { pending: [] }, information: { drafts: [], notices: [] },
      effects: { history: [] }, transformations: { pending: [] }, undo_previews: [],
      context: { lunatic_choices: [] }, seat_context: [{ seat: 1 }, { seat: 2 }],
    },
  }
}

it('shows join information when no player is selected', () => {
  const wrapper = mount(ContextPanel, { props: { view: lobbyView, selectedSeat: null } })
  expect(wrapper.text()).toContain('2468')
  expect(wrapper.text()).toContain('已入座 2/6')
  expect(wrapper.get('img').attributes('src')).toBe('/api/qr?mode=local&room=2468')
})

it('updates the storyteller shell theme when the live phase changes', async () => {
  liveView = shallowRef(nightView())
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  expect(wrapper.get('.storyteller-shell').attributes('data-phase')).toBe('night')

  liveView.value = { ...lobbyView, status: 'playing', phase: 'day', day_no: 2, day_stage: 'talk' }
  await nextTick()
  expect(wrapper.get('.storyteller-shell').attributes('data-phase')).toBe('day')
})

it('prioritizes selected-player details and can clear the selection', async () => {
  const view = {
    ...lobbyView,
    seats: lobbyView.seats.map((seat) => seat.seat === 1
      ? { ...seat, markers: ['poisoned'], player: { ...seat.player, alive: false } }
      : seat),
  }
  const wrapper = mount(ContextPanel, { props: { view, selectedSeat: 1 } })

  expect(wrapper.text()).toContain('阿青')
  expect(wrapper.text()).toContain('洗衣妇')
  expect(wrapper.text()).toContain('镇民')
  expect(wrapper.text()).toContain('死亡')
  expect(wrapper.text()).toContain('中毒')
  expect(wrapper.find('img').exists()).toBe(false)
  await wrapper.get('[data-clear-selection]').trigger('click')
  expect(wrapper.emitted('clear-selection')).toEqual([[]])
})

it('drops stale selected-player details after a server update removes that player', async () => {
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('[data-seat="1"]').trigger('click')
  expect(wrapper.text()).toContain('洗衣妇')

  liveView.value = {
    ...lobbyView,
    seats: lobbyView.seats.map((seat) => seat.seat === 1 ? { ...seat, player: null } : seat),
  }
  await nextTick()

  expect(wrapper.text()).toContain('玩家加入')
  expect(wrapper.text()).not.toContain('洗衣妇')
})

it('opens the corresponding read-only operation page when inspecting another night step', async () => {
  liveView = shallowRef(nightView())
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('[data-open-session]').trigger('click')
  await wrapper.findAll('.night-step')[1].trigger('click')

  expect(wrapper.get('[data-night-task]').text()).toContain('舞蛇人')
  expect(wrapper.get('[data-night-task]').text()).toContain('查看记录')
  expect(wrapper.get('[data-night-task]').find('.task-submit').exists()).toBe(false)
})

it('switches the right panel back to the newly current operation after night progress changes', async () => {
  liveView = shallowRef(nightView())
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('[data-open-session]').trigger('click')

  liveView.value = nightView('s2')
  await nextTick()

  expect(wrapper.get('[data-night-task]').text()).toContain('舞蛇人')
  expect(wrapper.get('[data-night-task]').text()).toContain('当前任务')
  expect(wrapper.get('[data-night-task]').find('.task-submit').exists()).toBe(true)
})

it('returns from a future-step preview to the actual current task through the header', async () => {
  liveView = shallowRef(nightView())
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.findAll('.night-step')[1].trigger('click')
  expect(wrapper.get('[data-night-task]').text()).toContain('查看记录')

  await wrapper.get('.drawer-toggle-right').trigger('click')

  expect(wrapper.get('[data-night-task]').text()).toContain('小恶魔')
  expect(wrapper.get('[data-night-task]').text()).toContain('当前任务')
})
