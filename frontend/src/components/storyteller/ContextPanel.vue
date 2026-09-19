<script setup>
import { computed } from 'vue'
import JoinPanel from './JoinPanel.vue'
import PlayerDetailPanel from './PlayerDetailPanel.vue'

const props = defineProps({
  view: { type: Object, required: true },
  selectedSeat: { type: Number, default: null },
})
defineEmits(['clear-selection'])

const selected = computed(() => props.view.seats?.find((seat) => (
  seat.seat === props.selectedSeat && seat.player
)) || null)
</script>

<template>
  <PlayerDetailPanel
    v-if="selected"
    :seat="selected"
    @close="$emit('clear-selection')"
  />
  <JoinPanel v-else :view="view" />
</template>
