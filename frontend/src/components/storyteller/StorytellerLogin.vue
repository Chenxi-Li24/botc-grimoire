<script setup>
import { ref } from 'vue'
import { api } from '../../services/api.js'
import { setStorytellerPassword } from '../../services/session.js'

const emit = defineEmits(['authenticated'])
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function login() {
  error.value = ''
  submitting.value = true
  try {
    const result = await api('/api/login', {
      method: 'POST',
      body: JSON.stringify({ password: password.value }),
    })
    if (!result.ok) {
      error.value = '密码错误'
      submitting.value = false
      return
    }
    setStorytellerPassword(password.value)
    emit('authenticated', password.value)
  } catch {
    error.value = '登录失败'
    submitting.value = false
  }
}
</script>

<template>
  <main class="page center">
    <h1>🕯 说书人入口</h1>
    <form class="join-form" @submit.prevent="login">
      <input
        v-model="password"
        data-password
        class="input"
        type="password"
        placeholder="说书人密码"
        autofocus
      >
      <button data-submit class="btn primary" type="submit" :disabled="submitting">
        {{ submitting ? '连接中…' : '进入魔典' }}
      </button>
    </form>
    <p class="hint">默认密码 grimoire，可用环境变量 STORYTELLER_PASSWORD 修改</p>
    <p data-error class="error" :hidden="!error">{{ error }}</p>
  </main>
</template>
