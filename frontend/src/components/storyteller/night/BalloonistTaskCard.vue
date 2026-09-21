<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  step: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  execute: { type: Function, required: true },
})

const target = ref('')
const registeredType = ref('')
const registeredRole = ref('')
const truthful = ref('')
const preview = ref(null)
const localError = ref('')
const sent = ref(false)

const context = computed(() => props.view.balloonist_context || {})
const candidates = computed(() => context.value.candidates || [])
const choice = computed(() => candidates.value.find((item) => String(item.target) === target.value))
const allowedTypes = computed(() => choice.value?.allowed_types || choice.value?.options || [])
const chosenType = computed(() => registeredType.value || (
  allowedTypes.value.length === 1 ? allowedTypes.value[0] : ''
))
const alternateRole = computed(() => choice.value && chosenType.value
  && chosenType.value !== choice.value.real_type)
const rolesForType = computed(() => (props.view.roles || [])
  .filter((item) => item.team === chosenType.value))
const busy = computed(() => props.pending.some((key) => key.startsWith('night:balloonist')))
const requiresTruth = computed(() => Boolean(context.value.impairments?.length))
const canPreview = computed(() => Boolean(
  props.connected && !busy.value && target.value && chosenType.value
  && (!alternateRole.value || registeredRole.value)
  && (!requiresTruth.value || truthful.value !== ''),
))
const currentHistory = computed(() => (props.view.balloonist_history || [])
  .filter((item) => item.night_no === props.view.night_no && !item.retracted)
  .at(-1) || null)

watch([target, registeredType, registeredRole, truthful, () => props.step.id], () => {
  preview.value = null
  localError.value = ''
  sent.value = false
})

function chooseTarget() {
  registeredType.value = ''
  registeredRole.value = ''
}

function chooseType() {
  registeredRole.value = ''
}

function payload(action) {
  const raw = target.value
  return {
    action,
    step_id: props.step.id,
    target: /^\d+$/.test(raw) ? Number(raw) : raw,
    ...(chosenType.value && ['recluse', 'spy'].includes(choice.value?.real_role)
      ? { registered_type: chosenType.value }
      : registeredType.value ? { registered_type: registeredType.value } : {}),
    ...(registeredRole.value ? { registered_role: registeredRole.value } : {}),
    ...(truthful.value === '' ? {} : { truthful: truthful.value === 'true' }),
    ...(action === 'send' && currentHistory.value
      ? { correction_of: currentHistory.value.event_id } : {}),
  }
}

async function execute(action) {
  if (!canPreview.value || (action === 'send' && !preview.value)) return
  localError.value = ''
  try {
    const response = await props.execute(payload(action))
    if (!response?.result) return
    if (action === 'preview') preview.value = response.result
    else {
      sent.value = true
      preview.value = null
    }
  } catch (error) {
    localError.value = error?.message || '操作失败'
  }
}

function typeName(type) {
  return ({ townsfolk: '镇民', outsider: '外来者', minion: '爪牙', demon: '恶魔',
    traveler: '旅行者' })[type] || type || '未记录'
}
</script>

