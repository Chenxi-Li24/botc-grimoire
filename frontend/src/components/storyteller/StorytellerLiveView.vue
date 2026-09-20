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

function closeDrawers() {
  leftOpen.value = false
  rightOpen.value = false
}

function selectSeat(seat) {
  selectedSeat.value = seat
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
  if (!selected?.player) selectedSeat.value = null
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
        @open-right="rightOpen = true; leftOpen = false"
      />
    </template>
    <template #controls>
      <GameControlPanel
        :view="view"
        :connected="connected"
        :pending="pending"
        :error="error"
        :manual-active="manual.active.value"
        @configure="configure"
        @set-sentinel="setSentinel"
        @toggle-fabled="toggleFabled"
        @begin-manual="beginManual"
        @assign-random="assignRandom"
        @start="startGame"
      />
    </template>
    <template #board>
      <GrimoireBoard
        :seats="view.seats"
        :selected-seat="selectedSeat"
        :draft-assignments="manual.active.value ? manual.assignments.value : null"
        :roles="view.roles"
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
        @clear-selection="selectedSeat = null"
        @toggle-role="manual.toggleRole(selectedSeat, $event)"
        @toggle-bluff="manual.setBluff"
        @set-fake="manual.setFake(selectedSeat, $event)"
        @toggle-lunatic-minion="manual.setLunaticMinion(selectedSeat, $event)"
        @toggle-lunatic-bluff="manual.setLunaticBluff(selectedSeat, $event)"
        @set-godfather="manual.setGodfatherAdjustment"
        @cancel-manual="manual.cancel(); selectedSeat = null"
        @confirm-manual="confirmManual"
      />
    </template>
  </StorytellerShell>
  <main v-else data-storyteller-live class="page center"><p>连接魔典…</p></main>
</template>
