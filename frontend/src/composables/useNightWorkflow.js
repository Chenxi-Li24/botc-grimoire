import { computed, ref, watch } from 'vue'

const commandKey = (kind, id = 'current') => `night:${kind}:${id}`
const asIdSet = (values, key = 'id') => new Set((values || []).map((item) => item[key]))

export function useNightWorkflow(viewRef, { service, run }) {
  const inspectedStepId = ref(null)
  const selectedSeat = ref(null)
  const targetDrafts = ref({})
  const characterDrafts = ref({})
  const informationClaims = ref({})
  const informationResults = ref({})
  const outcomeChoices = ref({})
  const forceTokens = ref({})
  const forceOmissions = ref({})
  const undoPreview = ref(null)
  const autoPreparedSteps = new Set()

  const workflow = computed(() => viewRef.value?.night_workflow || null)
  const orderedSteps = computed(() => workflow.value?.steps || [])
  const currentTask = computed(() => workflow.value?.current_task || null)
  const inspectedStep = computed(() => {
    const id = inspectedStepId.value || workflow.value?.current_step_id
    return orderedSteps.value.find((step) => step.id === id) || currentTask.value
  })
  const draftStepId = computed(() => inspectedStep.value?.id || currentTask.value?.id || null)
  const selectedTargets = computed(() => targetDrafts.value[draftStepId.value] || [])
  const selectedCharacter = computed(() => characterDrafts.value[draftStepId.value] || null)

  function setInspectedStep(stepId) { inspectedStepId.value = stepId }
  function inspectCurrentTask() { inspectedStepId.value = currentTask.value?.id || null }
  function setSelectedSeat(seat) { selectedSeat.value = seat }

  function toggleTarget(seat, stepId = draftStepId.value) {
    if (!stepId) return
    const current = targetDrafts.value[stepId] || []
    targetDrafts.value = {
      ...targetDrafts.value,
      [stepId]: current.includes(seat)
        ? current.filter((value) => value !== seat)
        : [...current, seat],
    }
  }

  function setTargets(seats, stepId = draftStepId.value) {
    if (!stepId) return
    targetDrafts.value = { ...targetDrafts.value, [stepId]: [...seats] }
  }

  function setSelectedCharacter(characterId, stepId = draftStepId.value) {
    if (!stepId) return
    characterDrafts.value = { ...characterDrafts.value, [stepId]: characterId }
  }

  function setInformationClaims(draftId, claims) {
    informationClaims.value = {
      ...informationClaims.value,
      [draftId]: claims.map((claim) => ({ ...claim })),
    }
  }

  function setInformationResult(draftId, result) {
    informationResults.value = { ...informationResults.value, [draftId]: result }
  }

  function setOutcomeChoice(outcomeId, choice) {
    outcomeChoices.value = { ...outcomeChoices.value, [outcomeId]: { ...choice } }
  }

  async function navigate(payload) {
    const key = commandKey('step', payload.step_id || workflow.value?.current_step_id)
    const response = await run(key, () => service.navigate(payload))
    const result = response?.result
    const stepId = result?.current_step_id || payload.step_id
    if (result?.blocked && result.force_token && stepId) {
      forceTokens.value = { ...forceTokens.value, [stepId]: result.force_token }
      forceOmissions.value = { ...forceOmissions.value, [stepId]: result.omissions || [] }
    } else if (stepId) {
      const next = { ...forceTokens.value }; delete next[stepId]; forceTokens.value = next
      const omissions = { ...forceOmissions.value }; delete omissions[stepId]; forceOmissions.value = omissions
    }
    return response
  }

  const selectNightTargets = (payload) => run(
    commandKey('select', payload.step_id || 'arbitrary'),
    () => service.selectNightTargets(payload),
  )
  const resolveOutcome = (payload) => run(
    commandKey('outcome', payload.outcome_id),
    () => service.resolveOutcome(payload),
  )
  const deliverInformation = (payload) => run(
    commandKey('information', payload.draft_id || payload.delivery_id || payload.actor_seat),
    () => service.deliverInformation(payload),
  )
  const balloonist = (payload) => run(
    commandKey('balloonist', payload.step_id),
    () => service.balloonist(payload),
  )
  const applyNightEffect = (payload) => run(
    commandKey('effect', `${payload.action}:${payload.source_seat}`),
    () => service.applyNightEffect(payload),
  )
  const confirmPitHag = (payload) => run(
    commandKey('pit-hag', payload.preview_id || payload.actor_seat),
    () => service.confirmPitHag(payload),
  )
  async function undoNightEvent(payload) {
    const response = await run(
      commandKey('undo', payload.event_id),
      () => service.undoNightEvent(payload),
    )
    if (response) {
      undoPreview.value = payload.confirm
        ? null
        : { ...response.result, root_event_id: payload.event_id }
    }
    return response
  }

  function clearUndoPreview() { undoPreview.value = null }

  watch([currentTask, () => viewRef.value?.roles], async ([step, roles]) => {
    if (!step || step.status !== 'current' || !step.actor_seat) return
    const required = step.required_fields || []
    if (required.includes('targets') || required.includes('character')) return
    const ability = step.source?.ability_character || step.perceived_as || step.character_id
    if (ability === 'balloonist') return
    const role = (roles || []).find((item) => item.id === ability)
    if (!role?.information_resolver) return
    if (Object.prototype.hasOwnProperty.call(step.values || {}, 'targets')) return
    if (autoPreparedSteps.has(step.id)) return
    autoPreparedSteps.add(step.id)
    const response = await deliverInformation({
      action: 'prepare',
      step_id: step.id,
      actor_seat: step.actor_seat,
      targets: [],
    })
    if (!response) autoPreparedSteps.delete(step.id)
  }, { immediate: true })

  watch(() => workflow.value?.current_step_id, (stepId, previousStepId) => {
    if (!stepId || stepId === previousStepId) return
    inspectedStepId.value = stepId
    selectedSeat.value = null
  })

  watch(workflow, (next) => {
    if (!next) return
    const steps = next.steps || []
    const stepIds = asIdSet(steps)
    const unfinishedStepIds = new Set(steps
      .filter((step) => ['current', 'upcoming'].includes(step.status))
      .map((step) => step.id))
    const pendingDraftIds = asIdSet(next.information?.drafts)
    const pendingOutcomeIds = asIdSet(next.outcomes?.pending)
    const seatIds = new Set((next.seat_context || []).map((seat) => seat.seat))

    const nextTargetDrafts = Object.fromEntries(Object.entries(targetDrafts.value)
      .filter(([id]) => unfinishedStepIds.has(id)))
    const nextCharacterDrafts = Object.fromEntries(Object.entries(characterDrafts.value)
      .filter(([id]) => unfinishedStepIds.has(id)))
    for (const step of steps) {
      if (!unfinishedStepIds.has(step.id)) continue
      if (Object.prototype.hasOwnProperty.call(step.values || {}, 'targets')) {
        nextTargetDrafts[step.id] = [...(step.values.targets || [])]
      }
      if (Object.prototype.hasOwnProperty.call(step.values || {}, 'character')) {
        nextCharacterDrafts[step.id] = step.values.character || null
      }
    }
    targetDrafts.value = nextTargetDrafts
    characterDrafts.value = nextCharacterDrafts
    informationClaims.value = Object.fromEntries(Object.entries(informationClaims.value)
      .filter(([id]) => pendingDraftIds.has(id)))
    informationResults.value = Object.fromEntries(Object.entries(informationResults.value)
      .filter(([id]) => pendingDraftIds.has(id)))
    outcomeChoices.value = Object.fromEntries(Object.entries(outcomeChoices.value)
      .filter(([id]) => pendingOutcomeIds.has(id)))
    forceTokens.value = Object.fromEntries(Object.entries(forceTokens.value)
      .filter(([id]) => unfinishedStepIds.has(id)))
    forceOmissions.value = Object.fromEntries(Object.entries(forceOmissions.value)
      .filter(([id]) => unfinishedStepIds.has(id)))

    if (inspectedStepId.value && !stepIds.has(inspectedStepId.value)) {
      inspectedStepId.value = next.current_step_id || null
    }
    if (selectedSeat.value !== null && !seatIds.has(selectedSeat.value)) {
      selectedSeat.value = null
    }
  }, { deep: false })

  return {
    workflow,
    orderedSteps,
    currentTask,
    inspectedStep,
    inspectedStepId,
    selectedSeat,
    selectedTargets,
    selectedCharacter,
    targetDrafts,
    characterDrafts,
    informationClaims,
    informationResults,
    outcomeChoices,
    forceTokens,
    forceOmissions,
    undoPreview,
    setInspectedStep,
    inspectCurrentTask,
    setSelectedSeat,
    toggleTarget,
    setTargets,
    setSelectedCharacter,
    setInformationClaims,
    setInformationResult,
    setOutcomeChoice,
    navigate,
    selectNightTargets,
    resolveOutcome,
    deliverInformation,
    balloonist,
    applyNightEffect,
    confirmPitHag,
    undoNightEvent,
    clearUndoPreview,
    commandKey,
  }
}
