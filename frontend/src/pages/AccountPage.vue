<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../services/api.js'

const props = defineProps({ account: { type: String, default: null }, protocol: { type: String, default: () => window.location.protocol } })
const emit = defineEmits(['authenticated', 'back', 'history'])
const mode = ref('login')
const loginMode = ref('username')
const username = ref('')
const password = ref('')
const registrationNickname = ref('')
const recoveryCode = ref('')
const registrationUid = ref('')
const recoveryInput = ref('')
const error = ref('')
const busy = ref(false)
const oldPassword = ref('')
const newPassword = ref('')
const notice = ref('')
const profile = ref(null)
const nickname = ref('')
const avatarVersion = ref(0)
const segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' })
const nicknameLength = computed(() => [...segmenter.segment(nickname.value.trim())].length)
const nicknameRemaining = computed(() => 8 - nicknameLength.value)
const avatarSrc = computed(() => profile.value?.has_avatar ? `/api/account/avatar?v=${avatarVersion.value}` : '/default-avatar.svg')
const validPassword = (value) => [...value].length >= 4 && [...value].length <= 128

async function loadProfile() {
  if (!props.account) { profile.value = null; return }
  try {
    profile.value = await api('/api/account/profile')
    nickname.value = profile.value.nickname || ''
  } catch (cause) { error.value = cause.message || '账户资料加载失败' }
}
onMounted(loadProfile)
watch(() => props.account, loadProfile)

async function submit() {
  if (!username.value.trim() || !password.value) return
  if (mode.value !== 'login' && !validPassword(password.value)) {
    error.value = '密码需为 4–128 个字符'; return
  }
  if (mode.value === 'login' && loginMode.value === 'uid' && !/^[1-9][0-9]{3}$/.test(username.value.trim())) {
    error.value = 'UID 需为四位数字'; return
  }
  busy.value = true; error.value = ''
  try {
    const payload = mode.value === 'reset'
      ? { username: username.value.trim(), recovery_code: recoveryInput.value.trim(), new_password: password.value }
      : mode.value === 'login'
        ? { username: username.value.trim(), password: password.value, ...(loginMode.value === 'uid' ? { mode: 'uid' } : {}) }
        : { username: username.value.trim(), password: password.value, ...(registrationNickname.value.trim() ? { nickname: registrationNickname.value.trim() } : {}) }
    const result = await api(`/api/account/${mode.value === 'reset' ? 'reset-password' : mode.value}`, { method: 'POST', body: JSON.stringify(payload) })
    password.value = ''; recoveryInput.value = ''
    if (mode.value !== 'login') { recoveryCode.value = result.recovery_code; registrationUid.value = result.uid || '' }
    else emit('authenticated')
  } catch (cause) { error.value = cause.message || '操作失败' }
  finally { busy.value = false }
}

function done() { recoveryCode.value = ''; emit('authenticated') }

async function copyUid() {
  if (!profile.value?.uid) return
  try { await navigator.clipboard.writeText(profile.value.uid); notice.value = 'UID 已复制' }
  catch { error.value = '复制失败，请手动选择 UID' }
}

async function changeNickname() {
  if (nicknameLength.value < 1 || nicknameLength.value > 8) { error.value = '昵称需为 1–8 个可见字符'; return }
  busy.value = true; error.value = ''; notice.value = ''
  try {
    const result = await api('/api/account/nickname', { method: 'POST', body: JSON.stringify({ nickname: nickname.value.trim() }) })
    profile.value = { ...profile.value, nickname: result.nickname }
    nickname.value = result.nickname
    notice.value = '昵称已更新，本局圆桌会同步显示'
  } catch (cause) { error.value = cause.message || '修改失败' }
  finally { busy.value = false }
}

async function uploadAvatar(event) {
  const file = event.target.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) { error.value = '头像不能超过 2 MiB'; return }
  busy.value = true; error.value = ''; notice.value = ''
  try {
    await api('/api/account/avatar', { method: 'PUT', body: await file.arrayBuffer(), headers: { 'Content-Type': file.type } })
    profile.value = { ...profile.value, has_avatar: true }
    avatarVersion.value += 1
    notice.value = '头像已更新'
  } catch (cause) { error.value = cause.message || '上传失败' }
  finally { busy.value = false; event.target.value = '' }
}

async function changePassword() {
  if (!oldPassword.value || !newPassword.value) return
  if (!validPassword(newPassword.value)) { error.value = '密码需为 4–128 个字符'; return }
  busy.value = true; error.value = ''; notice.value = ''
  try {
    await api('/api/account/change-password', { method: 'POST', body: JSON.stringify({ old_password: oldPassword.value, new_password: newPassword.value }) })
    notice.value = '密码已修改'; oldPassword.value = ''; newPassword.value = ''
  } catch (cause) { error.value = cause.message || '修改失败' }
  finally { busy.value = false }
}

