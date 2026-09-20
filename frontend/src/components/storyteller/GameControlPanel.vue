<script setup>
import { computed } from 'vue'
import { getScriptName } from '../../presentation/storyteller.js'
import DayControlPanel from './day/DayControlPanel.vue'
import LobbySetupPanel from './LobbySetupPanel.vue'
import NightStepList from './night/NightStepList.vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
  manualActive: { type: Boolean, default: false },
  night: { type: Object, default: null },
})
defineEmits([
  'configure', 'set-sentinel', 'toggle-fabled', 'begin-manual', 'assign-random', 'start', 'inspect-step',
  'set-day-stage', 'start-nomination', 'toggle-vote', 'resolve-nomination', 'end-day',
])
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
    :manual-active="manualActive"
    @configure="$emit('configure', $event)"
    @set-sentinel="$emit('set-sentinel', $event)"
    @toggle-fabled="$emit('toggle-fabled', $event)"
    @begin-manual="$emit('begin-manual')"
    @assign-random="$emit('assign-random')"
    @start="$emit('start')"
  />
  <div v-else-if="view.phase === 'night' && night?.workflow" class="panel-content night-control-panel">
    <div>
      <p class="panel-eyebrow">{{ scriptName }}</p>
      <h2>第 {{ night.workflow.night_no }} 夜</h2>
    </div>
    <NightStepList
      :steps="night.orderedSteps"
      :inspected-step-id="night.inspectedStepId"
      :current-step-id="night.workflow.current_step_id"
      @inspect="$emit('inspect-step', $event)"
    />
  </div>
  <DayControlPanel
    v-else-if="view.phase === 'day'"
    :view="view"
    :connected="connected"
    :pending="pending"
    :error="error"
    @set-stage="$emit('set-day-stage', $event)"
    @start-nomination="$emit('start-nomination', $event)"
    @toggle-vote="$emit('toggle-vote', $event)"
    @resolve-nomination="$emit('resolve-nomination', $event)"
    @end-day="$emit('end-day')"
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
    <p class="inline-note">游戏已经开始，大厅配置已锁定。白天与复盘功能暂时保留在旧版工具中。</p>
    <a class="btn" href="/legacy/#/storyteller">旧版白天与复盘工具</a>
  </div>
</template>
