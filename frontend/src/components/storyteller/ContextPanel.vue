<script setup>
import { computed } from 'vue'
import JoinPanel from './JoinPanel.vue'
import ManualAssignmentPanel from './ManualAssignmentPanel.vue'
import PlayerDetailPanel from './PlayerDetailPanel.vue'
import NightTaskPanel from './night/NightTaskPanel.vue'
import TravelerPanel from './TravelerPanel.vue'
import StorytellerChatPanel from './StorytellerChatPanel.vue'
import SessionPanel from './SessionPanel.vue'

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
  'set-room', 'load-save', 'reset-game', 'toggle-seat-alive', 'toggle-player-alive',
  'remove-player', 'set-marker', 'set-red-herring',
  'set-seat-fake',
])

const selected = computed(() => props.view.seats?.find((seat) => (
  seat.seat === props.selectedSeat
)) || null)
</script>

<template>
  <SessionPanel
    v-if="adminTab === 'session'"
    :view="view"
    :connected="connected"
    :pending="pending"
    :error="error"
    @set-room="$emit('set-room', $event)"
    @load-save="$emit('load-save')"
    @reset-game="$emit('reset-game')"
  />
  <StorytellerChatPanel
    v-else-if="adminTab === 'chats' && view.status === 'playing'"
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
  <PlayerDetailPanel
    v-else-if="selected && (selected.player || selected.assigned_role) && (adminTab === 'seats' || view.phase !== 'night')"
    :seat="selected"
    :view="view"
    :connected="connected"
    :pending="pending"
    :error="error"
    @close="$emit('clear-selection')"
    @toggle-seat-alive="$emit('toggle-seat-alive', $event)"
    @toggle-player-alive="$emit('toggle-player-alive', $event)"
    @remove-player="$emit('remove-player', $event)"
    @set-marker="$emit('set-marker', $event)"
    @set-fake="$emit('set-seat-fake', $event)"
    @set-red-herring="$emit('set-red-herring', $event)"
  />
  <NightTaskPanel
    v-else-if="view.status === 'playing' && view.phase === 'night' && night && adminTab !== 'seats'"
    :view="view"
    :night="night"
    :connected="connected"
    :pending="pending"
    :error="error"
  />
  <div v-else-if="adminTab === 'seats'" class="panel-content"><h2>座位管理</h2><p class="inline-note">点击魔典上的座位，查看和调整身份、状态与生死。</p></div>
  <JoinPanel v-else :view="view" />
</template>
