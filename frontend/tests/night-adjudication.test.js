import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import InformationEditor from '../src/components/storyteller/night/InformationEditor.vue'
import OutcomeAdjudicator from '../src/components/storyteller/night/OutcomeAdjudicator.vue'
import PitHagCard from '../src/components/storyteller/night/PitHagCard.vue'
import UndoPreview from '../src/components/storyteller/night/UndoPreview.vue'

describe('night adjudication controls', () => {
  it('emits a confidential outcome decision with its rationale', async () => {
    const outcome = {
      id: 'o1', source_character: 'imp', selected_seats: [2], hints: [],
    }
    const wrapper = mount(OutcomeAdjudicator, {
      props: {
        outcomes: [outcome],
        choices: { o1: { resolution: 'secret_death', affected_seats: [2], rationale: '恶魔攻击' } },
        connected: true,
        pending: [],
      },
    })
    await wrapper.get('button.btn.primary').trigger('click')
    expect(wrapper.emitted('resolve')[0][0]).toMatchObject({
      outcome_id: 'o1', resolution: 'secret_death', affected_seats: [2], rationale: '恶魔攻击',
    })
  })

  it('does not send affected seats for a lunatic choice-only record', async () => {
    const outcome = {
      id: 'o-lunatic', source_character: 'lunatic', selected_seats: [4], hints: [],
    }
    const wrapper = mount(OutcomeAdjudicator, {
      props: { outcomes: [outcome], choices: {}, connected: true, pending: [] },
    })

    await wrapper.get('button.btn.primary').trigger('click')

    expect(wrapper.emitted('resolve')[0][0]).toMatchObject({
      outcome_id: 'o-lunatic', resolution: 'choice_only', affected_seats: [],
    })
  })

  it('requires truth annotations before sending impaired information', async () => {
    const draft = {
      id: 'd1', actor_seat: 2, true_result: 1, legal_results: [0, 1],
      reason: 'poisoned', effect_snapshot: ['effect-1'],
    }
    const wrapper = mount(InformationEditor, {
      props: { drafts: [draft], results: {}, claims: {}, connected: true, pending: [] },
    })
    expect(wrapper.text()).toContain('异常状态')
    expect(wrapper.get('button.btn.primary').attributes('disabled')).toBeDefined()
    await wrapper.get('.claim-editor .chip-button').trigger('click')
    expect(wrapper.emitted('set-claims')[0][0].claims[0]).toMatchObject({ truthful: true })
  })

  it('offers Dreamer a good/evil pair and lets the backend derive the true claim', async () => {
    const draft = {
      id: 'dreamer-1', actor_seat: 4, resolver_key: 'dreamer',
      true_result: { target: 1, character_id: 'imp', alignment: 'evil' },
      legal_results: [{ target: 1, good_character: 'chef', evil_character: 'imp' }],
      reason: 'storyteller_discretion', effect_snapshot: [],
    }
    const wrapper = mount(InformationEditor, {
      props: {
        drafts: [draft], results: {}, claims: {}, connected: true, pending: [],
        roles: [{ id: 'chef', name: '厨师' }, { id: 'imp', name: '小恶魔' }],
      },
    })

    expect(wrapper.text()).toContain('厨师 / 小恶魔')
    expect(wrapper.text()).toContain('正确：小恶魔')
    expect(wrapper.get('button.btn.primary').attributes('disabled')).toBeUndefined()
    await wrapper.get('button.btn.primary').trigger('click')
    expect(wrapper.emitted('deliver')[0][0]).toMatchObject({
      delivered_result: { target: 1, good_character: 'chef', evil_character: 'imp' },
      claims: undefined,
    })
  })

  it('previews the full dependency set before confirming undo', async () => {
    const selected = {
      root_event_id: 'e1', event_ids: ['e1', 'e2'],
      events: [{ id: 'e1', kind: 'selection' }, { id: 'e2', kind: 'message' }],
      retractions: ['message-1'],
    }
    const wrapper = mount(UndoPreview, {
      props: { selected, connected: true, pending: [] },
    })
    expect(wrapper.text()).toContain('2 条关联记录')
    expect(wrapper.text()).toContain('撤回 1 条')
    await wrapper.get('button.btn.danger').trigger('click')
    expect(wrapper.emitted('confirm')).toEqual([['e1']])
  })

  it('renders the Pit-Hag preview with localized timing and character names', () => {
    const wrapper = mount(PitHagCard, {
      props: {
        step: { id: 'p1', actor_seat: 2 }, targetSeat: 7, characterId: 'grandmother',
        roles: [{ id: 'savant', name: '博学者' }, { id: 'grandmother', name: '祖母' }],
        preview: {
          id: 'preview-1', target_seat: 7, old_character: 'savant',
          new_character: 'grandmother', alignment: 'good',
          relative_order: 'immediate_start_knowing', warnings: [], demon_consequences: [],
        },
        connected: true, pending: [],
      },
    })

    expect(wrapper.text()).toContain('博学者 → 祖母')
    expect(wrapper.text()).toContain('善良（保持）')
    expect(wrapper.text()).toContain('立即补发首夜信息')
  })
})
