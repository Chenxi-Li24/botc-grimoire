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
const playerInferences = computed(() => (props.view.player_inferences || []).map((owner) => ({
  ...owner,
  events: (owner.events || []).filter((item) => item.target === props.seat.seat),
  current: (owner.current || []).filter((item) => item.target === props.seat.seat),
})).filter((owner) => owner.events.length))
const auditRound = ref('all')
const auditCategory = ref('all')
const auditEvents = computed(() => props.seat.audit?.events || (props.seat.effect_history || []).map((effect) => ({
  ...effect, category: 'status', kind: effect.type, phase: null, number: null,
  at: effect.started_at,
})))
const auditRounds = computed(() => [...new Set(auditEvents.value
  .filter((item) => item.phase && item.number != null)
  .map((item) => `${item.phase}:${item.number}`))])
const visibleAudit = computed(() => auditEvents.value.filter((item) =>
  (auditRound.value === 'all' || `${item.phase}:${item.number}` === auditRound.value)
  && (auditCategory.value === 'all' || item.category === auditCategory.value)))
const auditGroups = computed(() => [
  { id: 'status', label: '状态与转变' },
  { id: 'information', label: '收到的信息' },
  { id: 'action', label: '能力与目标' },
].map((group) => ({ ...group, events: visibleAudit.value.filter((item) => item.category === group.id) })))
const currentStatus = computed(() => [
  ...(props.seat.effects || []).map((item) => ({
    id: item.id, label: markerLabels[item.type] || item.type, state: effectState(item),
    started_at: item.started_at, source_seat: item.source_seat,
    source_character: item.source_character, expected_end: item.expected_end,
  })),
  ...(props.seat.markers || []).filter((marker) =>
    !['role-change', 'team-change'].includes(marker)
    && !(props.seat.effects || []).some((effect) => effect.type === marker))
    .map((marker) => ({ id: `marker-${marker}`, label: markerLabels[marker] || marker })),
  ...(props.seat.role_change ? [{ id: 'role-change', label: `角色转变为${props.seat.role_change.name}` }] : []),
  ...(props.seat.team_change ? [{ id: 'team-change', label: `阵营转变为${props.seat.team_change === 'evil' ? '邪恶' : '善良'}` }] : []),
])
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

function inferenceLabel(item) {
  const data = item.data || {}
  if (item.category === 'role') return `角色：${props.view.roles?.find((role) => role.id === data.role)?.name || data.role || '已清除'}`
  if (item.category === 'alignment') return `阵营：${({ good: '善良', evil: '邪恶', unknown: '未知' })[data.alignment] || '已清除'}`
  if (item.category === 'status') return `状态：${markerLabels[data.status] || data.status}`
  return `变化：${data.kind === 'role' ? '角色' : '阵营'} ${data.from || '未知'} → ${data.to || '未知'}`
}

function effectEndedAt(effect) {
  return [...(effect.transitions || [])].reverse().find((item) => item.to === 'ended')?.at || null
}

function roundLabel(item) {
  return item.number == null ? '轮次未记录' : `第 ${item.number} ${item.phase === 'day' ? '天' : '夜'}`
}

function roleName(id) {
  return props.view.roles?.find((item) => item.id === id)?.name || id || '未知'
}

function auditTitle(item) {
  if (item.category === 'status') {
    if (item.kind === 'role_change') return `角色转变：${roleName(item.from)} → ${roleName(item.to)}`
    if (item.kind === 'team_change') return `阵营转变：${item.to || '未知'}`
    return markerLabels[item.kind] || markerLabels[item.marker] || item.kind
  }
  if (item.category === 'information') return item.kind === 'delivery' ? '获告知的信息' : item.kind === 'draft' ? '待发送信息' : '说书人回复'
  if (item.kind === 'lunatic_kill') return '疯子自选目标（不直接生效）'
  return `${roleName(item.role_snapshot)} · ${item.kind === 'outcome' ? '选择与裁定' : '夜晚选择'}`
}

function auditState(item) {
  return ({ withdrawn: '已撤回', unsent: '未发送', pending: '待裁定', selected: '已选择',
    effective: '已生效', ended: '已结束', suspended: '已暂停', active: '持续中' })[item.state] || item.state
}

