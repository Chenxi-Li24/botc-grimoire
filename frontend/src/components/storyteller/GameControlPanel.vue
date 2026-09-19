<script setup>
import { computed } from 'vue'
import { getScriptName } from '../../presentation/storyteller.js'
import LobbySetupPanel from './LobbySetupPanel.vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: String, default: null },
  error: { type: Object, default: null },
})
defineEmits(['configure', 'set-sentinel', 'toggle-fabled'])
const scriptName = computed(() => getScriptName(props.view))
const seatedCount = computed(() => props.view.seats?.filter((seat) => seat.player).length || 0)
</script>

<template>
  <LobbySetupPanel
    v-if="view.status === 'lobby'"
    :view="view"
    :connected="connected"
    :pending="pending"
    :error="error"
    @configure="$emit('configure', $event)"
    @set-sentinel="$emit('set-sentinel', $event)"
    @toggle-fabled="$emit('toggle-fabled', $event)"
  />
  <div v-else class="panel-content">
    <div>
      <p class="panel-eyebrow">本局控制</p>
      <h2>{{ scriptName }}</h2>
    </div>
    <dl class="control-summary">
      <div><dt>人数</dt><dd>{{ view.player_count }} 人</dd></div>
      <div><dt>入座</dt><dd>已入座 {{ seatedCount }}/{{ view.player_count }}</dd></div>
      <div><dt>房间</dt><dd>{{ view.room_code }}</dd></div>
    </dl>
    <p class="inline-note">游戏已经开始，大厅配置已锁定。夜晚与白天操作仍在完整控制台中完成。</p>
    <a class="btn" href="/legacy/#/storyteller">前往完整控制台</a>
  </div>
</template>
