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
const hiddenIdentity = computed(() => !props.draftMode && ['drunk', 'lunatic'].includes(role.value?.id))
const perceivedRole = computed(() => hiddenIdentity.value ? props.seat.fake_role || null : null)
const displayRole = computed(() => perceivedRole.value || role.value)
const roleIcon = computed(() => roleIconUrl(displayRole.value?.id))
const seatImage = roleIcon
const seatImageAlt = computed(() => displayRole.value ? `${displayRole.value.name}角色图标` : '')
const realBadge = computed(() => role.value?.id === 'drunk' ? '🍺 酒鬼' : '🌙 疯子')
const accessibleName = computed(() => {
  const base = `${props.seat.seat}号 · ${player.value?.name || (role.value ? '线下/未领取' : '空座')}`
  if (!role.value) return base
  const identity = perceivedRole.value
    ? ` · 真实身份 ${role.value.name} · 他以为 ${perceivedRole.value.name}`
    : hiddenIdentity.value ? ` · 真实身份 ${role.value.name} · 待配置认知` : ''
  return `${base}${identity}${props.seat.red_herring && !props.draftMode ? ' · 宿敌' : ''}`
})
const markers = computed(() => (props.seat.markers || []).map((marker) => markerLabels[marker] || marker))
const ringTeam = computed(() => !props.draftMode && props.seat.team_change
  ? props.seat.team_change : role.value?.team)
const isDead = computed(() => props.secretDead || props.seat.alive === false || (player.value && !player.value.alive))
</script>

<template>
  <button
    class="grimoire-seat"
    :class="[
      ringTeam ? `team-${ringTeam}` : '',
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
    <img v-if="seatImage" class="seat-role-icon" :src="seatImage" :alt="seatImageAlt" width="40" height="40" loading="lazy" />
    <span v-if="displayRole" class="seat-role">{{ perceivedRole ? `他以为：${displayRole.name}` : displayRole.name }}</span>
    <span v-if="hiddenIdentity" class="seat-real-role">{{ realBadge }}</span>
    <span v-if="hiddenIdentity && !perceivedRole" class="seat-perception-pending">待配置认知</span>
    <span v-if="seat.red_herring && !draftMode" class="seat-red-herring">🎯 宿敌</span>
    <span v-if="draftModified" class="seat-draft">草稿</span>
    <span v-if="isDead" class="seat-life">{{ secretDead ? '本夜死亡' : '死亡' }}</span>
    <span v-if="effects.length" class="seat-effect">状态 {{ effects.length }}</span>
    <span v-for="(marker, index) in markers" :key="marker" class="seat-marker" :class="{ 'seat-marker-extra': index > 0 }">{{ marker }}</span>
    <span v-if="markers.length > 1" class="seat-marker-count">状态 +{{ markers.length - 1 }}</span>
  </button>
</template>
