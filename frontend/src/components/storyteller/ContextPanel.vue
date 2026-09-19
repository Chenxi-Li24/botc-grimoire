<script setup>
import { computed } from 'vue'
import JoinPanel from './JoinPanel.vue'
import ManualAssignmentPanel from './ManualAssignmentPanel.vue'
import PlayerDetailPanel from './PlayerDetailPanel.vue'

const props = defineProps({
  view: { type: Object, required: true },
  selectedSeat: { type: Number, default: null },
  manual: { type: Object, default: null },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
defineEmits([
  'clear-selection', 'toggle-role', 'toggle-bluff', 'set-fake',
  'toggle-lunatic-minion', 'toggle-lunatic-bluff', 'set-godfather',
  'cancel-manual', 'confirm-manual',
])

const selected = computed(() => props.view.seats?.find((seat) => (
  seat.seat === props.selectedSeat && seat.player
)) || null)
</script>

<template>
  <ManualAssignmentPanel
    v-if="manual?.active"
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
    v-else-if="selected"
    :seat="selected"
    @close="$emit('clear-selection')"
  />
  <JoinPanel v-else :view="view" />
</template>
