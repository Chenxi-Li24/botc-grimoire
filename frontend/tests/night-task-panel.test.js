import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import GameControlPanel from '../src/components/storyteller/GameControlPanel.vue'
import NightNavigation from '../src/components/storyteller/night/NightNavigation.vue'
import NightTaskPanel from '../src/components/storyteller/night/NightTaskPanel.vue'
import SeatTargetPicker from '../src/components/storyteller/night/SeatTargetPicker.vue'

const roles = [
  { id: 'imp', name: '小恶魔', team: 'demon', selection: { players: 1, allow_self: true } },
  { id: 'chef', name: '厨师', team: 'townsfolk', information_resolver: 'chef' },
  { id: 'lunatic', name: '疯子', team: 'outsider', selection: { players: 1, allow_self: true } },
  { id: 'snakecharmer', name: '舞蛇人', team: 'townsfolk', selection: { players: 1, alive_only: true } },
  { id: 'balloonist', name: '气球驾驶员', team: 'townsfolk', information_resolver: 'balloonist' },
]
const step = {
  id: 's1', actor_seat: 1, character_id: 'imp', name: '小恶魔',
  status: 'current', trigger: 'normal', reminder: '选择一名玩家。',
  required_fields: ['targets'], source: { ability_character: 'imp', claimed_by: null },
}

function night(overrides = {}) {
  return {
    workflow: {
      night_no: 2, current_step_id: 's1', steps: [step], current_task: step,
      outcomes: { pending: [] }, information: { drafts: [], notices: [] },
      effects: { history: [] }, transformations: { pending: [] }, undo_previews: [],
      context: { lunatic_choices: [] },
    },
    orderedSteps: [step], currentTask: step, inspectedStep: step, inspectedStepId: 's1',
    selectedSeat: null, selectedTargets: [], selectedCharacter: null,
    informationClaims: {}, informationResults: {}, outcomeChoices: {},
    forceTokens: {}, forceOmissions: {}, undoPreview: null,
    setSelectedSeat: vi.fn(), toggleTarget: vi.fn(), setSelectedCharacter: vi.fn(),
    setInformationClaims: vi.fn(), setInformationResult: vi.fn(), setOutcomeChoice: vi.fn(),
    inspectCurrentTask: vi.fn(), navigate: vi.fn(), selectNightTargets: vi.fn(),
    resolveOutcome: vi.fn(), deliverInformation: vi.fn(), applyNightEffect: vi.fn(),
    confirmPitHag: vi.fn(), undoNightEvent: vi.fn(), clearUndoPreview: vi.fn(),
    ...overrides,
  }
}

const view = {
  roles,
  seats: [
    { seat: 1, player: null, assigned_role: roles[0], alive: true },
    { seat: 2, player: null, assigned_role: roles[1], alive: true },
  ],
}

