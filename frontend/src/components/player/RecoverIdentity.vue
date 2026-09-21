<script setup>
import { ref } from 'vue'
import { api } from '../../services/api.js'

const props = defineProps({ initialRoom: { type: String, default: '' } })
const emit = defineEmits(['recovered', 'back'])
const roomCode = ref(props.initialRoom)
const code = ref('')
const error = ref('')
const busy = ref(false)

async function recover() {
  if (!/^\d{4}$/.test(roomCode.value.trim()) || !code.value.trim()) {
    error.value = '请填写四位房间号和续接码'
    return
  }
  busy.value = true
  error.value = ''
  try {
    await api('/api/recover-participant', {
      method: 'POST',
      body: JSON.stringify({ room_code: roomCode.value.trim(), code: code.value.trim() }),
    })
    code.value = ''
    emit('recovered')
  } catch (cause) {
    error.value = cause.message || '找回失败'
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <section data-recover-identity>
    <h2>找回本局身份</h2>
    <p>请向说书人索取本局一次性续接码。不会改变原座位或角色。</p>
    <form class="join-form" @submit.prevent="recover">
      <input v-model="roomCode" data-recovery-room class="input" placeholder="房间号" inputmode="numeric" maxlength="4">
      <input v-model="code" data-recovery-code class="input" placeholder="一次性续接码" autocomplete="off">
      <button data-recovery-submit class="btn primary" type="submit" :disabled="busy">找回身份</button>
    </form>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <button class="btn" type="button" @click="emit('back')">返回加入</button>
  </section>
</template>
