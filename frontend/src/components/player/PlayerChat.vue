<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  chat: { type: Object, required: true },
  seats: { type: Array, default: () => [] },
  travelers: { type: Array, default: () => [] },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
const emit = defineEmits(['command'])

const messageDraft = ref('')
const pickerMode = ref(null)
const invitees = ref([])

const busy = computed(() => props.pending.some((key) => key.startsWith('chat:')))
const memberIds = computed(() => new Set((props.chat.my_chat?.members || []).map((item) => String(item.who))))
const candidates = computed(() => {
  const values = [
    ...props.seats
      .filter((slot) => slot.player && !slot.is_me)
      .map((slot) => ({ id: slot.seat, label: `${slot.seat}号 ${slot.player.name}` })),
    ...props.travelers
      .filter((traveler) => !traveler.exiled && String(traveler.id) !== String(props.chat.who))
      .map((traveler) => ({ id: traveler.id, label: `🎒 ${traveler.name}` })),
    { id: 'st', label: '🕯 说书人' },
  ]
  return pickerMode.value === 'invite'
    ? values.filter((item) => !memberIds.value.has(String(item.id)))
    : values
})

function participantName(member) {
  return String(member.who) === 'st' ? '🕯 说书人' : member.name
}

function beginPicker(mode) {
  pickerMode.value = mode
  invitees.value = []
}

function toggleInvitee(id) {
  invitees.value = invitees.value.some((item) => item === id)
    ? invitees.value.filter((item) => item !== id)
    : [...invitees.value, id]
}

function submitPicker() {
  if (!invitees.value.length) return
  const command = pickerMode.value === 'invite'
    ? { type: 'invite-more', cid: props.chat.my_chat.id, invitees: [...invitees.value] }
    : { type: 'create', invitees: [...invitees.value] }
  emit('command', command)
  pickerMode.value = null
  invitees.value = []
}

function send() {
  const text = messageDraft.value.trim()
  if (!text || !props.chat.my_chat) return
  emit('command', { type: 'send', cid: props.chat.my_chat.id, text })
}

function markSent(sentText = null) {
  if (sentText === null || messageDraft.value.trim() === sentText) messageDraft.value = ''
}

defineExpose({ markSent })
</script>

