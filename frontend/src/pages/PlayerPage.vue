<script setup>
import { computed, ref } from 'vue'
import PlayerBoard from '../components/player/PlayerBoard.vue'
import InferenceEditor from '../components/player/InferenceEditor.vue'
import PlayerChat from '../components/player/PlayerChat.vue'
import PlayerDayAction from '../components/player/PlayerDayAction.vue'
import PlayerLobby from '../components/player/PlayerLobby.vue'
import PlayerNightAction from '../components/player/PlayerNightAction.vue'
import PlayerResult from '../components/player/PlayerResult.vue'
import PlayerRoleCard from '../components/player/PlayerRoleCard.vue'
import PlayerShell from '../components/player/PlayerShell.vue'
import PublicTimeline from '../components/player/PublicTimeline.vue'
import { usePlayerActions } from '../composables/usePlayerActions.js'
import { usePlayerView } from '../composables/usePlayerView.js'
import { createPlayerService } from '../services/player.js'

const props = defineProps({
  playerId: {
    type: String,
    required: true,
  },
  account: { type: String, default: null },
})
const emit = defineEmits(['invalid', 'account', 'history'])

const { view, connectionStatus } = usePlayerView(props.playerId, {
  onInvalid: (code) => emit('invalid', code),
})
const connected = computed(() => connectionStatus.value === 'connected')
const service = createPlayerService(props.playerId)
const { pending, error, run } = usePlayerActions({ service, connected })
const selectedParticipant = ref(null)
const inferenceMode = ref(false)
const playerChat = ref(null)

async function handleChatCommand(command) {
  const cid = command.cid ?? 'new'
  const operations = {
    create: () => service.createChat(command.invitees),
    'respond-invite': () => service.respondInvite(command.cid, command.accept),
    request: () => service.requestChat(command.cid),
    'invite-more': () => service.inviteMore(command.cid, command.invitees),
    approve: () => service.approveRequest(command.cid, command.who, command.approve),
    send: () => service.sendChat(command.cid, command.text),
    leave: () => service.leaveChat(command.cid),
    close: () => service.closeChat(command.cid),
  }
  const operation = operations[command.type]
  if (!operation) return
  const response = await run(`chat:${command.type}:${cid}`, operation)
  if (response && command.type === 'send') playerChat.value?.markSent(command.text)
}

function saveInference(command) {
  const clientId = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`
  return run('inference', () => service.recordInference({ ...command, client_id: clientId }))
}
</script>

<template>
  <main v-if="!view" data-player-page class="page center">
    <p v-if="!view">
      {{ connectionStatus === 'reconnecting' ? '正在重新连接…' : '正在连接房间…' }}
    </p>
  </main>
  <PlayerShell v-else data-player-page :view="view" :connection-status="connectionStatus">
    <template #header-actions>
      <div class="player-account-actions">
        <button v-if="!account" data-open-account class="btn" type="button" @click="emit('account')">绑定账户</button>
        <button v-else data-open-history class="btn" type="button" @click="emit('history')">我的历史</button>
      </div>
    </template>
    <p v-if="error" class="error" role="alert">{{ error.message }}</p>
    <div v-if="view.status === 'playing' || view.result" class="inference-mode-actions">
      <button data-inference-toggle class="btn" :class="{ primary: inferenceMode }" type="button" @click="inferenceMode = !inferenceMode">{{ inferenceMode ? '返回对局' : '打开我的推理魔典' }}</button>
    </div>
    <template v-if="inferenceMode">
      <PlayerBoard :view="view" inference-mode @select-participant="selectedParticipant = $event" />
      <InferenceEditor v-if="selectedParticipant !== null" :view="view" :target="selectedParticipant" :connected="connected && !view.result" @submit="saveInference" />
      <p v-else class="inline-note">点击任意座位记录推测，线下空座也可以标记。只有你和说书人能看到。</p>
    </template>
    <template v-else>
    <PlayerResult v-if="view.result" :view="view" />
    <PlayerLobby
      v-else-if="view.status === 'lobby' || (view.me?.seat == null && !view.traveler)"
      :view="view"
      :connected="connected"
      :pending="pending"
      @sit="run('sit', () => service.sit($event))"
      @wish="run('wish', () => service.setWish($event))"
      @traveler="run('traveler', () => service.joinTraveler())"
    />
    <template v-else>
      <PlayerBoard :view="view" @select-participant="selectedParticipant = $event" />
      <PlayerNightAction
        v-if="view.phase === 'night'"
        :view="view"
        :connected="connected"
        :pending="pending"
        @submit="run('night-action', () => service.submitNightAction($event))"
      />
      <PlayerDayAction
        v-if="view.phase === 'day'"
        :view="view"
        :connected="connected"
        :pending="pending"
        :selected-participant="selectedParticipant"
        @nominate="run('nominate', () => service.nominate($event))"
        @vote="run('vote', () => service.vote())"
      />
      <PlayerChat
        v-if="view.phase === 'day' && view.chat"
        ref="playerChat"
        :chat="view.chat"
        :seats="view.seats"
        :travelers="view.travelers_public"
        :day-stage="view.day_stage"
        :connected="connected"
        :pending="pending"
        @command="handleChatCommand"
      />
      <PublicTimeline :view="view" />
      <PlayerRoleCard :view="view" />
    </template>
    </template>
  </PlayerShell>
</template>

<style scoped>
.inference-mode-actions { display: flex; justify-content: flex-end; }
</style>
