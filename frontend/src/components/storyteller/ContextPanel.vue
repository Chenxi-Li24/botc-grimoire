<script setup>
import { computed } from 'vue'
import JoinPanel from './JoinPanel.vue'
import ManualAssignmentPanel from './ManualAssignmentPanel.vue'
import PlayerDetailPanel from './PlayerDetailPanel.vue'
import NightTaskPanel from './night/NightTaskPanel.vue'
import TravelerPanel from './TravelerPanel.vue'
import StorytellerChatPanel from './StorytellerChatPanel.vue'

const props = defineProps({
  view: { type: Object, required: true },
  selectedSeat: { type: Number, default: null },
  manual: { type: Object, default: null },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
  night: { type: Object, default: null },
  adminTab: { type: String, default: null },
})
defineEmits([
  'clear-selection', 'toggle-role', 'toggle-bluff', 'set-fake',
  'toggle-lunatic-minion', 'toggle-lunatic-bluff', 'set-godfather',
  'cancel-manual', 'confirm-manual',
  'add-traveler', 'assign-traveler', 'set-traveler-exile', 'toggle-traveler-alive',
  'answer-chat-invite', 'send-storyteller-chat', 'leave-storyteller-chat', 'close-storyteller-chat', 'recall-chats',
])

const selected = computed(() => props.view.seats?.find((seat) => (
  seat.seat === props.selectedSeat
)) || null)
</script>

<template>
  <StorytellerChatPanel
    v-if="adminTab === 'chats' && view.status === 'playing'"
    :view="view"
    :connected="connected"
    :pending="pending"
    :error="error"
    @answer-invite="$emit('answer-chat-invite', $event)"
    @send="$emit('send-storyteller-chat', $event)"
    @leave="$emit('leave-storyteller-chat', $event)"
    @close="$emit('close-storyteller-chat', $event)"
    @recall="$emit('recall-chats')"
  />
  <TravelerPanel
    v-else-if="adminTab === 'travelers' && view.status === 'playing'"
    :view="view"
    :connected="connected"
    :pending="pending"
    :error="error"
    @add="$emit('add-traveler', $event)"
    @assign="$emit('assign-traveler', $event)"
    @set-exile="$emit('set-traveler-exile', $event)"
    @toggle-alive="$emit('toggle-traveler-alive', $event)"
  />
  <ManualAssignmentPanel
    v-else-if="manual?.active"
    :view="view"
    :selected-seat="selectedSeat"
    :assignments="manual.assignments"
    :bluffs="manual.bluffs"
    :fakes="manual.fakes"
    :lunatic-minions="manual.lunaticMinions"
    :lunatic-bluffs="manual.lunaticBluffs"
    :godfather-adjustment="manual.godfatherAdjustment"
    :summary="manual.summary"
    :connected="connected"
    :pending="pending"
    :error="error"
    @toggle-role="$emit('toggle-role', $event)"
    @toggle-bluff="$emit('toggle-bluff', $event)"
    @set-fake="$emit('set-fake', $event)"
    @toggle-lunatic-minion="$emit('toggle-lunatic-minion', $event)"
    @toggle-lunatic-bluff="$emit('toggle-lunatic-bluff', $event)"
    @set-godfather="$emit('set-godfather', $event)"
    @cancel="$emit('cancel-manual')"
    @confirm="$emit('confirm-manual')"
  />
  <NightTaskPanel
    v-else-if="view.status === 'playing' && view.phase === 'night' && night"
    :view="view"
    :night="night"
    :connected="connected"
    :pending="pending"
    :error="error"
  />
  <PlayerDetailPanel
    v-else-if="selected?.player"
    :seat="selected"
    @close="$emit('clear-selection')"
  />
  <JoinPanel v-else :view="view" />
</template>
