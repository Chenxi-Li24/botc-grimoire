<script setup>
import { computed, ref } from 'vue'
import { getPhaseLabel, getScriptName } from '../../presentation/storyteller.js'

const props = defineProps({
  view: { type: Object, required: true },
  connectionStatus: { type: String, required: true },
})
const emit = defineEmits(['open-left', 'open-right', 'open-join', 'open-travelers', 'open-chats', 'open-session', 'open-seats', 'open-end', 'open-review'])

const scriptName = computed(() => getScriptName(props.view))
const phaseLabel = computed(() => getPhaseLabel(props.view))
const connectionLabel = computed(() => ({
  connected: '已连接', connecting: '连接中', reconnecting: '重连中',
}[props.connectionStatus] || props.connectionStatus))
const menuOpen = ref(false)
function openAdmin(event) {
  menuOpen.value = false
  emit(event)
}
</script>

<template>
  <div class="storyteller-header-inner">
    <button class="drawer-toggle drawer-toggle-left" type="button" @click="emit('open-left')">设置</button>
    <strong class="storyteller-title">🕯 魔典</strong>
    <span class="header-chip">房间 {{ view.room_code }}</span>
    <span class="header-script">{{ scriptName }}</span>
    <span class="phase-badge">{{ phaseLabel }}</span>
    <span class="connection-badge" :data-status="connectionStatus">{{ connectionLabel }}</span>
    <button data-open-admin-menu class="btn header-admin-toggle" type="button" :aria-expanded="menuOpen" aria-controls="storyteller-admin-actions" @click="menuOpen = !menuOpen">管理</button>
    <nav id="storyteller-admin-actions" data-admin-actions class="header-admin-actions" :class="{ 'is-open': menuOpen }" aria-label="说书人管理">
      <button data-open-session class="btn header-primary" type="button" @click="openAdmin('open-session')">⚙ 房间</button>
      <button data-open-join class="btn" type="button" @click="openAdmin('open-join')">📱 玩家加入</button>
      <button v-if="view.status === 'playing'" data-open-seats class="btn" type="button" @click="openAdmin('open-seats')">座位</button>
      <button v-if="view.status === 'playing'" data-open-travelers class="btn" type="button" @click="openAdmin('open-travelers')">🎒 旅行者</button>
      <button v-if="view.status === 'playing'" data-open-chats class="btn" type="button" @click="openAdmin('open-chats')">💬 私聊</button>
      <button v-if="view.status === 'playing'" data-open-end class="btn" type="button" @click="openAdmin('open-end')">🏁 结算</button>
      <button v-if="view.winner" data-open-review class="btn" type="button" @click="openAdmin('open-review')">📜 复盘</button>
    </nav>
    <button class="drawer-toggle drawer-toggle-right" type="button" @click="emit('open-right')">当前任务</button>
  </div>
</template>
