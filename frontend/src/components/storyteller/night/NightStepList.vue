<script setup>
import { nightStatusLabel, nightTriggerLabel } from '../../../presentation/nightWorkflow.js'

defineProps({
  steps: { type: Array, default: () => [] },
  inspectedStepId: { type: String, default: null },
  currentStepId: { type: String, default: null },
})
defineEmits(['inspect'])

const skipLabels = {
  actor_dead: '玩家已死亡，不唤醒',
  ability_inactive: '能力已失效',
  death_trigger_not_met: '未满足死亡触发',
  requires_demon_attack: '并非死于恶魔攻击',
  created_demon_no_kill_this_night: '本夜新生恶魔不能刀人',
  forced: '说书人强制略过',
  event_undone: '相关事件已撤销',
}
</script>

<template>
  <div class="night-step-list" data-night-step-list>
    <div class="night-step-list-heading">
      <p class="panel-eyebrow">本夜行动顺序</p>
      <span>{{ steps.length }} 项</span>
    </div>
    <button
      v-for="step in steps"
      :key="step.id"
      type="button"
      class="night-step"
      :class="[`status-${step.status}`, { 'is-inspected': inspectedStepId === step.id, 'is-current': currentStepId === step.id }]"
      @click="$emit('inspect', step.id)"
    >
      <span class="night-step-status">{{ nightStatusLabel(step.status) }}</span>
      <strong>{{ step.actor_seat ? `${step.actor_seat}号` : '流程' }} · {{ step.name || step.character_id }}</strong>
      <small>{{ nightTriggerLabel(step.trigger) }}</small>
      <small v-if="step.skip_reason" class="night-step-skip">{{ skipLabels[step.skip_reason] || step.skip_reason }}</small>
    </button>
    <p v-if="!steps.length" class="inline-note">当前夜晚没有行动步骤。</p>
  </div>
</template>
