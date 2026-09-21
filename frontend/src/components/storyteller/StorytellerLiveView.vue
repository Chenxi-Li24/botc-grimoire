<script setup>
import { computed, ref, watch } from 'vue'
import { useManualAssignment } from '../../composables/useManualAssignment.js'
import { useNightWorkflow } from '../../composables/useNightWorkflow.js'
import { useStorytellerCommand } from '../../composables/useStorytellerCommand.js'
import { useStorytellerView } from '../../composables/useStorytellerView.js'
import { createStorytellerService } from '../../services/storyteller.js'
import ContextPanel from './ContextPanel.vue'
import GameControlPanel from './GameControlPanel.vue'
import GrimoireBoard from './GrimoireBoard.vue'
import ReviewPanel from './ReviewPanel.vue'
import StorytellerHeader from './StorytellerHeader.vue'
import StorytellerShell from './StorytellerShell.vue'
import '../../styles/storyteller.css'

const props = defineProps({ password: { type: String, required: true } })
const emit = defineEmits(['auth-failure'])
const { view, connectionStatus } = useStorytellerView(props.password, {
  onAuthFailure: () => emit('auth-failure'),
})
const connected = computed(() => connectionStatus.value === 'connected')
const service = createStorytellerService(props.password)
const { pending, error, run } = useStorytellerCommand({ connected })
const manual = useManualAssignment(view)
const nightWorkflow = useNightWorkflow(view, { service, run })
const selectedSeat = nightWorkflow.selectedSeat
const nightContext = computed(() => ({
  workflow: nightWorkflow.workflow.value,
  orderedSteps: nightWorkflow.orderedSteps.value,
  currentTask: nightWorkflow.currentTask.value,
  inspectedStep: nightWorkflow.inspectedStep.value,
  inspectedStepId: nightWorkflow.inspectedStepId.value,
  selectedSeat: nightWorkflow.selectedSeat.value,
  selectedTargets: nightWorkflow.selectedTargets.value,
  selectedCharacter: nightWorkflow.selectedCharacter.value,
  informationClaims: nightWorkflow.informationClaims.value,
  informationResults: nightWorkflow.informationResults.value,
  outcomeChoices: nightWorkflow.outcomeChoices.value,
  forceTokens: nightWorkflow.forceTokens.value,
  forceOmissions: nightWorkflow.forceOmissions.value,
  undoPreview: nightWorkflow.undoPreview.value,
  setInspectedStep: nightWorkflow.setInspectedStep,
  inspectCurrentTask: nightWorkflow.inspectCurrentTask,
  setSelectedSeat: nightWorkflow.setSelectedSeat,
  toggleTarget: nightWorkflow.toggleTarget,
  setTargets: nightWorkflow.setTargets,
  setSelectedCharacter: nightWorkflow.setSelectedCharacter,
  setInformationClaims: nightWorkflow.setInformationClaims,
  setInformationResult: nightWorkflow.setInformationResult,
  setOutcomeChoice: nightWorkflow.setOutcomeChoice,
  navigate: nightWorkflow.navigate,
  selectNightTargets: nightWorkflow.selectNightTargets,
  resolveOutcome: nightWorkflow.resolveOutcome,
  deliverInformation: nightWorkflow.deliverInformation,
  applyNightEffect: nightWorkflow.applyNightEffect,
  confirmPitHag: nightWorkflow.confirmPitHag,
  undoNightEvent: nightWorkflow.undoNightEvent,
  clearUndoPreview: nightWorkflow.clearUndoPreview,
}))
const manualContext = computed(() => ({
  active: manual.active.value,
  assignments: manual.assignments.value,
  bluffs: manual.bluffs.value,
  fakes: manual.fakes.value,
  lunaticMinions: manual.lunaticMinions.value,
  lunaticBluffs: manual.lunaticBluffs.value,
  godfatherAdjustment: manual.godfatherAdjustment.value,
  summary: manual.summary.value,
}))
const leftOpen = ref(false)
const rightOpen = ref(false)
const adminTab = ref(null)
const reviewOpen = ref(false)

function closeDrawers() {
  leftOpen.value = false
  rightOpen.value = false
}

