<script setup>
import { ref } from 'vue'
import { api } from '../services/api.js'

const emit = defineEmits(['authenticated', 'back'])
const mode = ref('login')
const username = ref('')
const password = ref('')
const recoveryCode = ref('')
const recoveryInput = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  if (!username.value.trim() || !password.value) return
  busy.value = true
  error.value = ''
  try {
    const payload = mode.value === 'reset'
      ? { username: username.value.trim(), recovery_code: recoveryInput.value.trim(), new_password: password.value }
      : { username: username.value.trim(), password: password.value }
    const result = await api(`/api/account/${mode.value === 'reset' ? 'reset-password' : mode.value}`, {
      method: 'POST', body: JSON.stringify(payload),
    })
    password.value = ''
    recoveryInput.value = ''
    if (mode.value !== 'login') recoveryCode.value = result.recovery_code
    else emit('authenticated')
  } catch (cause) {
    error.value = cause.message || '操作失败'
  } finally {
    busy.value = false
  }
}

function done() {
  recoveryCode.value = ''
  emit('authenticated')
}
</script>

<template>
  <main data-account-page class="page center">
    <h1>玩家账户</h1>
    <p class="sub">可继续以游客身份游玩；注册账户可跨设备找回座位并保存个人历史。</p>
    <p class="inline-note">当前为 HTTP 小规模测试：请使用测试专用密码，不要复用重要账户密码。</p>
    <template v-if="recoveryCode">
      <p>请妥善保存账户恢复码；只会显示这一次。</p>
      <strong data-account-recovery-code>{{ recoveryCode }}</strong>
      <button data-account-done class="btn primary" type="button" @click="done">已保存，进入游戏</button>
    </template>
    <template v-else>
      <div class="admin-actions">
        <button data-mode-login class="btn" type="button" @click="mode = 'login'">登录</button>
        <button data-mode-register class="btn" type="button" @click="mode = 'register'">注册</button>
        <button data-mode-reset class="btn" type="button" @click="mode = 'reset'">忘记密码</button>
      </div>
      <form class="join-form" @submit.prevent="submit">
        <input v-model="username" data-username class="input" autocomplete="username" placeholder="用户名" maxlength="64">
        <input v-if="mode === 'reset'" v-model="recoveryInput" data-account-recovery-input class="input" autocomplete="off" placeholder="账户恢复码">
        <input v-model="password" data-password class="input" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" placeholder="密码（至少 8 位）">
        <button data-account-submit class="btn primary" type="submit" :disabled="busy">{{ mode === 'register' ? '注册' : mode === 'reset' ? '重设密码' : '登录' }}</button>
      </form>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="btn" type="button" @click="emit('back')">返回游客加入</button>
    </template>
  </main>
</template>