<template>
  <section class="player-chat">
    <header class="chat-heading">
      <div><p class="eyebrow">白天功能</p><h2>💬 私聊</h2></div>
      <span v-if="chat.my_chat" class="chat-dot" :style="{ background: chat.my_chat.color }" />
    </header>

    <template v-if="chat.my_chat">
      <div class="chat-members">
        <span v-for="member in chat.my_chat.members" :key="member.who">{{ participantName(member) }}</span>
      </div>
      <div class="chat-toolbar">
        <button v-if="chat.my_chat.is_owner" data-chat-invite-more class="btn" type="button" @click="beginPicker('invite')">➕ 邀请</button>
        <button data-chat-leave class="btn" :disabled="!connected || busy" type="button" @click="emit('command', { type: 'leave', cid: chat.my_chat.id })">退出</button>
        <button v-if="chat.my_chat.is_owner" data-chat-close class="btn" :disabled="!connected || busy" type="button" @click="emit('command', { type: 'close', cid: chat.my_chat.id })">关闭群聊</button>
      </div>

      <div class="chat-messages" aria-live="polite">
        <p v-if="!chat.my_chat.messages.length" class="hint">暂无消息</p>
        <p v-for="message in chat.my_chat.messages" :key="message.seq" :class="{ mine: String(message.from) === String(chat.who) }">
          <strong>{{ message.name }}</strong>：{{ message.text }}
        </p>
      </div>

      <div v-if="chat.my_chat.is_owner && chat.my_chat.requests.length" class="chat-requests">
        <p v-for="request in chat.my_chat.requests" :key="request.who">
          {{ request.name }} 申请加入
          <button :data-approve="request.who" class="btn" type="button" @click="emit('command', { type: 'approve', cid: chat.my_chat.id, who: request.who, approve: true })">同意</button>
          <button :data-reject="request.who" class="btn" type="button" @click="emit('command', { type: 'approve', cid: chat.my_chat.id, who: request.who, approve: false })">拒绝</button>
        </p>
      </div>

      <div class="chat-compose">
        <input v-model="messageDraft" data-chat-draft class="input" maxlength="500" placeholder="输入消息（仅本群可见）" @keydown.enter.prevent="send">
        <button data-chat-send class="btn primary" :disabled="!connected || busy || !messageDraft.trim()" type="button" @click="send">发送</button>
      </div>
    </template>

    <template v-else>
      <button data-chat-new class="btn primary" :disabled="!connected || busy" type="button" @click="beginPicker('create')">🙋 发起私聊</button>

      <div v-if="chat.invites.length" class="chat-invites">
        <p v-for="invite in chat.invites" :key="invite.id">
          <span class="chat-dot" :style="{ background: invite.color }" />{{ invite.owner_name }} 邀请你私聊
          <button :data-invite-accept="invite.id" class="btn" type="button" @click="emit('command', { type: 'respond-invite', cid: invite.id, accept: true })">接受</button>
          <button :data-invite-reject="invite.id" class="btn" type="button" @click="emit('command', { type: 'respond-invite', cid: invite.id, accept: false })">拒绝</button>
        </p>
      </div>

      <div v-if="chat.chats_public.length" class="chat-public">
        <p class="hint">进行中的私聊</p>
        <div v-for="item in chat.chats_public" :key="item.id" class="public-chat-row">
          <span class="chat-dot" :style="{ background: item.color }" />
          <span>{{ item.members.map(participantName).join('、') }}</span>
          <span v-if="item.requested" class="hint">已申请</span>
          <button v-else :data-chat-request="item.id" class="btn" type="button" @click="emit('command', { type: 'request', cid: item.id })">申请加入</button>
        </div>
      </div>
    </template>

    <section v-if="pickerMode" class="chat-picker">
      <p>{{ pickerMode === 'invite' ? '邀请更多玩家' : '选择私聊对象' }}</p>
      <div class="picker-grid">
        <button
          v-for="candidate in candidates"
          :key="candidate.id"
          :data-chat-pick="candidate.id"
          class="picker-person"
          :class="{ on: invitees.includes(candidate.id) }"
          type="button"
          @click="toggleInvitee(candidate.id)"
        >{{ candidate.label }}</button>
      </div>
      <button
        :data-chat-create="pickerMode === 'create' ? '' : null"
        :data-chat-invite-submit="pickerMode === 'invite' ? '' : null"
        class="btn primary"
        :disabled="!connected || busy || !invitees.length"
        type="button"
        @click="submitPicker"
      >发送邀请</button>
      <button class="btn" type="button" @click="pickerMode = null; invitees = []">取消</button>
    </section>
  </section>
</template>

<style scoped>
.player-chat { padding: 16px; display: grid; gap: 12px; border: 1px solid #3d657a; border-radius: 18px; background: color-mix(in srgb, var(--panel) 92%, #18303c); }
.chat-heading, .chat-toolbar, .chat-members, .chat-compose, .public-chat-row { display: flex; align-items: center; gap: 8px; }
.chat-heading { justify-content: space-between; }
.chat-heading h2 { font-size: 19px; }
.eyebrow, .hint { color: var(--dim); font-size: 12px; }
.chat-dot { width: 11px; height: 11px; flex: 0 0 11px; border-radius: 50%; }
.chat-members, .chat-toolbar { flex-wrap: wrap; }
.chat-members span { padding: 4px 7px; border-radius: 999px; background: #294452; font-size: 12px; }
.chat-messages { max-height: 220px; padding: 10px; display: grid; gap: 7px; overflow: auto; border-radius: 12px; background: rgb(0 0 0 / 18%); }
.chat-messages p { font-size: 13px; line-height: 1.45; }
.chat-messages .mine { color: #a9dcf4; text-align: right; }
.chat-requests, .chat-invites, .chat-public { display: grid; gap: 8px; }
.chat-requests p, .chat-invites p { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; }
.chat-compose .input { min-width: 0; flex: 1; }
.chat-picker { padding: 12px; display: grid; gap: 9px; border: 1px solid var(--line); border-radius: 12px; }
.picker-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 7px; }
.picker-person { padding: 8px; border: 1px solid var(--line); border-radius: 9px; background: var(--panel); color: var(--text); }
.picker-person.on { border-color: #78b7d6; background: #294452; }
</style>