function selectSeat(seat) {
  if (adminTab.value !== 'seats') adminTab.value = null
  selectedSeat.value = seat
  rightOpen.value = true
  leftOpen.value = false
}

function openAdmin(tab) {
  if (tab !== 'seats') selectedSeat.value = null
  adminTab.value = tab
  rightOpen.value = true
  leftOpen.value = false
}

function beginManual() {
  manual.begin(view.value)
  selectedSeat.value = Array.from({ length: view.value.player_count }, (_, index) => index + 1)
    .find((seat) => !manual.assignments.value[String(seat)]) || 1
  rightOpen.value = true
  leftOpen.value = false
}

async function configure({ script, playerCount }) {
  const result = await run('configure', () => service.configure(script, playerCount))
  if (result) {
    manual.invalidate()
    selectedSeat.value = null
  }
}

const setSentinel = (value) => run('sentinel', () => service.setSentinel(value))
const toggleFabled = ({ id, on }) => run(`fabled:${id}`, () => service.toggleFabled(id, on))
const setDayStage = (stage) => run('day:stage', () => service.setDayStage(stage))
const startNomination = ({ nominator, nominee }) => run(
  'day:nomination',
  () => service.startNomination(nominator, nominee),
)
const toggleVote = (participant) => run(
  `day:vote:${participant}`,
  () => service.toggleVote(participant),
)
const resolveNomination = (passed) => run(
  'day:resolve',
  () => service.resolveNomination(passed),
)
const endDay = () => run('day:end', () => service.endDay())
const addTraveler = (name) => run('traveler:add', () => service.addTraveler(name))
const assignTraveler = ({ id, role, align }) => run(`traveler:assign:${id}`, () => service.assignTraveler(id, role, align))
const setTravelerExile = ({ id, exiled }) => run(`traveler:exile:${id}`, () => service.setTravelerExile(id, exiled))
const toggleTravelerAlive = (id) => run(`traveler:alive:${id}`, () => service.toggleTravelerAlive(id))
const answerChatInvite = ({ id, accept }) => run(`chat-st:invite:${id}`, () => service.answerChatInvite(id, accept))
const sendStorytellerChat = ({ id, text }) => run(`chat-st:send:${id}`, () => service.sendStorytellerChat(id, text))
const leaveStorytellerChat = (id) => run(`chat-st:leave:${id}`, () => service.leaveStorytellerChat(id))
const closeStorytellerChat = (id) => run(`chat-st:close:${id}`, () => service.closeStorytellerChat(id))
const recallChats = () => run('chat-st:recall', () => service.recallChats())
const setRoom = (code) => run('room', () => service.setRoom(code))
const setFake = (payload) => run(`seat:fake:${payload.seat}`, () => service.setFake(payload))
const setMarker = (payload) => run(`seat:marker:${payload.seat}`, () => service.setMarker(payload))
const setRedHerring = (seat) => run('seat:red', () => service.setRedHerring(seat))
const toggleSeatAlive = (seat) => run(`seat:alive:${seat}`, () => service.toggleSeatAlive(seat))
const togglePlayerAlive = (playerId) => run(`seat:alive:${playerId}`, () => service.togglePlayerAlive(playerId))
const removePlayer = (playerId) => run(`seat:remove:${playerId}`, () => service.removePlayer(playerId))
const loadSave = () => run('load', () => service.loadSave())
const resetGame = () => run('reset', () => service.resetGame())
async function setWinner(winner) {
  const result = await run('end', () => service.setWinner(winner))
  if (result && winner === null) reviewOpen.value = false
}
const markReview = ({ seat, night, wrong }) => run('review:mark', () => service.markReview(seat, night, wrong))

async function assignRandom() {
  const result = await run('assign-random', () => service.assignRandom())
  if (result) selectedSeat.value = null
}

async function startGame() {
  const result = await run('start', () => service.start())
  if (result) selectedSeat.value = null
}

async function confirmManual() {
  const result = await run('assign-manual', () => service.assignManual(manual.payload.value))
  if (result) {
    manual.cancel()
    selectedSeat.value = null
  }
}

watch(() => view.value?.seats, (nextSeats) => {
  if (selectedSeat.value === null || !nextSeats) return
  const selected = nextSeats.find((seat) => seat.seat === selectedSeat.value)
  if (manual.active.value && selected) return
  if (!selected) selectedSeat.value = null
})
</script>

