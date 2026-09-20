<script setup>
import { computed } from 'vue'
import DayResolution from './DayResolution.vue'
import NominationComposer from './NominationComposer.vue'
import NominationHistory from './NominationHistory.vue'
import VoteBoard from './VoteBoard.vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
defineEmits(['set-stage', 'start-nomination', 'toggle-vote', 'resolve-nomination', 'end-day'])

const stageBusy = computed(() => props.pending.includes('day:stage'))
const nominationBusy = computed(() => props.pending.includes('day:nomination'))
</script>

<template>
  <div class="panel-content day-control-panel">
    <header class="day-panel-header">
      <div>
        <p class="panel-eyebrow">白天流程</p>
        <h2>第 {{ view.day_no }} 天</h2>
      </div>
      <div class="day-stage-switch" aria-label="白天阶段">
        <button
          type="button"
          :class="{ active: view.day_stage === 'talk' }"
          data-day-stage="talk"
          :disabled="!connected || stageBusy || view.day_stage === 'talk'"
          @click="$emit('set-stage', 'talk')"
        >公聊私聊</button>
        <button
          type="button"
          :class="{ active: view.day_stage === 'nom' }"
          data-day-stage="nom"
          :disabled="!connected || stageBusy || view.day_stage === 'nom'"
          @click="$emit('set-stage', 'nom')"
        >提名投票</button>
      </div>
    </header>

    <p v-if="view.day_stage === 'talk'" class="inline-note">
      当前是公聊与私聊阶段。准备好后切换到提名投票。
    </p>
    <NominationComposer
      v-else-if="view.day_stage === 'nom' && !view.current"
      :view="view"
      :connected="connected"
      :busy="nominationBusy"
      :error="error"
      @start-nomination="$emit('start-nomination', $event)"
    />
    <VoteBoard
      v-else
      :view="view"
      :connected="connected"
      :pending="pending"
      @toggle-vote="$emit('toggle-vote', $event)"
    />
    <NominationHistory :view="view" />
    <DayResolution
      :view="view"
      :connected="connected"
      :pending="pending"
      :error="error"
      @resolve-nomination="$emit('resolve-nomination', $event)"
      @end-day="$emit('end-day')"
    />
  </div>
</template>
