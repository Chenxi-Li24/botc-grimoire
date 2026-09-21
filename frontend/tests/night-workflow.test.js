import { nextTick, shallowRef } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import { useNightWorkflow } from '../src/composables/useNightWorkflow.js'

function workflowView(overrides = {}) {
  return {
    night_workflow: {
      current_step_id: 's1',
      steps: [{ id: 's1', actor_seat: 1, status: 'current' }],
      current_task: { id: 's1', actor_seat: 1, status: 'current' },
      information: { drafts: [] },
      outcomes: { pending: [] },
      seat_context: [{ seat: 1 }],
      ...overrides,
    },
  }
}

describe('night workflow state', () => {
  it('arms force continuation with exact omissions and reuses the token', async () => {
    const view = shallowRef(workflowView())
    const navigate = vi.fn().mockResolvedValue({
      result: {
        blocked: true,
        current_step_id: 's1',
        force_token: 'force-1',
        omissions: ['targets', 'outcome:o1'],
      },
    })
    const run = vi.fn((_key, operation) => operation())
    const workflow = useNightWorkflow(view, { service: { navigate }, run })

    await workflow.navigate({ direction: 'next', step_id: 's1' })
    expect(workflow.forceTokens.value.s1).toBe('force-1')
    expect(workflow.forceOmissions.value.s1).toEqual(['targets', 'outcome:o1'])
  })

  it('keeps unfinished per-step drafts across projection refreshes', async () => {
    const view = shallowRef(workflowView())
    const workflow = useNightWorkflow(view, {
      service: {}, run: vi.fn((_key, operation) => operation()),
    })
    workflow.toggleTarget(2, 's1')
    workflow.setSelectedCharacter('chef', 's1')
    view.value = workflowView({ night_no: 2 })
    await nextTick()
    expect(workflow.targetDrafts.value.s1).toEqual([2])
    expect(workflow.characterDrafts.value.s1).toBe('chef')
  })

  it('hydrates a storyteller draft from canonical values submitted by a player', async () => {
    const view = shallowRef(workflowView())
    const workflow = useNightWorkflow(view, {
      service: {}, run: vi.fn((_key, operation) => operation()),
    })

    const submitted = {
      id: 's1', actor_seat: 1, status: 'current',
      values: { targets: [2], character: 'chef' },
    }
    view.value = workflowView({ steps: [submitted], current_task: submitted })
    await nextTick()

    expect(workflow.targetDrafts.value.s1).toEqual([2])
    expect(workflow.characterDrafts.value.s1).toBe('chef')
  })

  it('follows the newly current step instead of leaving a previously inspected step open', async () => {
    const first = { id: 's1', actor_seat: 1, status: 'current' }
    const second = { id: 's2', actor_seat: 2, status: 'upcoming' }
    const third = { id: 's3', actor_seat: 3, status: 'upcoming' }
    const view = shallowRef(workflowView({
      steps: [first, second, third], current_task: first,
      seat_context: [{ seat: 1 }, { seat: 2 }, { seat: 3 }],
    }))
    const workflow = useNightWorkflow(view, {
      service: {}, run: vi.fn((_key, operation) => operation()),
    })
    workflow.setInspectedStep('s3')
    workflow.setSelectedSeat(3)

    view.value = workflowView({
      current_step_id: 's2',
      steps: [{ ...first, status: 'completed' }, { ...second, status: 'current' }, third],
      current_task: { ...second, status: 'current' },
      seat_context: [{ seat: 1 }, { seat: 2 }, { seat: 3 }],
    })
    await nextTick()

    expect(workflow.inspectedStep.value.id).toBe('s2')
    expect(workflow.selectedSeat.value).toBeNull()
  })

  it('attaches the root event to an undo dependency preview', async () => {
    const view = shallowRef(workflowView())
    const service = { undoNightEvent: vi.fn().mockResolvedValue({ result: { event_ids: ['e1', 'e2'] } }) }
    const workflow = useNightWorkflow(view, {
      service, run: vi.fn((_key, operation) => operation()),
    })
    await workflow.undoNightEvent({ event_id: 'e1', confirm: false })
    expect(workflow.undoPreview.value).toEqual({
      event_ids: ['e1', 'e2'], root_event_id: 'e1',
    })
  })

  it('prepares target-free role information automatically on entering the step', async () => {
    const chefStep = {
      id: 'chef-first', actor_seat: 5, character_id: 'chef', status: 'current',
      required_fields: [], source: { ability_character: 'chef' },
    }
    const view = shallowRef({
      roles: [{ id: 'chef', information_resolver: 'chef' }],
      night_workflow: {
        current_step_id: chefStep.id, steps: [chefStep], current_task: chefStep,
        information: { drafts: [], deliveries: [], notices: [] },
        outcomes: { pending: [] }, seat_context: [{ seat: 5 }],
      },
    })
    const service = { deliverInformation: vi.fn().mockResolvedValue({ result: { automatic: true } }) }
    useNightWorkflow(view, {
      service, run: vi.fn((_key, operation) => operation()),
    })

    await vi.waitFor(() => expect(service.deliverInformation).toHaveBeenCalledWith({
      action: 'prepare', step_id: chefStep.id, actor_seat: 5, targets: [],
    }))
  })

  it('leaves Balloonist information to its dedicated preview/send workflow', async () => {
    const balloonistStep = {
      id: 'balloonist-night', actor_seat: 5, character_id: 'balloonist', status: 'current',
      required_fields: [], source: { ability_character: 'balloonist' },
    }
    const view = shallowRef({
      roles: [{ id: 'balloonist', information_resolver: 'balloonist' }],
      night_workflow: {
        current_step_id: balloonistStep.id, steps: [balloonistStep], current_task: balloonistStep,
        information: { drafts: [], deliveries: [], notices: [] },
        outcomes: { pending: [] }, seat_context: [{ seat: 5 }],
      },
    })
    const service = {
      deliverInformation: vi.fn(),
      balloonist: vi.fn().mockResolvedValue({ result: { target: 2 } }),
    }
    const state = useNightWorkflow(view, {
      service, run: vi.fn((_key, operation) => operation()),
    })
    await nextTick()
    expect(service.deliverInformation).not.toHaveBeenCalled()
    await expect(state.balloonist({ action: 'preview', step_id: balloonistStep.id, target: 2 }))
      .resolves.toEqual({ result: { target: 2 } })
    expect(service.balloonist).toHaveBeenCalledWith({ action: 'preview', step_id: balloonistStep.id, target: 2 })
  })
})
