<script setup>
import { computed } from 'vue'

const markerLabels = {
  poisoned: '中毒',
  drunk: '醉酒',
  mad: '疯狂',
  redherring: '宿敌',
  'role-change': '角色转变',
  'team-change': '阵营转变',
}

const props = defineProps({
  seat: { type: Object, required: true },
  position: { type: Object, required: true },
  selected: { type: Boolean, default: false },
  contextual: { type: Boolean, default: false },
  draftMode: { type: Boolean, default: false },
  draftRole: { type: Object, default: null },
  draftModified: { type: Boolean, default: false },
})
const emit = defineEmits(['select'])

const player = computed(() => props.seat.player)
const role = computed(() => props.draftMode
  ? props.draftRole
  : (player.value?.role || props.seat.assigned_role || null))
const accessibleName = computed(() => `${props.seat.seat}号 · ${player.value?.name || '空座'}`)
const markers = computed(() => (props.seat.markers || []).map((marker) => markerLabels[marker] || marker))
</script>

<template>
  <button
    class="grimoire-seat"
    :class="[
      role?.team ? `team-${role.team}` : '',
      { 'is-empty': !player, 'is-dead': player && !player.alive, 'is-selected': selected, 'is-contextual': contextual, 'is-draft': draftModified },
    ]"
    type="button"
    :data-seat="seat.seat"
    :style="position"
    :aria-label="accessibleName"
    @click="emit('select', seat.seat)"
  >
    <span class="seat-number">{{ seat.seat }}号</span>
    <strong class="seat-player">{{ player?.name || '空座' }}</strong>
    <span v-if="role" class="seat-role">{{ role.name }}</span>
    <span v-if="draftModified" class="seat-draft">草稿</span>
    <span v-if="player && !player.alive" class="seat-life">死亡</span>
    <span v-for="marker in markers" :key="marker" class="seat-marker">{{ marker }}</span>
  </button>
</template>
