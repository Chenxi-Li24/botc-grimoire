<script setup>
import { ref } from 'vue'
import { api } from '../services/api.js'

const emit = defineEmits(['joined', 'account'])

const hashQuery = window.location.hash.split('?')[1] || ''
const name = ref('')
const roomCode = ref(new URLSearchParams(hashQuery).get('room') || '')
const error = ref('')
const submitting = ref(false)

async function join() {
  const cleanName = name.value.trim()
  const cleanRoomCode = roomCode.value.trim()
  error.value = ''

  if (!cleanName) return
  if (!/^\d{4}$/.test(cleanRoomCode)) {
    error.value = '房间号需为 4 位数字'
    return
  }

  submitting.value = true
  try {
    const result = await api('/api/join', {
      method: 'POST',
      body: JSON.stringify({ name: cleanName, room_code: cleanRoomCode }),
    })
    emit('joined', result.player_id)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加入失败'
    submitting.value = false
  }
}
</script>

<template>
  <main class="page center">
    <h1>🩸 血染钟楼</h1>
    <p class="sub">输入名字和房间号加入本局，然后选座入座</p>
    <form class="join-form" @submit.prevent="join">
      <input
        v-model="name"
        data-name
        class="input"
        placeholder="你的名字"
        maxlength="20"
        autofocus
      >
      <input
        v-model="roomCode"
        data-room
        class="input"
        placeholder="房间号(4位数字)"
        maxlength="4"
        inputmode="numeric"
      >
      <button data-submit class="btn primary" :disabled="submitting" type="submit">
        {{ submitting ? '加入中…' : '加入' }}
      </button>
    </form>
    <p data-error class="error" :hidden="!error">{{ error }}</p>
    <button data-account-entry class="btn" type="button" @click="emit('account')">账户登录或注册</button>
    <span class="credit">botc-grimoire · github.com/Chenxi-Li24/botc-grimoire</span>
  </main>
</template>
