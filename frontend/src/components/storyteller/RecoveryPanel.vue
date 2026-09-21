<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  service: { type: Object, required: true },
  connected: { type: Boolean, default: false },
})
const playerId = ref('')
const code = ref('')
const error = ref('')
const busy = ref(false)
const selected = computed(() => props.view.players?.find((player) => player.id === playerId.value))

watch(playerId, () => { code.value = ''; error.value = '' })

async function issue() {
  if (!props.connected || !playerId.value || busy.value) return
  busy.value = true
  code.value = ''
  error.value = ''
  try {
    const result = await props.service.issueRecoveryCode(playerId.value)
    code.value = result.code
  } catch (cause) {
    error.value = cause.message || '续接码生成失败'
  } finally {
    busy.value = false
  }
}

async function revoke() {
  if (!props.connected || !playerId.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await props.service.revokeGuestSessions(playerId.value)
    code.value = ''
  } catch (cause) {
    error.value = cause.message || '撤销失败'
  } finally {
    busy.value = false
  }
}

async function copyCode() {
  if (code.value && navigator.clipboard?.writeText) await navigator.clipboard.writeText(code.value)
}
</script>

<template>
  <section class="panel-content recovery-panel">
    <h3>找回本局身份</h3>
    <p class="inline-note">仅用于游客换设备或掉线后无法恢复。账户玩家请直接登录。</p>
    <label class="field-row">选择玩家
      <select v-model="playerId" data-recovery-player class="input" :disabled="!connected || busy">
        <option value="">请选择</option>
        <option v-for="player in view.players || []" :key="player.id" :value="player.id">
          {{ player.name }}{{ player.seat ? `（${player.seat} 号座）` : '（未入座）' }}
        </option>
      </select>
    </label>
    <button data-issue-recovery class="btn" type="button" :disabled="!connected || !playerId || busy" @click="issue">生成一次性续接码</button>
    <div v-if="code" data-recovery-code class="join-code-card">
      <p>请将此码私下交给 {{ selected?.name }}；10 分钟内有效，仅能使用一次。</p>
      <strong>{{ code }}</strong>
      <button class="btn" type="button" @click="copyCode">复制续接码</button>
    </div>
    <button v-if="playerId" data-revoke-guest class="btn" type="button" :disabled="!connected || busy" @click="revoke">撤销该玩家的游客设备登录</button>
    <p v-if="error" class="inline-error">{{ error }}</p>
  </section>
</template>
