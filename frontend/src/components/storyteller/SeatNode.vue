<script setup>
import { computed } from 'vue'
import { roleIconUrl } from '../../presentation/roleIcons.js'

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
  acting: { type: Boolean, default: false },
  draftTarget: { type: Boolean, default: false },
  secretDead: { type: Boolean, default: false },
  effects: { type: Array, default: () => [] },
})
const emit = defineEmits(['select'])

const player = computed(() => props.seat.player)
const role = computed(() => props.draftMode
  ? props.draftRole
  : (player.value?.role || props.seat.assigned_role || null))
const roleIcon = computed(() => roleIconUrl(role.value?.id))
const accessibleName = computed(() => `${props.seat.seat}号 · ${player.value?.name || (role.value ? '线下/未领取' : '空座')}`)
const markers = computed(() => (props.seat.markers || []).map((marker) => markerLabels[marker] || marker))
const isDead = computed(() => props.secretDead || props.seat.alive === false || (player.value && !player.value.alive))
</script>

<template>
  <button
    class="grimoire-seat"
    :class="[
      role?.team ? `team-${role.team}` : '',
      { 'is-empty': !player && !role, 'is-unclaimed': !player && role, 'is-dead': isDead, 'is-secret-dead': secretDead, 'is-selected': selected, 'is-contextual': contextual, 'is-draft': draftModified, 'is-acting': acting, 'is-target-draft': draftTarget, 'has-effects': effects.length },
    ]"
    type="button"
    :data-seat="seat.seat"
    :style="position"
    :aria-label="accessibleName"
    @click="emit('select', seat.seat)"
  >
    <span class="seat-number">{{ seat.seat }}号</span>
    <strong class="seat-player">{{ player?.name || (role ? '线下/未领取' : '空座') }}</strong>
    <img v-if="roleIcon" class="seat-role-icon" :src="roleIcon" alt="" width="40" height="40" loading="lazy" />
    <span v-if="role" class="seat-role">{{ role.name }}</span>
    <span v-if="draftModified" class="seat-draft">草稿</span>
    <span v-if="isDead" class="seat-life">{{ secretDead ? '本夜死亡' : '死亡' }}</span>
    <span v-if="effects.length" class="seat-effect">状态 {{ effects.length }}</span>
    <span v-for="marker in markers" :key="marker" class="seat-marker">{{ marker }}</span>
  </button>
</template>
