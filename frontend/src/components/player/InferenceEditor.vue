<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  target: { type: [Number, String], required: true },
  connected: { type: Boolean, default: false },
})
const emit = defineEmits(['submit'])
const role = ref('')
const alternative1 = ref('')
const alternative2 = ref('')
const alignment = ref('unknown')
const confidence = ref('medium')
const reason = ref('')
const status = ref('poisoned')
const since = ref('')
const until = ref('')
const claimedRole = ref('')
const changeKind = ref('role')
const changeFrom = ref('')
const changeTo = ref('')

const roles = computed(() => props.view.script_roles || [])
const current = computed(() => (props.view.inference?.current || []).filter((item) => item.target === props.target))
const history = computed(() => (props.view.inference?.events || []).filter((item) => item.target === props.target).slice().reverse())
const targetLabel = computed(() => typeof props.target === 'number' ? `${props.target}号座位` : '旅行者')
const statusLabels = { poisoned: '中毒', drunk: '醉酒', mad: '疯狂' }
const categoryLabels = { role: '角色', alignment: '阵营', status: '状态', change: '变化' }

watch(() => props.target, () => {
  role.value = current.value.find((item) => item.category === 'role')?.data.role || ''
  alignment.value = current.value.find((item) => item.category === 'alignment')?.data.alignment || 'unknown'
  reason.value = ''
  since.value = ''
  until.value = ''
}, { immediate: true })

function send(category, operation, data) {
  if (!props.connected) return
  emit('submit', { target: props.target, category, operation, data })
}

function saveRole() {
  if (!role.value) return
  send('role', 'set', { role: role.value, alternatives: [alternative1.value, alternative2.value].filter(Boolean),
    confidence: confidence.value, reason: reason.value })
}

function saveStatus() {
  send('status', 'set', { status: status.value, since: since.value, until: until.value,
    claimed_role: status.value === 'mad' ? claimedRole.value : '', reason: reason.value })
}

function saveChange() {
  send('change', 'set', { kind: changeKind.value, from: changeFrom.value, to: changeTo.value,
    since: since.value, reason: reason.value })
}

function roleName(id) { return roles.value.find((item) => item.id === id)?.name || id }
function describe(item) {
  if (item.category === 'role') return `${roleName(item.data.role)}${item.data.alternatives?.length ? `（备选 ${item.data.alternatives.map(roleName).join('、')}）` : ''}`
  if (item.category === 'alignment') return ({ good: '善良', evil: '邪恶', unknown: '未知' })[item.data.alignment]
  if (item.category === 'status') return statusLabels[item.data.status] || item.data.status
  return `${item.data.kind === 'role' ? '角色' : '阵营'} ${item.data.from || '未知'} → ${item.data.to || '未知'}`
}
</script>

<template>
  <section data-inference-editor class="inference-editor">
    <header><h2>我的推测 · {{ targetLabel }}</h2><p>仅你和说书人可见，不改变真实游戏状态。</p></header>
    <div class="inference-grid">
      <label>主要角色
        <select v-model="role" data-guess-role><option value="">请选择</option><option v-for="item in roles" :key="item.id" :value="item.id">{{ item.name }}</option></select>
      </label>
      <label>把握程度<select v-model="confidence"><option value="low">低</option><option value="medium">中</option><option value="high">高</option></select></label>
      <label>备选角色一<select v-model="alternative1"><option value="">无</option><option v-for="item in roles" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
      <label>备选角色二<select v-model="alternative2"><option value="">无</option><option v-for="item in roles" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
      <div class="inference-actions"><button class="btn primary" type="button" :disabled="!connected || !role" @click="saveRole">保存角色推测</button><button class="btn" type="button" :disabled="!connected" @click="send('role', 'clear', {})">清除角色推测</button></div>
    </div>
    <div class="inference-grid">
      <label>推测阵营<select v-model="alignment" data-guess-alignment><option value="unknown">未知</option><option value="good">善良</option><option value="evil">邪恶</option></select></label>
      <button class="btn" type="button" :disabled="!connected" @click="send('alignment', 'set', { alignment, reason })">保存阵营推测</button>
    </div>
    <div class="inference-grid">
      <label>异常状态<select v-model="status" data-guess-status><option value="poisoned">中毒</option><option value="drunk">醉酒</option><option value="mad">疯狂</option></select></label>
      <label>推测开始于<input v-model="since" maxlength="100" placeholder="如：第二夜" /></label>
      <label>推测结束于（可留空）<input v-model="until" maxlength="100" placeholder="如：第三天黄昏" /></label>
      <label v-if="status === 'mad'">疯狂声称角色<select v-model="claimedRole"><option value="">未知</option><option v-for="item in roles" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
      <div class="inference-actions"><button class="btn" type="button" :disabled="!connected" @click="saveStatus">记录状态</button><button class="btn" type="button" :disabled="!connected" @click="send('status', 'end', { status })">结束这项推测</button></div>
    </div>
    <div class="inference-grid">
      <label>变化类型<select v-model="changeKind"><option value="role">角色变化</option><option value="alignment">阵营变化</option></select></label>
      <template v-if="changeKind === 'role'">
        <label>原角色<select v-model="changeFrom"><option value="">未知</option><option v-for="item in roles" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
        <label>新角色<select v-model="changeTo"><option value="">未知</option><option v-for="item in roles" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
      </template>
      <template v-else>
        <label>原阵营<select v-model="changeFrom"><option value="">未知</option><option value="good">善良</option><option value="evil">邪恶</option></select></label>
        <label>新阵营<select v-model="changeTo"><option value="">未知</option><option value="good">善良</option><option value="evil">邪恶</option></select></label>
      </template>
      <button class="btn" type="button" :disabled="!connected" @click="saveChange">记录变化</button>
    </div>
    <label>依据或备注<textarea v-model="reason" maxlength="500" rows="2" placeholder="记录为什么这样判断" /></label>
    <section class="inference-log"><h3>当前标记</h3><p v-if="!current.length">还没有标记。</p><p v-for="item in current" :key="item.seq">{{ categoryLabels[item.category] }}：{{ describe(item) }}</p></section>
    <section class="inference-log"><h3>修改历史</h3><p v-if="!history.length">还没有记录。</p><p v-for="item in history" :key="item.seq">{{ new Date(item.recorded_at * 1000).toLocaleString() }} · {{ item.phase === 'night' ? `第${item.night_no}夜` : `第${item.day_no}天` }} · {{ item.operation === 'set' ? '设置' : '结束/清除' }}{{ categoryLabels[item.category] }}：{{ describe(item) }}<span v-if="item.data.reason"> · {{ item.data.reason }}</span></p></section>
  </section>
</template>

<style scoped>
.inference-editor { padding: 16px; display: grid; gap: 16px; border: 1px solid var(--line); border-radius: 18px; background: var(--panel); }
.inference-editor header p, .inference-log p { color: var(--dim); font-size: 12px; }
.inference-grid { padding-top: 12px; display: grid; gap: 9px; border-top: 1px solid var(--line); grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }
.inference-editor label { display: grid; gap: 5px; font-size: 12px; }
.inference-editor select, .inference-editor input, .inference-editor textarea { width: 100%; padding: 8px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); color: var(--text); }
.inference-actions { display: flex; gap: 8px; align-items: end; flex-wrap: wrap; }
.inference-log { padding-top: 12px; display: grid; gap: 5px; border-top: 1px solid var(--line); }
.inference-log h3 { font-size: 14px; }
</style>
