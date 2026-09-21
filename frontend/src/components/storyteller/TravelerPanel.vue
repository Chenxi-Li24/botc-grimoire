<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits(['add', 'assign', 'set-exile', 'toggle-alive'])
const name = ref('')
const selectedId = ref(null)
const draftAlign = ref('good')
const armedExile = ref(null)
let exileTimer = null

const travelers = computed(() => props.view.travelers || [])
const roles = computed(() => props.view.traveler_roles || [])
const byRoleId = computed(() => Object.fromEntries(roles.value.map((role) => [role.id, role])))
const selected = computed(() => travelers.value.find((traveler) => traveler.id === selectedId.value) || null)
const recommendedIds = computed(() => props.view.traveler_recommended || [])
const recommended = computed(() => recommendedIds.value.map((id) => byRoleId.value[id]).filter(Boolean))
const otherRoles = computed(() => roles.value.filter((role) => !recommendedIds.value.includes(role.id)))
const busy = computed(() => props.pending.some((key) => key.startsWith('traveler:')))

function select(traveler) {
  selectedId.value = traveler.id
  draftAlign.value = traveler.align || 'good'
}

function add() {
  const trimmed = name.value.trim()
  if (!props.connected || busy.value || !trimmed) return
  emit('add', trimmed)
  name.value = ''
}

function setAlign(align) {
  draftAlign.value = align
  if (selected.value?.role_id) {
    emit('assign', { id: selected.value.id, role: selected.value.role_id, align })
  }
}

function assign(role) {
  if (!selected.value || !props.connected || busy.value) return
  emit('assign', { id: selected.value.id, role, align: draftAlign.value })
}

function clearExileArm() {
  armedExile.value = null
  if (exileTimer) clearTimeout(exileTimer)
  exileTimer = null
}

function setExile(traveler) {
  if (!props.connected || busy.value) return
  if (traveler.exiled) {
    clearExileArm()
    emit('set-exile', { id: traveler.id, exiled: false })
    return
  }
  if (armedExile.value === traveler.id) {
    clearExileArm()
    emit('set-exile', { id: traveler.id, exiled: true })
    return
  }
  clearExileArm()
  armedExile.value = traveler.id
  exileTimer = setTimeout(clearExileArm, 3000)
}

watch(() => props.connected, (connected) => { if (!connected) clearExileArm() })
onBeforeUnmount(clearExileArm)
</script>

<template>
  <div class="panel-content traveler-panel">
    <div>
      <p class="panel-eyebrow">说书人管理</p>
      <h2>🎒 旅行者</h2>
      <p class="inline-note">流放需 {{ view.exile_quorum }} 票；说书人可随时添加、指派与代管。</p>
    </div>
    <form class="admin-inline-form" @submit.prevent="add">
      <input v-model="name" data-traveler-name class="input" maxlength="20" placeholder="旅行者名字" :disabled="!connected || busy">
      <button data-traveler-add class="btn" type="submit" :disabled="!connected || busy || !name.trim()">添加</button>
    </form>
    <p v-if="error?.key?.startsWith('traveler:')" class="inline-error">{{ error.message }}</p>
    <p v-if="!travelers.length" class="inline-note">暂无旅行者。满座或迟到的玩家也可从手机以旅行者身份加入。</p>
    <div v-for="traveler in travelers" :key="traveler.id" class="traveler-row">
      <div class="traveler-row-heading">
        <strong>{{ traveler.name }}</strong>
        <span>{{ byRoleId[traveler.role_id]?.name || '未指派' }} · {{ traveler.align === 'evil' ? '邪恶' : '善良' }}</span>
      </div>
      <p class="inline-note">{{ traveler.exiled ? '已流放' : traveler.alive ? '存活' : '死亡' }}{{ traveler.dead_vote_used ? ' · 死票已交' : '' }}</p>
      <div class="admin-actions">
        <button :data-traveler-select="traveler.id" class="btn" type="button" @click="select(traveler)">指派</button>
        <button :data-traveler-alive="traveler.id" class="btn" type="button" :disabled="!connected || busy || traveler.exiled || !traveler.role_id" @click="emit('toggle-alive', traveler.id)">{{ traveler.alive ? '标记死亡' : '复活' }}</button>
        <button :data-traveler-exile="traveler.id" class="btn" type="button" :disabled="!connected || busy" :aria-pressed="armedExile === traveler.id" @click="setExile(traveler)">{{ traveler.exiled ? '撤销流放' : armedExile === traveler.id ? '确认流放？' : '流放' }}</button>
      </div>
    </div>
    <section v-if="selected" class="traveler-picker">
      <h3>指派 {{ selected.name }}</h3>
      <p class="inline-note">角色公开，阵营仅说书人和旅行者本人知道。</p>
      <div class="admin-actions">
        <button v-for="align in ['good', 'evil']" :key="align" :data-traveler-align="align" class="btn" :class="{ primary: draftAlign === align }" type="button" :disabled="!connected || busy" @click="setAlign(align)">{{ align === 'good' ? '善良' : '邪恶' }}</button>
      </div>
      <p v-if="recommended.length" class="panel-eyebrow">本板推荐</p>
      <div class="admin-actions">
        <button v-for="role in recommended" :key="role.id" :data-traveler-role="role.id" class="btn" type="button" :disabled="!connected || busy" :title="role.ability" @click="assign(role.id)">{{ role.name }}</button>
      </div>
      <p v-if="otherRoles.length" class="panel-eyebrow">其他旅行者</p>
      <div class="admin-actions">
        <button v-for="role in otherRoles" :key="role.id" :data-traveler-role="role.id" class="btn" type="button" :disabled="!connected || busy" :title="role.ability" @click="assign(role.id)">{{ role.name }}</button>
      </div>
    </section>
  </div>
</template>
