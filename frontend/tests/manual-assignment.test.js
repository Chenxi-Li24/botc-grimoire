import { nextTick, shallowRef } from 'vue'
import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { useManualAssignment } from '../src/composables/useManualAssignment.js'
import BluffPicker from '../src/components/storyteller/BluffPicker.vue'
import RolePicker from '../src/components/storyteller/RolePicker.vue'
import {
  eligibleBluffRoles,
  expectedComposition,
  manualAssignmentPayload,
  manualAssignmentSummary,
} from '../src/presentation/manualAssignment.js'
import { lobbyView } from './fixtures/storytellerView.js'

const validDraft = {
  assignments: {
    1: 'washerwoman', 2: 'librarian', 3: 'investigator',
    4: 'drunk', 5: 'poisoner', 6: 'imp',
  },
  bluffs: [],
  fakes: { 4: 'washerwoman' },
  lunaticMinions: {},
  lunaticBluffs: {},
  godfatherAdjustment: 1,
}

it('calculates script, Godfather, and Sentinel composition adjustments', () => {
  expect(expectedComposition(lobbyView, { 1: 'godfather' }, 1)).toEqual([2, 2, 1, 1])
  expect(expectedComposition({ ...lobbyView, sentinel: -1 }, {}, 1)).toEqual([4, 0, 1, 1])
  expect(expectedComposition(lobbyView, { 1: 'godfather' }, -1)).toEqual([4, 0, 1, 1])
})

it('keeps composition differences as warnings while enforcing hard role rules', () => {
  const view = { ...lobbyView, roles: [...lobbyView.roles,
    { id: 'extra-town', name: '额外镇民', team: 'townsfolk' },
    { id: 'bluff-a', name: '伪装甲', team: 'townsfolk' },
    { id: 'bluff-b', name: '伪装乙', team: 'townsfolk' },
    { id: 'bluff-c', name: '伪装丙', team: 'townsfolk' }] }
  const draft = {
    ...validDraft,
    assignments: { ...validDraft.assignments, 4: 'extra-town' },
    bluffs: ['bluff-a', 'bluff-b', 'bluff-c'],
    fakes: {},
  }
  const summary = manualAssignmentSummary(view, draft)
  expect(summary.warnings).toHaveLength(1)
  expect(summary.hardErrors).toEqual([])
  expect(summary.valid).toBe(true)

  const withoutDemon = manualAssignmentSummary(view, {
    ...draft, assignments: { ...draft.assignments, 6: 'drunk' },
  })
  expect(withoutDemon.hardErrors).toContain('必须且只能有 1 名恶魔')
})

it('rejects duplicates and roles that cannot be demon bluffs', () => {
  const duplicate = { ...validDraft,
    assignments: { ...validDraft.assignments, 2: 'washerwoman' },
    bluffs: ['librarian', 'lunatic', 'godfather'] }
  const summary = manualAssignmentSummary(lobbyView, duplicate)
  expect(summary.hardErrors).toContain('角色不能重复')
  expect(eligibleBluffRoles(lobbyView, validDraft.assignments).map((role) => role.id))
    .not.toContain('poisoner')
})

it('serializes drunk and lunatic knowledge into the existing payload', () => {
  const payload = manualAssignmentPayload({
    ...validDraft,
    assignments: { ...validDraft.assignments, 4: 'lunatic' },
    fakes: { 4: 'imp' },
    lunaticMinions: { 4: [5] },
    lunaticBluffs: { 4: ['washerwoman', 'librarian', 'investigator'] },
  })
  expect(payload.assignments).toHaveLength(6)
  expect(payload.fakes).toEqual([{
    seat: 4, role: 'imp', minions: [5],
    bluffs: ['washerwoman', 'librarian', 'investigator'],
  }])
})

it('reconstructs a draft and invalidates it after configuration changes', async () => {
  const view = shallowRef(lobbyView)
  const manual = useManualAssignment(view)
  manual.begin(lobbyView)
  expect(manual.active.value).toBe(true)
  expect(manual.assignments.value).toMatchObject({ 1: 'washerwoman', 2: 'imp' })

  view.value = { ...lobbyView, player_count: 7 }
  await nextTick()
  expect(manual.active.value).toBe(false)
  expect(manual.assignments.value).toEqual({})
})

it('announces selected roles and bluffs without relying on color', () => {
  const rolePicker = mount(RolePicker, {
    props: { roles: lobbyView.roles, assignments: { 1: 'washerwoman' }, selectedSeat: 1 },
  })
  const bluffPicker = mount(BluffPicker, {
    props: { roles: lobbyView.roles.slice(0, 3), selected: ['washerwoman'], title: '伪装' },
  })

  expect(rolePicker.get('button').attributes('aria-pressed')).toBe('true')
  expect(bluffPicker.get('button').attributes('aria-pressed')).toBe('true')
})
