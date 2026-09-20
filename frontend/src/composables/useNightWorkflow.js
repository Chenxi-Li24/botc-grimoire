import { computed, ref, watch } from 'vue'

const commandKey = (kind, id = 'current') => `night:${kind}:${id}`
const asIdSet = (values, key = 'id') => new Set((values || []).map((item) => item[key]))

export function useNightWorkflow(viewRef, { service, run }) {
  const inspectedStepId = ref(null)
  const selectedSeat = ref(null)
  const targetDrafts = ref({})
  const characterDrafts = ref({})
  const informationClaims = ref({})
  const outcomeChoices = ref({})
  const forceTokens = ref({})

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
    } else if (stepId) {
      const next = { ...forceTokens.value }; delete next[stepId]; forceTokens.value = next
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
  const applyNightEffect = (payload) => run(
    commandKey('effect', `${payload.action}:${payload.source_seat}`),
    () => service.applyNightEffect(payload),
  )
  const confirmPitHag = (payload) => run(
    commandKey('pit-hag', payload.preview_id || payload.actor_seat),
    () => service.confirmPitHag(payload),
  )
  const undoNightEvent = (payload) => run(
    commandKey('undo', payload.event_id),
    () => service.undoNightEvent(payload),
  )

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

    targetDrafts.value = Object.fromEntries(Object.entries(targetDrafts.value)
      .filter(([id]) => unfinishedStepIds.has(id)))
    characterDrafts.value = Object.fromEntries(Object.entries(characterDrafts.value)
      .filter(([id]) => unfinishedStepIds.has(id)))
    informationClaims.value = Object.fromEntries(Object.entries(informationClaims.value)
      .filter(([id]) => pendingDraftIds.has(id)))
    outcomeChoices.value = Object.fromEntries(Object.entries(outcomeChoices.value)
      .filter(([id]) => pendingOutcomeIds.has(id)))
    forceTokens.value = Object.fromEntries(Object.entries(forceTokens.value)
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
    outcomeChoices,
    forceTokens,
    setInspectedStep,
    inspectCurrentTask,
    setSelectedSeat,
    toggleTarget,
    setTargets,
    setSelectedCharacter,
    setInformationClaims,
    setOutcomeChoice,
    navigate,
    selectNightTargets,
    resolveOutcome,
    deliverInformation,
    applyNightEffect,
    confirmPitHag,
    undoNightEvent,
    commandKey,
  }
}
