<script setup>
import { usePlayerView } from '../composables/usePlayerView.js'

const props = defineProps({
  playerId: {
    type: String,
    required: true,
  },
})
const emit = defineEmits(['invalid'])

const { view, connectionStatus } = usePlayerView(props.playerId, {
  onInvalid: (code) => emit('invalid', code),
})
</script>

<template>
  <main data-player-page class="page center">
    <p v-if="!view">
      {{ connectionStatus === 'reconnecting' ? '正在重新连接…' : '正在连接房间…' }}
    </p>
    <template v-else>
      <h1>🩸 血染钟楼</h1>
      <p class="sub">房间 {{ view.room_code }}</p>
    </template>
  </main>
</template>
