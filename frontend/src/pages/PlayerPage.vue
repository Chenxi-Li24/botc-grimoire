<script setup>
import { computed, ref } from 'vue'
import PlayerBoard from '../components/player/PlayerBoard.vue'
import PlayerLobby from '../components/player/PlayerLobby.vue'
import PlayerRoleCard from '../components/player/PlayerRoleCard.vue'
import PlayerShell from '../components/player/PlayerShell.vue'
import { usePlayerActions } from '../composables/usePlayerActions.js'
import { usePlayerView } from '../composables/usePlayerView.js'
import { createPlayerService } from '../services/player.js'

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
const connected = computed(() => connectionStatus.value === 'connected')
const service = createPlayerService(props.playerId)
const { pending, error, run } = usePlayerActions({ service, connected })
const selectedParticipant = ref(null)
</script>

<template>
  <main v-if="!view" data-player-page class="page center">
    <p v-if="!view">
      {{ connectionStatus === 'reconnecting' ? '正在重新连接…' : '正在连接房间…' }}
    </p>
  </main>
  <PlayerShell v-else data-player-page :view="view" :connection-status="connectionStatus">
    <p v-if="error" class="error" role="alert">{{ error.message }}</p>
    <PlayerLobby
      v-if="view.status === 'lobby' || (view.me?.seat == null && !view.traveler)"
      :view="view"
      :connected="connected"
      :pending="pending"
      @sit="run('sit', () => service.sit($event))"
      @wish="run('wish', () => service.setWish($event))"
      @traveler="run('traveler', () => service.joinTraveler())"
    />
    <template v-else>
      <PlayerBoard :view="view" @select-participant="selectedParticipant = $event" />
      <PlayerRoleCard :view="view" />
    </template>
  </PlayerShell>
</template>
