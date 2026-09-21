<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits(['set-room', 'load-save', 'reset-game'])
const roomCode = ref(props.view.room_code)
const armed = ref(null)
let timer = null

watch(() => props.view.room_code, (value) => { roomCode.value = value })
watch(() => props.connected, (connected) => { if (!connected) clearArm() })
onBeforeUnmount(clearArm)

function clearArm() {
  armed.value = null
  if (timer) clearTimeout(timer)
  timer = null
}

function setRoom() {
  const code = roomCode.value.trim()
  if (!props.connected || !/^\d{4}$/.test(code) || code === props.view.room_code) return
  emit('set-room', code)
}

function confirm(action) {
  if (!props.connected || props.pending.length) return
  if (armed.value === action) {
    clearArm()
    emit(action === 'load' ? 'load-save' : 'reset-game')
    return
  }
  clearArm()
  armed.value = action
  timer = setTimeout(clearArm, 3000)
}
</script>

<template>
  <div class="panel-content session-panel">
    <div><p class="panel-eyebrow">说书人管理</p><h2>房间与存档</h2></div>
    <label class="field-row">房间号
      <input v-model="roomCode" data-room-code class="input" maxlength="4" inputmode="numeric" :disabled="!connected">
    </label>
    <div class="admin-actions">
      <button data-room-apply class="btn" type="button" :disabled="!connected || !/^\d{4}$/.test(roomCode.trim()) || roomCode === view.room_code" @click="setRoom">修改房间号</button>
      <button class="btn" type="button" :disabled="!connected" @click="roomCode = String(Math.floor(Math.random() * 10000)).padStart(4, '0')">随机生成</button>
    </div>
    <p class="inline-note">改号后请把新号码告诉尚未加入的玩家；已加入者会保持连接。</p>
    <p v-if="error?.key && ['room', 'load', 'reset'].includes(error.key)" class="inline-error">{{ error.message }}</p>
    <section class="session-danger-zone">
      <h3>存档操作</h3>
      <p class="inline-note">读档会用磁盘上的上次自动存档覆盖当前内存状态。重置会清空本局；重置本身不写盘。</p>
      <button data-session-load class="btn" type="button" :disabled="!connected || !!pending.length" :aria-pressed="armed === 'load'" @click="confirm('load')">{{ armed === 'load' ? '确认从磁盘读档？' : '从磁盘读档' }}</button>
      <button data-session-reset class="btn danger" type="button" :disabled="!connected || !!pending.length" :aria-pressed="armed === 'reset'" @click="confirm('reset')">{{ armed === 'reset' ? '确认重置本局？' : '重置本局' }}</button>
    </section>
  </div>
</template>