function seatsLabel(items) {
  return (items || []).length ? items.map((item) => `${item}号`).join('、') : '未记录'
}

function informationValue(value) {
  if (value == null) return '未记录'
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function registrationLabel(item) {
  if (typeof item !== 'object' || item === null) return String(item)
  return `${item.seat ? `${item.seat}号：` : ''}${item.as || item.registered_as || item.character || informationValue(item)}`
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
  auditRound.value = 'all'
  auditCategory.value = 'all'
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
      <div><dt>角色</dt><dd>{{ role?.name || '未分配' }}<span v-if="seat.fake_role && ['drunk', 'lunatic'].includes(role?.id)"> · 他以为：{{ seat.fake_role.name }}</span><span v-else-if="['drunk', 'lunatic'].includes(role?.id)"> · 待配置认知</span></dd></div>
      <div><dt>阵营</dt><dd>{{ teamLabel }}</dd></div>
      <div><dt>状态</dt><dd>{{ alive ? '存活' : '死亡' }}</dd></div>
    </dl>
    <div v-if="seat.red_herring" class="seat-red-herring">🎯 宿敌</div>
    <section data-current-status class="seat-admin-section">
      <h3>当前状态</h3>
      <p v-if="!currentStatus.length" class="inline-note">暂无异常状态</p>
      <div v-for="item in currentStatus" :key="item.id" class="effect-history-row">
        <strong>{{ item.label }}{{ item.state ? ` · ${item.state}` : '' }}</strong>
        <span>开始：{{ item.started_at || '早期历史未记录' }}</span>
        <span v-if="item.source_seat || item.source_character">来源：{{ item.source_seat ? `${item.source_seat}号` : '' }}{{ item.source_character ? ` · ${roleName(item.source_character)}` : '' }}</span>
        <span v-if="item.expected_end">预计结束：{{ item.expected_end }}</span>
      </div>
    </section>
    <p v-if="seat.player?.wish" class="inline-note">许愿：{{ seat.player.wish }}</p>
    <div class="admin-actions">
      <button data-seat-alive class="btn" type="button" :disabled="!connected || !role" @click="toggleLife">{{ alive ? '标记死亡' : '复活' }}</button>
      <button v-if="seat.player" data-seat-remove class="btn danger" type="button" :disabled="!connected" :aria-pressed="removeArmed" @click="removePlayer">{{ removeArmed ? `确认移除 ${seat.player.name}？` : '移除玩家' }}</button>
    </div>
    <p v-if="!seat.player" class="inline-note">该身份已分配给座位，线下玩家无需领取也会参与规则判定。</p>
    <section data-storyteller-inferences class="seat-admin-section">
      <h3>玩家推测 · 只读</h3>
      <p class="inline-note">这里是玩家的主观笔记，与上方真实角色及状态分开；不会影响判定。</p>
      <p v-if="!playerInferences.length" class="inline-note">暂无玩家推测本座。</p>
      <details v-for="owner in playerInferences" :key="owner.player_id">
        <summary>{{ owner.name }} · {{ owner.events.length }} 条记录</summary>
        <p v-for="item in owner.current" :key="`current-${item.seq}`" class="inline-note">当前：{{ inferenceLabel(item) }}</p>
        <p v-for="item in owner.events.slice().reverse()" :key="item.seq" class="inline-note">{{ new Date(item.recorded_at * 1000).toLocaleString() }} · {{ item.operation === 'set' ? '记录' : '结束/清除' }} {{ inferenceLabel(item) }}{{ item.data?.reason ? ` · ${item.data.reason}` : '' }}</p>
      </details>
    </section>
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
    <section class="seat-admin-section" data-seat-audit>
      <h3>逐日记录</h3>
      <div class="admin-actions">
        <label>轮次 <select v-model="auditRound" data-audit-round><option value="all">全部</option><option v-for="round in auditRounds" :key="round" :value="round">{{ roundLabel({ phase: round.split(':')[0], number: Number(round.split(':')[1]) }) }}</option></select></label>
        <label>类别 <select v-model="auditCategory" data-audit-filter><option value="all">全部</option><option value="status">状态与转变</option><option value="information">收到的信息</option><option value="action">能力与目标</option></select></label>
      </div>
      <p v-if="!visibleAudit.length" class="inline-note">无历史记录；早期事件可能未留存。</p>
      <section v-for="group in auditGroups.filter((item) => item.events.length)" :key="group.id" :data-audit-category="group.id" class="seat-audit-group">
        <h4>{{ group.label }}</h4>
        <div v-for="item in group.events.slice(0, 4)" :key="item.id" class="effect-history-row">
          <strong>{{ roundLabel(item) }} · {{ auditTitle(item) }}</strong>
          <span>{{ auditState(item) }}</span>
          <span v-if="item.at">获得：{{ item.at }}</span>
          <span v-if="item.source_seat">来源：{{ item.source_seat }}号{{ item.source_character ? ` · ${roleName(item.source_character)}` : '' }}</span>
          <span v-if="item.expected_end">预期结束：{{ item.expected_end }}</span>
          <span v-if="effectEndedAt(item)">结束于：{{ effectEndedAt(item) }}</span>
          <span v-if="item.selected_seats?.length">选择：{{ seatsLabel(item.selected_seats) }}</span>
          <span v-if="item.linked_lunatic_selection?.length">疯子自选：{{ seatsLabel(item.linked_lunatic_selection) }}</span>
          <span v-if="item.linked_outcome_id">{{ item.demon_followed ? '真恶魔沿用' : '真恶魔未沿用' }} · 裁定 {{ item.linked_outcome_id }}</span>
          <span v-if="item.resolution">裁定：{{ item.resolution }}</span>
          <span v-if="item.affected_seats?.length">实际影响：{{ seatsLabel(item.affected_seats) }}</span>
          <span v-if="item.dawn_deaths?.length">天亮死亡：{{ seatsLabel(item.dawn_deaths) }}</span>
          <span v-if="item.delivered_result != null">告知：{{ informationValue(item.delivered_result) }}</span>
          <span v-if="item.reply != null">回复：{{ item.reply }}</span>
          <span v-if="item.claims?.length">真假：{{ item.claims.map((claim) => `${claim.label || '结果'}${claim.truthful ? '真' : '假'}`).join('、') }}</span>
          <span v-if="item.registrations?.length">登记：{{ item.registrations.map(registrationLabel).join('、') }}</span>
          <span v-if="item.effect_snapshot?.length">异常快照：{{ item.effect_snapshot.join('、') }}</span>
          <span v-for="correction in item.corrections || []" :key="correction.id">更正：{{ correction.reason || '原因未记录' }}{{ correction.claims?.length ? ` · ${correction.claims.map((claim) => `${claim.label || '结果'}${claim.truthful ? '真' : '假'}`).join('、')}` : '' }}</span>
          <span v-if="item.source_event">事件：{{ item.source_event }}</span>
          <span v-if="item.transitions?.length">变化：{{ item.transitions.map((transition) => `${transition.at || '时间未记录'} ${transition.reason || transition.to}`).join('；') }}</span>
        </div>
        <details v-if="group.events.length > 4"><summary>展开更早记录（{{ group.events.length - 4 }}）</summary><div v-for="item in group.events.slice(4)" :key="item.id" class="effect-history-row"><strong>{{ roundLabel(item) }} · {{ auditTitle(item) }}</strong><span>{{ auditState(item) }}</span><span v-if="item.source_event">事件：{{ item.source_event }}</span><span v-if="item.selected_seats?.length">选择：{{ seatsLabel(item.selected_seats) }}</span><span v-if="item.linked_lunatic_selection?.length">疯子自选：{{ seatsLabel(item.linked_lunatic_selection) }}</span><span v-if="item.linked_outcome_id">{{ item.demon_followed ? '真恶魔沿用' : '真恶魔未沿用' }} · 裁定 {{ item.linked_outcome_id }}</span><span v-if="item.resolution">裁定：{{ item.resolution }}</span><span v-if="item.affected_seats?.length">实际影响：{{ seatsLabel(item.affected_seats) }}</span><span v-if="item.dawn_deaths?.length">天亮死亡：{{ seatsLabel(item.dawn_deaths) }}</span><span v-if="item.delivered_result != null">告知：{{ informationValue(item.delivered_result) }}</span></div></details>
      </section>
    </section>
    <p v-if="error?.key?.startsWith('seat:')" class="inline-error">{{ error.message }}</p>
  </div>
</template>