async function logout(all = false) {
  busy.value = true; error.value = ''
  try { await api(`/api/account/${all ? 'logout-all' : 'logout'}`, { method: 'POST' }); emit('authenticated') }
  catch (cause) { error.value = cause.message || '退出失败' }
  finally { busy.value = false }
}
</script>

<template>
  <main data-account-page class="page center">
    <h1>玩家账户</h1>
    <p class="sub">可继续以游客身份游玩；注册账户可跨设备找回座位并保存个人历史。</p>
    <p class="inline-note">{{ protocol === 'https:' ? '当前通过 HTTPS 访问。' : '当前为 HTTP 小规模测试：' }}请使用测试专用密码，不要复用重要账户密码。</p>
    <template v-if="account && !recoveryCode">
      <div v-if="profile" class="account-profile">
        <img data-account-avatar :src="avatarSrc" alt="账户头像" width="72" height="72">
        <p data-account-uid>UID：<strong>{{ profile.uid }}</strong> <button class="btn" type="button" @click="copyUid">复制 UID</button></p>
        <p data-account-username>登录用户名：{{ profile.username }}</p>
        <p>当前昵称：{{ profile.nickname }}</p>
        <p v-if="profile.nickname_conflict" class="inline-note">此旧昵称与其他账户重名；下次改名需选择新昵称。</p>
        <p>自动登录：此访问地址已启用 30 天服务端会话；退出或到期后需重新登录。</p>
        <form class="join-form" @submit.prevent="changeNickname">
          <input v-model="nickname" data-nickname class="input" placeholder="新昵称（最多 8 个可见字符）">
          <small data-nickname-remaining>还可输入 {{ nicknameRemaining }} 个可见字符</small>
          <button data-change-nickname class="btn" type="button" :disabled="busy" @click="changeNickname">修改昵称</button>
        </form>
        <label class="btn">上传或更换头像（PNG/JPEG/WebP，最多 2 MiB）<input data-avatar-upload type="file" accept="image/png,image/jpeg,image/webp" hidden @change="uploadAvatar"></label>
      </div>
      <p v-else class="inline-note">已登录账户：{{ account }}</p>
      <button data-account-history class="btn" type="button" @click="emit('history')">我的对局历史</button>
      <form class="join-form" @submit.prevent="changePassword">
        <input v-model="oldPassword" data-old-password class="input" type="password" autocomplete="current-password" placeholder="原密码">
        <input v-model="newPassword" data-new-password class="input" type="password" autocomplete="new-password" placeholder="新密码（4–128 个字符）">
        <button data-change-password class="btn primary" type="button" :disabled="busy" @click="changePassword">修改密码</button>
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
      <p v-if="registrationUid">你的登录 UID：<strong data-registered-uid>{{ registrationUid }}</strong></p>
      <strong data-account-recovery-code>{{ recoveryCode }}</strong>
      <button data-account-done class="btn primary" type="button" @click="done">已保存，进入游戏</button>
    </template>
    <template v-else>
      <div class="admin-actions">
        <button data-mode-login class="btn" type="button" @click="mode = 'login'">登录</button>
        <button data-mode-register class="btn" type="button" @click="mode = 'register'">注册</button>
        <button data-mode-reset class="btn" type="button" @click="mode = 'reset'">忘记密码</button>
      </div>
      <div v-if="mode === 'login'" class="admin-actions" aria-label="登录方式">
        <button data-login-username class="btn" type="button" :aria-pressed="loginMode === 'username'" @click="loginMode = 'username'">用户名登录</button>
        <button data-login-uid class="btn" type="button" :aria-pressed="loginMode === 'uid'" @click="loginMode = 'uid'">UID 登录</button>
      </div>
      <form class="join-form" @submit.prevent="submit">
        <input v-model="username" data-username class="input" autocomplete="username" :placeholder="mode === 'login' && loginMode === 'uid' ? '四位 UID' : '用户名'" :inputmode="mode === 'login' && loginMode === 'uid' ? 'numeric' : undefined" maxlength="64">
        <input v-if="mode === 'register'" v-model="registrationNickname" data-registration-nickname class="input" placeholder="显示昵称（默认用户名，最多 8 个可见字符）">
        <input v-if="mode === 'reset'" v-model="recoveryInput" data-account-recovery-input class="input" autocomplete="off" placeholder="账户恢复码">
        <input v-model="password" data-password class="input" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" :placeholder="mode === 'login' ? '密码' : '密码（4–128 个字符）'">
        <button data-account-submit class="btn primary" type="submit" :disabled="busy">{{ mode === 'register' ? '注册' : mode === 'reset' ? '重设密码' : '登录' }}</button>
      </form>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="btn" type="button" @click="emit('back')">返回游客加入</button>
    </template>
  </main>
</template>

<style scoped>
.account-profile { display: grid; justify-items: center; gap: 6px; max-width: 420px; }
.account-profile p { margin: 2px 0; }
.account-profile img { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; background: var(--panel); }
.account-profile small { color: var(--dim); }
</style>