<template>
  <section class="night-card balloonist-card" data-balloonist-card>
    <div class="night-card-heading"><h4>气球驾驶员（{{ view.balloonist_version === 'old' ? '旧版' : '新版' }}）</h4><span>逐夜单条信息</span></div>
    <p v-if="view.balloonist_version === 'old'">依次给出此前未登记过的类型；类型用尽后不再发信。</p>
    <p v-else>本夜目标的登记类型须与上次有效信息不同。</p>
    <p v-if="context.previous_type">上次有效登记：{{ typeName(context.previous_type) }}</p>
    <p v-if="context.used_types?.length">已用登记类型：{{ context.used_types.map(typeName).join('、') }}</p>

    <p v-if="view.balloonist_version == null" class="inline-warning">旧局未指定气球驾驶员版本，请由说书人按旧流程手动裁定。</p>
    <p v-else-if="context.exhausted" class="inline-note">旧版登记类型已用尽，本夜无需再发送信息。</p>
    <p v-else-if="!candidates.length" class="inline-note">当前没有可判定的目标，请由说书人人工裁定。</p>
    <template v-else>
      <label class="field-row">本夜给哪名玩家
        <select v-model="target" data-balloonist-target :disabled="!connected || busy" @change="chooseTarget">
          <option value="">请选择座位或旅行者</option>
          <option v-for="candidate in candidates" :key="candidate.target" :value="String(candidate.target)">
            {{ candidate.target_label }} · {{ candidate.real_role_name || candidate.real_role }}
          </option>
        </select>
      </label>
      <label v-if="choice && (choice.options?.length > 1 || allowedTypes.length > 1)" class="field-row">本次登记类型
        <select v-model="registeredType" data-balloonist-registration :disabled="!connected || busy" @change="chooseType">
          <option value="">请明确选择本次登记</option>
          <option v-for="type in (choice.options || allowedTypes)" :key="type" :value="type">
            {{ typeName(type) }}{{ (choice.rule_compliant_types || allowedTypes).includes(type) ? '' : '（当前顺序不符）' }}
          </option>
        </select>
      </label>
      <label v-if="alternateRole" class="field-row">本次登记角色
        <select v-model="registeredRole" data-balloonist-role :disabled="!connected || busy">
          <option value="">请选择角色</option>
          <option v-for="role in rolesForType" :key="role.id" :value="role.id">{{ role.name }}</option>
        </select>
      </label>
      <label class="field-row">本次信息真假（异常状态时必选）
        <select v-model="truthful" data-balloonist-truth :disabled="!connected || busy">
          <option value="">正常自动判定</option>
          <option value="true">正确</option>
          <option value="false">错误</option>
        </select>
      </label>
      <p v-if="requiresTruth" class="state-alert">当前信息受 {{ context.impairments.join('、') }} 影响，请明确标记正确或错误。</p>
      <button class="btn" type="button" :disabled="!canPreview" @click="execute('preview')">确认预览</button>
      <section v-if="preview" class="night-card balloonist-preview">
        <h5>发送前核对</h5>
        <p>第 {{ preview.night_no }} 夜 → {{ preview.target_label }}</p>
        <p>真实类型：{{ typeName(preview.real_type) }}（{{ preview.real_role_name }}）</p>
        <p>登记类型：{{ typeName(preview.registered_type) }} · {{ preview.registered_role }}</p>
        <p>登记来源：{{ preview.registration_reason }}</p>
        <p>信息：{{ preview.truthful ? '正确' : '错误' }}；{{ preview.rule_compliant ? '符合当前顺序' : '不符合当前顺序' }}</p>
        <p v-if="preview.impairments?.length" class="state-alert">异常状态：{{ preview.impairments.join('、') }}</p>
        <button class="btn primary" type="button" :disabled="!connected || busy" @click="execute('send')">
          {{ currentHistory ? '更正并发送给玩家' : '发送给玩家' }}
        </button>
      </section>
      <p v-if="sent" class="inline-note" role="status">本夜信息已发送，玩家端仅显示目标。</p>
    </template>
    <p v-if="localError" class="inline-error" role="alert">{{ localError }}</p>

    <details v-if="view.balloonist_history?.length" open class="balloonist-history">
      <summary>前几夜已发送记录（仅说书人可见）</summary>
      <p v-for="record in view.balloonist_history" :key="record.event_id">
        第 {{ record.night_no }} 夜 → {{ record.target_label }}；真实：{{ typeName(record.real_type) }} / {{ record.real_role_name }}；登记：{{ typeName(record.registered_type) }} / {{ record.registered_role }}；{{ record.truthful ? '标记正确' : '标记错误' }}<span v-if="record.impairments?.length">；状态：{{ record.impairments.join('、') }}</span><span v-if="record.retracted">；已撤回</span><span v-if="record.correction_of">；更正前次</span>
      </p>
    </details>
  </section>
</template>

<style scoped>
.balloonist-card { display: grid; gap: 10px; }
.balloonist-card p { margin: 0; }
.balloonist-card .field-row { display: grid; gap: 5px; }
.balloonist-card select { width: 100%; }
.balloonist-preview { display: grid; gap: 7px; }
.balloonist-history { line-height: 1.55; }
.balloonist-history p { margin-top: 8px; }
</style>
