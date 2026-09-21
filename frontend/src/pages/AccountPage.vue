<script setup>
import { ref } from 'vue'
import { api } from '../services/api.js'

defineProps({ account: { type: String, default: null } })
const emit = defineEmits(['authenticated', 'back', 'history'])
const mode = ref('login')
const username = ref('')
const password = ref('')
const recoveryCode = ref('')
const recoveryInput = ref('')
const error = ref('')
const busy = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const notice = ref('')

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

async function changePassword() {
  if (!oldPassword.value || !newPassword.value) return
  busy.value = true
  error.value = ''
  notice.value = ''
  try {
    await api('/api/account/change-password', {
      method: 'POST',
      body: JSON.stringify({ old_password: oldPassword.value, new_password: newPassword.value }),
    })
    notice.value = '密码已修改'
    oldPassword.value = ''
    newPassword.value = ''
  } catch (cause) {
    error.value = cause.message || '修改失败'
  } finally {
    busy.value = false
  }
}

async function logout(all = false) {
  busy.value = true
  error.value = ''
  try {
    await api(`/api/account/${all ? 'logout-all' : 'logout'}`, { method: 'POST' })
    emit('authenticated')
  } catch (cause) {
    error.value = cause.message || '退出失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main data-account-page class="page center">
    <h1>玩家账户</h1>
    <p class="sub">可继续以游客身份游玩；注册账户可跨设备找回座位并保存个人历史。</p>
    <p class="inline-note">当前为 HTTP 小规模测试：请使用测试专用密码，不要复用重要账户密码。</p>
    <template v-if="account && !recoveryCode">
      <p class="inline-note">已登录账户：{{ account }}</p>
      <button data-account-history class="btn" type="button" @click="emit('history')">我的对局历史</button>
      <form class="join-form" @submit.prevent="changePassword">
        <input v-model="oldPassword" data-old-password class="input" type="password" autocomplete="current-password" placeholder="原密码">
        <input v-model="newPassword" data-new-password class="input" type="password" autocomplete="new-password" placeholder="新密码（至少 8 位）">
        <button data-change-password class="btn primary" type="submit" :disabled="busy">修改密码</button>
      </form>
      <p v-if="notice" class="inline-note">{{ notice }}</p>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <div class="admin-actions">
        <button data-account-logout class="btn" type="button" :disabled="busy" @click="logout(false)">退出此设备</button>
        <button data-account-logout-all class="btn" type="button" :disabled="busy" @click="logout(true)">退出所有设备</button>
      </div>
      <button class="btn" type="button" @click="emit('back')">返回游戏</button>
    </template>
    <template v-else-if="recoveryCode">
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
