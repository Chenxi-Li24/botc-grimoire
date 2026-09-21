<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits(['answer-invite', 'send', 'leave', 'close', 'recall'])
const openId = ref(null)
const draft = ref('')
const armedClose = ref(null)
const armedRecall = ref(false)
let armTimer = null

const active = computed(() => (props.view.chats || []).filter((chat) => !chat.closed))
const archives = computed(() => (props.view.chats || []).filter((chat) => chat.closed))
const busy = computed(() => props.pending.some((key) => key.startsWith('chat-st:')))
const canWrite = computed(() => props.connected && !busy.value)

function isMember(chat) {
  return (chat.members || []).some((member) => String(member.who) === 'st')
}

function clearArm() {
  armedClose.value = null
  armedRecall.value = false
  if (armTimer) clearTimeout(armTimer)
  armTimer = null
}

function arm(kind, id = null) {
  if (!canWrite.value) return
  const armed = kind === 'recall' ? armedRecall.value : armedClose.value === id
  if (armed) {
    clearArm()
    if (kind === 'recall') emit('recall')
    else emit('close', id)
    return
  }
  clearArm()
  if (kind === 'recall') armedRecall.value = true
  else armedClose.value = id
  armTimer = setTimeout(clearArm, 3000)
}

function toggleOpen(id) {
  openId.value = openId.value === id ? null : id
  draft.value = ''
}

function send(id) {
  const text = draft.value.trim()
  if (!text || !canWrite.value) return
  emit('send', { id, text })
  draft.value = ''
}

watch(() => props.connected, (connected) => { if (!connected) clearArm() })
onBeforeUnmount(clearArm)
</script>

<template>
  <div class="panel-content storyteller-chat-panel">
    <div>
      <p class="panel-eyebrow">说书人监管</p>
      <h2>💬 私聊</h2>
      <p class="inline-note">可查看全部私聊；加入后才能以说书人身份发言。关闭的私聊保留档案。</p>
    </div>
    <button data-chat-admin-recall class="btn danger" type="button" :disabled="!canWrite || !active.length" :aria-pressed="armedRecall" @click="arm('recall')">{{ armedRecall ? '确认召回全部？' : '召回全部私聊' }}</button>
    <p v-if="error?.key?.startsWith('chat-st:')" class="inline-error">{{ error.message }}</p>
    <p v-if="!active.length" class="inline-note">目前没有进行中的私聊。</p>
    <section v-for="chat in active" :key="chat.id" class="storyteller-chat-row">
      <div class="traveler-row-heading"><strong>私聊 #{{ chat.id }}</strong><span>{{ (chat.members || []).map((member) => member.name).join('、') }}</span></div>
      <p v-if="isMember(chat)" class="inline-note">你在群里</p>
      <div v-for="invite in (chat.invites || []).filter((item) => String(item.who) === 'st')" :key="invite.who" class="admin-actions">
        <span>邀请说书人加入</span>
        <button :data-chat-admin-accept="chat.id" class="btn" type="button" :disabled="!canWrite" @click="emit('answer-invite', { id: chat.id, accept: true })">接受</button>
        <button :data-chat-admin-reject="chat.id" class="btn" type="button" :disabled="!canWrite" @click="emit('answer-invite', { id: chat.id, accept: false })">拒绝</button>
      </div>
      <div class="admin-actions">
        <button :data-chat-admin-open="chat.id" class="btn" type="button" @click="toggleOpen(chat.id)">{{ openId === chat.id ? '收起' : '查看' }}</button>
        <button v-if="isMember(chat)" :data-chat-admin-leave="chat.id" class="btn" type="button" :disabled="!canWrite" @click="emit('leave', chat.id)">退出</button>
        <button :data-chat-admin-close="chat.id" class="btn danger" type="button" :disabled="!canWrite" :aria-pressed="armedClose === chat.id" @click="arm('close', chat.id)">{{ armedClose === chat.id ? '确认关闭？' : '关闭' }}</button>
      </div>
      <div v-if="openId === chat.id" class="storyteller-chat-messages">
        <p v-if="!chat.messages?.length" class="inline-note">暂无消息</p>
        <p v-for="message in chat.messages || []" :key="message.seq"><strong>{{ message.name }}</strong>：{{ message.text }}</p>
        <div v-if="isMember(chat)" class="admin-inline-form">
          <input v-model="draft" :data-chat-admin-draft="chat.id" class="input" maxlength="500" placeholder="以说书人身份发言" :disabled="!canWrite" @keydown.enter.prevent="send(chat.id)">
          <button :data-chat-admin-send="chat.id" class="btn" type="button" :disabled="!canWrite || !draft.trim()" @click="send(chat.id)">发送</button>
        </div>
      </div>
    </section>
    <section v-if="archives.length" class="chat-archives">
      <h3>📦 私聊档案</h3>
      <div v-for="chat in archives" :key="chat.id" class="storyteller-chat-row">
        <div class="traveler-row-heading"><strong>#{{ chat.id }}</strong><span>{{ (chat.members || []).map((member) => member.name).join('、') }}</span></div>
        <button :data-chat-admin-open="chat.id" class="btn" type="button" @click="toggleOpen(chat.id)">{{ openId === chat.id ? '收起' : '查看' }}</button>
        <div v-if="openId === chat.id" class="storyteller-chat-messages">
          <p v-if="!chat.messages?.length" class="inline-note">无消息</p>
          <p v-for="message in chat.messages || []" :key="message.seq"><strong>{{ message.name }}</strong>：{{ message.text }}</p>
        </div>
      </div>
    </section>
  </div>
</template>
