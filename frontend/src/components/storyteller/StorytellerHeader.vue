<script setup>
import { computed } from 'vue'
import { getPhaseLabel, getScriptName } from '../../presentation/storyteller.js'

const props = defineProps({
  view: { type: Object, required: true },
  connectionStatus: { type: String, required: true },
})
const emit = defineEmits(['open-left', 'open-right', 'open-travelers', 'open-chats', 'open-session', 'open-seats'])

const scriptName = computed(() => getScriptName(props.view))
const phaseLabel = computed(() => getPhaseLabel(props.view))
const connectionLabel = computed(() => ({
  connected: '已连接', connecting: '连接中', reconnecting: '重连中',
}[props.connectionStatus] || props.connectionStatus))
</script>

<template>
  <div class="storyteller-header-inner">
    <button class="drawer-toggle drawer-toggle-left" type="button" @click="emit('open-left')">设置</button>
    <strong class="storyteller-title">🕯 魔典</strong>
    <span class="header-chip">房间 {{ view.room_code }}</span>
    <span class="header-script">{{ scriptName }}</span>
    <span class="phase-badge">{{ phaseLabel }}</span>
    <span class="connection-badge" :data-status="connectionStatus">{{ connectionLabel }}</span>
    <a class="btn header-primary" href="/legacy/#/storyteller">旧版白天与复盘工具</a>
    <button data-open-session class="btn" type="button" @click="emit('open-session')">⚙ 房间</button>
    <button v-if="view.status === 'playing'" data-open-seats class="btn" type="button" @click="emit('open-seats')">座位</button>
    <button v-if="view.status === 'playing'" data-open-travelers class="btn" type="button" @click="emit('open-travelers')">🎒 旅行者</button>
    <button v-if="view.status === 'playing'" data-open-chats class="btn" type="button" @click="emit('open-chats')">💬 私聊</button>
    <button class="drawer-toggle drawer-toggle-right" type="button" @click="emit('open-right')">当前任务</button>
  </div>
</template>