<template>
  <StorytellerShell
    v-if="view"
    data-storyteller-live
    :left-open="leftOpen"
    :right-open="rightOpen"
    @close-drawer="closeDrawers"
  >
    <template #header>
      <StorytellerHeader
        :view="view"
        :connection-status="connectionStatus"
        @open-left="leftOpen = true; rightOpen = false"
        @open-right="adminTab = null; rightOpen = true; leftOpen = false"
        @open-travelers="openAdmin('travelers')"
        @open-chats="openAdmin('chats')"
        @open-session="openAdmin('session')"
        @open-join="openAdmin('join')"
        @open-seats="openAdmin('seats')"
        @open-end="openAdmin('end')"
        @open-review="reviewOpen = true"
      />
    </template>
    <template #controls>
      <GameControlPanel
        :view="view"
        :connected="connected"
        :pending="pending"
        :error="error"
        :manual-active="manual.active.value"
        :night="nightContext"
        @configure="configure"
        @set-sentinel="setSentinel"
        @toggle-fabled="toggleFabled"
        @begin-manual="beginManual"
        @assign-random="assignRandom"
        @start="startGame"
        @inspect-step="nightWorkflow.setInspectedStep($event); rightOpen = true"
        @set-day-stage="setDayStage"
        @start-nomination="startNomination"
        @toggle-vote="toggleVote"
        @resolve-nomination="resolveNomination"
        @end-day="endDay"
      />
    </template>
    <template #board>
      <GrimoireBoard
        :seats="view.seats"
        :selected-seat="selectedSeat"
        :draft-assignments="manual.active.value ? manual.assignments.value : null"
        :roles="view.roles"
        :acting-seat="nightWorkflow.currentTask.value?.actor_seat || null"
        :draft-targets="nightWorkflow.selectedTargets.value"
        :night-seat-context="nightWorkflow.workflow.value?.seat_context || []"
        :night-effects="nightWorkflow.workflow.value?.effects?.current || []"
        @select-seat="selectSeat"
      />
    </template>
    <template #context>
      <ContextPanel
        :view="view"
        :selected-seat="selectedSeat"
        :manual="manualContext"
        :connected="connected"
        :pending="pending"
        :error="error"
        :night="nightContext"
        :admin-tab="adminTab"
        @clear-selection="selectedSeat = null"
        @toggle-role="manual.toggleRole(selectedSeat, $event)"
        @toggle-bluff="manual.setBluff"
        @set-fake="manual.setFake(selectedSeat, $event)"
        @toggle-lunatic-minion="manual.setLunaticMinion(selectedSeat, $event)"
        @toggle-lunatic-bluff="manual.setLunaticBluff(selectedSeat, $event)"
        @set-godfather="manual.setGodfatherAdjustment"
        @cancel-manual="manual.cancel(); selectedSeat = null"
        @confirm-manual="confirmManual"
        @add-traveler="addTraveler"
        @assign-traveler="assignTraveler"
        @set-traveler-exile="setTravelerExile"
        @toggle-traveler-alive="toggleTravelerAlive"
        @answer-chat-invite="answerChatInvite"
        @send-storyteller-chat="sendStorytellerChat"
        @leave-storyteller-chat="leaveStorytellerChat"
        @close-storyteller-chat="closeStorytellerChat"
        @recall-chats="recallChats"
        @set-room="setRoom"
        @load-save="loadSave"
        @reset-game="resetGame"
        @toggle-seat-alive="toggleSeatAlive"
        @toggle-player-alive="togglePlayerAlive"
        @remove-player="removePlayer"
        @set-marker="setMarker"
        @set-seat-fake="setFake"
        @set-red-herring="setRedHerring"
        @set-winner="setWinner"
        @open-review="reviewOpen = true"
      />
    </template>
  </StorytellerShell>
  <main v-else data-storyteller-live class="page center"><p>连接魔典…</p></main>
  <ReviewPanel
    v-if="view?.winner && reviewOpen"
    :view="view"
    :connected="connected"
    :pending="pending"
    :error="error"
    @mark-review="markReview"
    @back="reviewOpen = false"
  />
</template>
