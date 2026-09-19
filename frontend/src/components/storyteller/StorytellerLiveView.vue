<script setup>
import { ref, watch } from 'vue'
import { useStorytellerView } from '../../composables/useStorytellerView.js'
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
const leftOpen = ref(false)
const rightOpen = ref(false)
const selectedSeat = ref(null)

function closeDrawers() {
  leftOpen.value = false
  rightOpen.value = false
}

function selectSeat(seat) {
  selectedSeat.value = seat
  rightOpen.value = true
  leftOpen.value = false
}

watch(() => view.value?.seats, (nextSeats) => {
  if (selectedSeat.value === null || !nextSeats) return
  const selected = nextSeats.find((seat) => seat.seat === selectedSeat.value)
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
    <template #controls><GameControlPanel :view="view" /></template>
    <template #board>
      <GrimoireBoard
        :seats="view.seats"
        :selected-seat="selectedSeat"
        @select-seat="selectSeat"
      />
    </template>
    <template #context>
      <ContextPanel
        :view="view"
        :selected-seat="selectedSeat"
        @clear-selection="selectedSeat = null"
      />
    </template>
  </StorytellerShell>
  <main v-else data-storyteller-live class="page center"><p>连接魔典…</p></main>
</template>