describe('fixed night workspace', () => {
  it('keeps night navigation below the left step list and emits the existing navigation payload', async () => {
    const state = night({ forceTokens: { s1: 'force-1' } })
    const controls = mount(GameControlPanel, {
      props: {
        view: { ...view, status: 'playing', phase: 'night', script: '暗流涌动' },
        night: state, connected: true, pending: [],
      },
    })
    const task = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })

    expect(controls.find('[data-night-navigation]').exists()).toBe(true)
    expect(task.find('[data-night-navigation]').exists()).toBe(false)
    await controls.get('[data-night-next]').trigger('click')
    expect(controls.emitted('navigate-night')).toEqual([[
      { direction: 'next', step_id: 's1', force_token: 'force-1' },
    ]])
  })

  it('keeps previous and next in stable slots and changes next to dawn', () => {
    const wrapper = mount(NightNavigation, {
      props: { steps: [step], currentStep: { ...step, character_id: 'dawn' }, connected: true },
    })
    expect(wrapper.get('[data-night-previous]').attributes('data-slot')).toBe('left')
    expect(wrapper.get('[data-night-next]').attributes('data-slot')).toBe('right')
    expect(wrapper.get('[data-night-next]').text()).toContain('天亮')
  })

  it('renders exact omissions and arms only the right action', () => {
    const state = night({
      forceTokens: { s1: 'force-1' },
      forceOmissions: { s1: ['targets'] },
    })
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })
    const controls = mount(GameControlPanel, {
      props: {
        view: { ...view, status: 'playing', phase: 'night', script: '暗流涌动' },
        night: state, connected: true, pending: [],
      },
    })
    expect(wrapper.text()).toContain('尚未选择玩家')
    expect(controls.get('[data-night-next]').text()).toContain('仍然继续')
    expect(controls.get('[data-night-previous]').text()).toContain('上一步')
  })

  it('lets the storyteller select an assigned but unclaimed seat', async () => {
    const wrapper = mount(SeatTargetPicker, {
      props: { seats: view.seats, roles, selected: [], actorSeat: 1, selection: { players: 1 } },
    })
    expect(wrapper.text()).toContain('线下/未领取')
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('toggle')).toEqual([[2]])
  })

  it('treats the first-night lunatic as an acknowledgement step, not a kill choice', async () => {
    const lunaticStep = {
      ...step,
      id: 'lunatic-first', actor_seat: 2, character_id: 'lunatic', name: '疯子',
      trigger: 'first-night', required_fields: ['acknowledged'],
      source: { ability_character: 'lunatic', claimed_by: null },
    }
    const state = night({
      workflow: {
        ...night().workflow,
        current_step_id: lunaticStep.id,
        steps: [lunaticStep],
        current_task: lunaticStep,
      },
      orderedSteps: [lunaticStep], currentTask: lunaticStep,
      inspectedStep: lunaticStep, inspectedStepId: lunaticStep.id,
    })
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })

    expect(wrapper.text()).not.toContain('选择玩家')
    await wrapper.get('.task-submit').trigger('click')
    expect(state.selectNightTargets).toHaveBeenCalledWith(expect.objectContaining({
      step_id: lunaticStep.id,
      selected_seats: [],
      create_outcome: false,
      acknowledged: true,
    }))
  })

  it('shows the exact automatically sent information as a notice', () => {
    const chefStep = {
      ...step,
      id: 'chef-first', actor_seat: 2, character_id: 'chef', name: '厨师',
      trigger: 'start-knowing', required_fields: [], values: { targets: [] },
      source: { ability_character: 'chef', claimed_by: null },
    }
    const state = night({
      workflow: {
        ...night().workflow,
        current_step_id: chefStep.id,
        steps: [chefStep],
        current_task: chefStep,
      },
      orderedSteps: [chefStep], currentTask: chefStep,
      inspectedStep: chefStep, inspectedStepId: chefStep.id,
    })
    state.workflow.information.notices = [{
      id: 'notice-1', kind: 'automatic_information_sent', actor_seat: 2, payload: 2,
    }]
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })

    expect(wrapper.text()).toContain('已自动发送给 2号：2')
    expect(wrapper.find('.task-submit').exists()).toBe(false)
  })

  it('uses only the dedicated Balloonist card for the current step', () => {
    const balloonistStep = {
      ...step, id: 'balloonist-1', actor_seat: 2, character_id: 'balloonist',
      source: { ability_character: 'balloonist', claimed_by: null },
      required_fields: ['targets'],
    }
    const state = night({
      workflow: {
        ...night().workflow, current_step_id: balloonistStep.id,
        steps: [balloonistStep], current_task: balloonistStep,
      },
      currentTask: balloonistStep, inspectedStep: balloonistStep,
    })
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })
    expect(wrapper.find('.task-submit').exists()).toBe(false)
    expect(wrapper.findComponent(SeatTargetPicker).exists()).toBe(false)
    expect(wrapper.find('[data-balloonist-card]').exists()).toBe(true)
  })

  it('shows live poisoned actor and source in the operation panel', () => {
    const chefStep = {
      ...step, id: 'chef-live', actor_seat: 2, character_id: 'chef',
      source: { ability_character: 'chef', claimed_by: null },
    }
    const state = night({
      workflow: {
        ...night().workflow, current_step_id: chefStep.id,
        steps: [chefStep], current_task: chefStep,
        effects: { current: [{ id: 'e1', type: 'poisoned', target_seat: 2,
          source_seat: 1, source_character: 'poisoner', started_at: '2026-09-22T00:00:00Z',
          expected_end: 'next_dusk' }], history: [] },
      },
      currentTask: chefStep, inspectedStep: chefStep,
    })
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })
    expect(wrapper.get('[data-actor-impairment]').text()).toContain('中毒')
    expect(wrapper.get('[data-actor-impairment]').text()).toContain('1号')
    expect(wrapper.get('[data-actor-impairment]').text()).toContain('发送信息前')
  })

  it('requires truth marking when an actor becomes poisoned after a clean draft', () => {
    const chefStep = { ...step, actor_seat: 2, character_id: 'chef',
      source: { ability_character: 'chef', claimed_by: null } }
    const state = night({
      workflow: {
        ...night().workflow, current_task: chefStep,
        information: { drafts: [{ id: 'd1', actor_seat: 2, resolver_key: 'chef',
          true_result: 0, legal_results: [0], reason: null, effect_snapshot: [] }], notices: [] },
        effects: { current: [{ id: 'e1', type: 'poisoned', target_seat: 2,
          source_seat: 1, state: 'active' }], history: [] },
      },
      currentTask: chefStep, inspectedStep: chefStep,
    })
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })
    expect(wrapper.text()).toContain('必须至少标记一条真假记录')
    expect(wrapper.find('.information-editor .btn.primary').attributes('disabled')).toBeDefined()
  })

  it('does not offer a second outcome after the current choice was resolved', () => {
    const resolvedStep = { ...step, values: { targets: [2] } }
    const state = night({
      workflow: {
        ...night().workflow,
        steps: [resolvedStep], current_task: resolvedStep,
        outcomes: { pending: [], history: [{ id: 'o1', status: 'resolved' }] },
      },
      orderedSteps: [resolvedStep], currentTask: resolvedStep, inspectedStep: resolvedStep,
    })
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })

    expect(wrapper.find('.task-submit').exists()).toBe(false)
    expect(wrapper.find('.target-picker').exists()).toBe(false)
  })

  it('shows the recorded choice on the current snake charmer operation page', () => {
    const snakeStep = {
      ...step, character_id: 'snakecharmer', name: '舞蛇人',
      source: { ability_character: 'snakecharmer', claimed_by: 'player-1' },
      values: { targets: [2] },
    }
    const state = night({
      workflow: {
        ...night().workflow,
        steps: [snakeStep], current_task: snakeStep,
      },
      orderedSteps: [snakeStep], currentTask: snakeStep, inspectedStep: snakeStep,
      selectedTargets: [2],
    })
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })

    expect(wrapper.get('[data-night-recorded-choice]').text()).toContain('2号')
    expect(wrapper.find('.task-submit').exists()).toBe(false)
    expect(wrapper.find('.target-picker').exists()).toBe(false)
  })

  it('lets the storyteller submit the current snake charmer choice when none is recorded', async () => {
    const snakeStep = {
      ...step, character_id: 'snakecharmer', name: '舞蛇人',
      source: { ability_character: 'snakecharmer', claimed_by: null },
    }
    const state = night({
      workflow: { ...night().workflow, steps: [snakeStep], current_task: snakeStep },
      orderedSteps: [snakeStep], currentTask: snakeStep, inspectedStep: snakeStep,
      selectedTargets: [2],
    })
    const wrapper = mount(NightTaskPanel, {
      props: { view, night: state, connected: true, pending: [] },
    })

    expect(wrapper.find('.target-picker').exists()).toBe(true)
    await wrapper.get('.task-submit').trigger('click')
    expect(state.selectNightTargets).toHaveBeenCalledWith(expect.objectContaining({
      step_id: snakeStep.id, selected_seats: [2],
    }))
  })
})
