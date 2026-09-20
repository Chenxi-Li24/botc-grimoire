<script setup>
import { computed } from 'vue'

const props = defineProps({
  seats: { type: Array, default: () => [] },
  roles: { type: Array, default: () => [] },
  selected: { type: Array, default: () => [] },
  actorSeat: { type: Number, default: null },
  selection: { type: Object, default: null },
})
defineEmits(['toggle', 'inspect'])

const roleMap = computed(() => Object.fromEntries(props.roles.map((role) => [role.id, role])))
function roleFor(seat) {
  const assigned = seat.player?.role || seat.assigned_role
  if (typeof assigned === 'string') return roleMap.value[assigned] || { id: assigned, name: assigned }
  return assigned || null
}
function unavailable(seat) {
  if (!roleFor(seat)) return true
  if (props.selection?.alive_only && (seat.secret_dead || seat.alive === false || seat.player?.alive === false)) return true
  return props.selection?.allow_self === false && seat.seat === props.actorSeat
}
</script>

<template>
  <section class="night-card target-picker">
    <div class="night-card-heading">
      <h4>选择玩家</h4>
      <span v-if="selection?.players">已选 {{ selected.length }}/{{ selection.players }}</span>
    </div>
    <div class="target-picker-grid">
      <button
        v-for="seat in seats"
        :key="seat.seat"
        type="button"
        class="target-seat"
        :class="{ active: selected.includes(seat.seat), unavailable: unavailable(seat) }"
        :disabled="unavailable(seat)"
        @click="$emit('toggle', seat.seat)"
        @contextmenu.prevent="$emit('inspect', seat.seat)"
      >
        <strong>{{ seat.seat }}号 · {{ seat.player?.name || '线下/未领取' }}</strong>
        <small>{{ roleFor(seat)?.name || '未配置角色' }}</small>
        <span v-if="seat.secret_dead || seat.alive === false || seat.player?.alive === false">已死亡</span>
      </button>
    </div>
  </section>
</template>
