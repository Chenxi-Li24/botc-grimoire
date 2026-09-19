import { computed, ref, watch } from 'vue'
import { manualAssignmentPayload, manualAssignmentSummary } from '../presentation/manualAssignment.js'

const projectionSignature = (view) => `${view?.status || ''}:${view?.script || ''}:${view?.player_count || ''}`

export function useManualAssignment(viewRef) {
  const active = ref(false)
  const assignments = ref({})
  const bluffs = ref([])
  const fakes = ref({})
  const lunaticMinions = ref({})
  const lunaticBluffs = ref({})
  const godfatherAdjustment = ref(1)
  let sourceSignature = null

  const snapshot = computed(() => ({
    assignments: assignments.value,
    bluffs: bluffs.value,
    fakes: fakes.value,
    lunaticMinions: lunaticMinions.value,
    lunaticBluffs: lunaticBluffs.value,
    godfatherAdjustment: godfatherAdjustment.value,
  }))
  const summary = computed(() => manualAssignmentSummary(viewRef.value, snapshot.value))
  const payload = computed(() => manualAssignmentPayload(snapshot.value))

  function clear() {
    active.value = false
    assignments.value = {}
    bluffs.value = []
    fakes.value = {}
    lunaticMinions.value = {}
    lunaticBluffs.value = {}
    godfatherAdjustment.value = 1
    sourceSignature = null
  }

  function begin(view) {
    const nextAssignments = { ...(view.seat_roles || {}) }
    ;(view.seats || []).forEach((seat) => {
      const roleId = seat.player?.role?.id || seat.assigned_role?.id
      if (roleId) nextAssignments[seat.seat] = roleId
    })
    assignments.value = nextAssignments
    bluffs.value = (view.bluffs || []).map((role) => role.id)
    const nextFakes = {}
    ;(view.seats || []).forEach((seat) => {
      if (seat.fake_role?.id) nextFakes[seat.seat] = seat.fake_role.id
    })
    fakes.value = nextFakes
    lunaticMinions.value = Object.fromEntries(Object.entries(view.lunatic_minions || {})
      .map(([seat, values]) => [seat, [...values]]))
    lunaticBluffs.value = Object.fromEntries(Object.entries(view.lunatic_bluffs || {})
      .map(([seat, values]) => [seat, values.map((role) => role.id || role)]))
    godfatherAdjustment.value = 1
    sourceSignature = projectionSignature(view)
    active.value = true
  }

  function toggleRole(seat, roleId) {
    const key = String(seat)
    const next = { ...assignments.value }
    if (next[key] === roleId) delete next[key]
    else next[key] = roleId
    assignments.value = next
    bluffs.value = bluffs.value.filter((id) => !Object.values(next).includes(id))
    const nextFakes = { ...fakes.value }; delete nextFakes[key]; fakes.value = nextFakes
    const nextMinions = { ...lunaticMinions.value }; delete nextMinions[key]; lunaticMinions.value = nextMinions
    const nextLunaticBluffs = { ...lunaticBluffs.value }; delete nextLunaticBluffs[key]; lunaticBluffs.value = nextLunaticBluffs
  }

  function setBluff(roleId) {
    bluffs.value = bluffs.value.includes(roleId)
      ? bluffs.value.filter((id) => id !== roleId)
      : (bluffs.value.length < 3 ? [...bluffs.value, roleId] : bluffs.value)
  }

  function setFake(seat, roleId) {
    const key = String(seat)
    fakes.value = { ...fakes.value, [key]: fakes.value[key] === roleId ? '' : roleId }
  }

  function setLunaticMinion(seat, targetSeat) {
    const key = String(seat)
    const current = lunaticMinions.value[key] || []
    lunaticMinions.value = {
      ...lunaticMinions.value,
      [key]: current.includes(targetSeat)
        ? current.filter((value) => value !== targetSeat)
        : [...current, targetSeat],
    }
  }

  function setLunaticBluff(seat, roleId) {
    const key = String(seat)
    const current = lunaticBluffs.value[key] || []
    lunaticBluffs.value = {
      ...lunaticBluffs.value,
      [key]: current.includes(roleId)
        ? current.filter((value) => value !== roleId)
        : (current.length < 3 ? [...current, roleId] : current),
    }
  }

  function cancel() { clear() }
  function invalidate() { clear() }
  function setGodfatherAdjustment(value) { godfatherAdjustment.value = value }

  watch(() => projectionSignature(viewRef.value), (signature) => {
    if (active.value && signature !== sourceSignature) invalidate()
  })

  return {
    active,
    assignments,
    bluffs,
    fakes,
    lunaticMinions,
    lunaticBluffs,
    godfatherAdjustment,
    summary,
    payload,
    begin,
    toggleRole,
    setBluff,
    setFake,
    setLunaticMinion,
    setLunaticBluff,
    setGodfatherAdjustment,
    cancel,
    invalidate,
  }
}
