<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const teamLabels = {
  townsfolk: '镇民', outsider: '外来者', minion: '爪牙', demon: '恶魔', traveler: '旅行者',
}
const markerLabels = {
  poisoned: '中毒', drunk: '醉酒', mad: '疯狂',
  'role-change': '角色转变', 'team-change': '阵营转变',
}
const props = defineProps({
  seat: { type: Object, required: true },
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits([
  'close', 'toggle-seat-alive', 'toggle-player-alive', 'remove-player',
  'set-marker', 'set-fake', 'set-red-herring',
])
const role = computed(() => props.seat.player?.role || props.seat.assigned_role || null)
const alive = computed(() => props.seat.player?.alive ?? props.seat.alive ?? true)
const name = computed(() => props.seat.player?.name || '线下/未领取')
const teamLabel = computed(() => teamLabels[role.value?.team] || role.value?.team || '未分配')
const markers = computed(() => props.seat.markers || [])
const fakeTeams = computed(() => props.view.fake_pools?.[role.value?.id] || [])
const fakeCandidates = computed(() => (props.view.roles || []).filter((item) => fakeTeams.value.includes(item.team)))
const goodRoles = computed(() => (props.view.roles || []).filter((item) => ['townsfolk', 'outsider'].includes(item.team)))
const picker = ref(null)
const removeArmed = ref(false)
let removeTimer = null
const draftMinions = ref([])
const draftBluffs = ref([])

function effectState(effect) {
  if (effect.state === 'ended') return '已结束'
  if (effect.state === 'suspended') return '已暂停'
  return '持续中'
}

function effectEndedAt(effect) {
  return [...(effect.transitions || [])].reverse().find((item) => item.to === 'ended')?.at || null
}

function clearRemoveArm() {
  removeArmed.value = false
  if (removeTimer) clearTimeout(removeTimer)
  removeTimer = null
}

function removePlayer() {
  if (!props.connected || !props.seat.player) return
  if (removeArmed.value) {
    clearRemoveArm()
    emit('remove-player', props.seat.player.id)
    return
  }
  removeArmed.value = true
  removeTimer = setTimeout(clearRemoveArm, 3000)
}

function toggleLife() {
  if (!props.connected || !role.value) return
  if (props.seat.player) emit('toggle-player-alive', props.seat.player.id)
  else emit('toggle-seat-alive', props.seat.seat)
}

function markerActive(marker) {
  if (marker === 'role-change') return !!props.seat.role_change
  if (marker === 'team-change') return !!props.seat.team_change
  return markers.value.includes(marker)
}

function chooseMarker(marker) {
  if (!props.connected) return
  if (markerActive(marker) || ['poisoned', 'drunk'].includes(marker)) {
    emit('set-marker', { seat: props.seat.seat, marker, on: !markerActive(marker) })
    picker.value = null
  } else {
    picker.value = picker.value === marker ? null : marker
  }
}

function setMarkerValue(marker, field, value) {
  if (!props.connected) return
  emit('set-marker', { seat: props.seat.seat, marker, on: true, [field]: value })
  picker.value = null
}

function markerDetail(marker) {
  if (marker === 'team-change' && props.seat.team_change) {
    return ` · 转变为${props.seat.team_change === 'evil' ? '邪恶' : '善良'}`
  }
  if (marker === 'mad' && props.seat.mad_about) return ` · 疯狂宣称${props.seat.mad_about.name}`
  if (marker === 'role-change' && props.seat.role_change) return ` · 转变为${props.seat.role_change.name}`
  return markerActive(marker) ? ' · 已标记' : ''
}

function setFake(roleId, preserve = false) {
  const next = !preserve && props.seat.fake_role?.id === roleId ? null : roleId
  const payload = { seat: props.seat.seat, role: next }
  if (next && role.value?.id === 'lunatic') {
    if (draftMinions.value.length) payload.minions = [...draftMinions.value]
    if (draftBluffs.value.length === 3) payload.bluffs = [...draftBluffs.value]
  }
  emit('set-fake', payload)
}

function toggleMinion(seat) {
  draftMinions.value = draftMinions.value.includes(seat)
    ? draftMinions.value.filter((item) => item !== seat)
    : [...draftMinions.value, seat]
}

function toggleBluff(roleId) {
  draftBluffs.value = draftBluffs.value.includes(roleId)
    ? draftBluffs.value.filter((item) => item !== roleId)
    : draftBluffs.value.length < 3 ? [...draftBluffs.value, roleId] : draftBluffs.value
}

watch(() => props.seat.seat, () => {
  picker.value = null
  clearRemoveArm()
  draftMinions.value = [...(props.view.lunatic_minions?.[String(props.seat.seat)] || [])]
  draftBluffs.value = (props.view.lunatic_bluffs?.[String(props.seat.seat)] || [])
    .map((item) => typeof item === 'string' ? item : item?.id)
    .filter(Boolean)
}, { immediate: true })
watch(() => props.connected, (connected) => { if (!connected) clearRemoveArm() })
onBeforeUnmount(clearRemoveArm)
</script>

<template>
  <div class="panel-content player-context">
    <div class="context-heading">
      <div><p class="panel-eyebrow">{{ seat.seat }}号座位</p><h2>{{ name }}</h2></div>
      <button data-clear-selection class="context-close" type="button" @click="$emit('close')">返回当前任务</button>
    </div>
    <dl class="player-summary">
      <div><dt>角色</dt><dd>{{ role?.name || '未分配' }}</dd></div>
      <div><dt>阵营</dt><dd>{{ teamLabel }}</dd></div>
      <div><dt>状态</dt><dd>{{ alive ? '存活' : '死亡' }}</dd></div>
    </dl>
    <p v-if="seat.player?.wish" class="inline-note">许愿：{{ seat.player.wish }}</p>
    <div class="admin-actions">
      <button data-seat-alive class="btn" type="button" :disabled="!connected || !role" @click="toggleLife">{{ alive ? '标记死亡' : '复活' }}</button>
      <button v-if="seat.player" data-seat-remove class="btn danger" type="button" :disabled="!connected" :aria-pressed="removeArmed" @click="removePlayer">{{ removeArmed ? `确认移除 ${seat.player.name}？` : '移除玩家' }}</button>
    </div>
    <p v-if="!seat.player" class="inline-note">该身份已分配给座位，线下玩家无需领取也会参与规则判定。</p>
    <section class="seat-admin-section">
      <h3>状态标记</h3>
      <div class="admin-actions">
        <button v-for="(label, marker) in markerLabels" :key="marker" :data-seat-marker="marker" class="btn" :class="{ primary: markerActive(marker) }" type="button" :disabled="!connected || !role" @click="chooseMarker(marker)">{{ label }}{{ markerDetail(marker) }}</button>
      </div>
      <div v-if="picker === 'role-change'" class="admin-actions">
        <button v-for="item in view.roles || []" :key="item.id" :data-seat-role="item.id" class="btn" type="button" :disabled="!connected" @click="setMarkerValue('role-change', 'role', item.id)">{{ item.name }}</button>
      </div>
      <div v-if="picker === 'team-change'" class="admin-actions">
        <button v-for="item in ['good', 'evil']" :key="item" :data-seat-team="item" class="btn" type="button" :disabled="!connected" @click="setMarkerValue('team-change', 'team', item)">{{ item === 'good' ? '善良' : '邪恶' }}</button>
      </div>
      <div v-if="picker === 'mad'" class="admin-actions">
        <button v-for="item in goodRoles" :key="item.id" :data-seat-mad="item.id" class="btn" type="button" :disabled="!connected" @click="setMarkerValue('mad', 'about', item.id)">{{ item.name }}</button>
      </div>
    </section>
    <section v-if="fakeCandidates.length" class="seat-admin-section">
      <h3>认知覆盖 · 玩家看到的身份</h3>
      <div class="admin-actions">
        <button v-for="item in fakeCandidates" :key="item.id" :data-seat-fake="item.id" class="btn" :class="{ primary: seat.fake_role?.id === item.id }" type="button" :disabled="!connected" @click="setFake(item.id)">{{ item.name }}</button>
      </div>
      <template v-if="role?.id === 'lunatic'">
        <p class="inline-note">疯子以为的爪牙</p>
        <div class="admin-actions">
          <button v-for="slot in view.seats.filter((item) => item.seat !== seat.seat)" :key="slot.seat" :data-fake-minion="slot.seat" class="btn" :class="{ primary: draftMinions.includes(slot.seat) }" type="button" :disabled="!connected" @click="toggleMinion(slot.seat)">{{ slot.seat }}号</button>
        </div>
        <p class="inline-note">疯子看到的三张伪装（已选 {{ draftBluffs.length }}/3）</p>
        <div class="admin-actions">
          <button v-for="item in goodRoles" :key="item.id" :data-fake-bluff="item.id" class="btn" :class="{ primary: draftBluffs.includes(item.id) }" type="button" :disabled="!connected" @click="toggleBluff(item.id)">{{ item.name }}</button>
        </div>
        <button v-if="seat.fake_role" data-save-lunatic class="btn" type="button" :disabled="!connected || !draftMinions.length || draftBluffs.length !== 3" @click="setFake(seat.fake_role.id, true)">保存疯子线索</button>
      </template>
    </section>
    <section class="seat-admin-section">
      <h3>占卜师宿敌</h3>
      <button data-seat-red class="btn" type="button" :disabled="!connected || !role" @click="$emit('set-red-herring', view.fortuneteller_red === seat.seat ? null : seat.seat)">{{ view.fortuneteller_red === seat.seat ? '清除本座宿敌' : '设本座为宿敌' }}</button>
    </section>
    <section v-if="seat.effects?.length || seat.effect_history?.length" class="seat-admin-section">
      <h3>异常状态溯源</h3>
      <p v-for="effect in seat.effects || []" :key="`current-${effect.id}`" class="inline-note">当前：{{ markerLabels[effect.type] || effect.type }} · {{ effectState(effect) }}</p>
      <div v-for="effect in seat.effect_history || []" :key="`history-${effect.id}`" class="effect-history-row">
        <strong>{{ markerLabels[effect.type] || effect.type }} · {{ effectState(effect) }}</strong>
        <span>获得：{{ effect.started_at }}</span>
        <span v-if="effect.source_seat">来源：{{ effect.source_seat }}号{{ effect.source_character ? ` · ${effect.source_character}` : '' }}</span>
        <span v-else-if="effect.source_character">来源：{{ effect.source_character }}</span>
        <span v-if="effect.expected_end">预期结束：{{ effect.expected_end }}</span>
        <span v-if="effectEndedAt(effect)">结束于：{{ effectEndedAt(effect) }}</span>
        <span v-for="(transition, index) in effect.transitions || []" :key="index">{{ transition.at }} · {{ transition.reason }}</span>
      </div>
    </section>
    <p v-if="error?.key?.startsWith('seat:')" class="inline-error">{{ error.message }}</p>
  </div>
</template>
