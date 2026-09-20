<script setup>
import SeatNode from './SeatNode.vue'

const props = defineProps({
  seats: { type: Array, required: true },
  selectedSeat: { type: Number, default: null },
  contextualSeat: { type: Number, default: null },
  draftAssignments: { type: Object, default: null },
  roles: { type: Array, default: () => [] },
  actingSeat: { type: Number, default: null },
  draftTargets: { type: Array, default: () => [] },
  nightSeatContext: { type: Array, default: () => [] },
  nightEffects: { type: Array, default: () => [] },
})
const emit = defineEmits(['select-seat'])

function seatPosition(seat) {
  const angle = ((2 * Math.PI) / props.seats.length) * (seat.seat - 1) - (Math.PI / 2)
  return {
    '--seat-x': `${50 + 40 * Math.cos(angle)}%`,
    '--seat-y': `${50 + 40 * Math.sin(angle)}%`,
  }
}

function draftRole(seat) {
  if (!props.draftAssignments) return null
  const roleId = props.draftAssignments[String(seat.seat)]
  return props.roles.find((role) => role.id === roleId) || null
}

function serverRoleId(seat) {
  return seat.player?.role?.id || seat.assigned_role?.id || null
}

function contextFor(seat) {
  return props.nightSeatContext.find((item) => item.seat === seat.seat) || null
}

function effectsFor(seat) {
  return props.nightEffects.filter((item) => item.target_seat === seat.seat)
}
</script>

<template>
  <div class="grimoire-stage">
    <div class="grimoire-board" aria-label="说书人魔典座位图">
      <SeatNode
        v-for="seat in seats"
        :key="seat.seat"
        :seat="seat"
        :position="seatPosition(seat)"
        :selected="selectedSeat === seat.seat"
        :contextual="contextualSeat === seat.seat"
        :draft-mode="draftAssignments !== null"
        :draft-role="draftRole(seat)"
        :draft-modified="draftAssignments !== null && (draftAssignments[String(seat.seat)] || null) !== serverRoleId(seat)"
        :acting="actingSeat === seat.seat"
        :draft-target="draftTargets.includes(seat.seat)"
        :secret-dead="Boolean(contextFor(seat)?.secret_dead)"
        :effects="effectsFor(seat)"
        @select="emit('select-seat', $event)"
      />
      <div class="grimoire-center" aria-hidden="true">
        <span>🕯</span>
        <strong>说书人</strong>
      </div>
    </div>
  </div>
</template>
