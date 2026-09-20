<script setup>
import { computed } from 'vue'
import { currentVoteSummary, executionStanding } from '../../../presentation/dayWorkflow.js'
import { participantLabel } from '../../../presentation/player.js'
import ConfirmAction from '../ConfirmAction.vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
defineEmits(['resolve-nomination', 'end-day'])

const summary = computed(() => currentVoteSummary(props.view))
const standing = computed(() => executionStanding(props.view))
const resolving = computed(() => props.pending.includes('day:resolve'))
const ending = computed(() => props.pending.includes('day:end'))
const errorMessage = computed(() => props.error?.message || '')

function label(id) {
  return participantLabel(id, props.view.seats, props.view.travelers)
}
</script>

<template>
  <footer class="day-resolution">
    <p v-if="errorMessage" class="inline-error" role="alert">{{ errorMessage }}</p>

    <div v-if="view.current" class="resolution-actions">
      <p>
        当前 {{ summary.votes }} / {{ summary.quorum }} 票，
        {{ summary.passes ? '达到门槛' : '尚未达到门槛' }}。
      </p>
      <ConfirmAction
        data-resolve-pass
        label="宣布通过"
        confirm-label="再次点击确认通过"
        summary="结票后本次举手和死亡票将被锁定。"
        :disabled="!connected || resolving || !summary.passes"
        @confirm="$emit('resolve-nomination', true)"
      />
      <ConfirmAction
        data-resolve-fail
        label="宣布未通过"
        confirm-label="再次点击确认未通过"
        summary="结票后本次举手和死亡票将被锁定。"
        :disabled="!connected || resolving"
        @confirm="$emit('resolve-nomination', false)"
      />
    </div>

    <div v-else class="execution-standing">
      <p v-if="standing.state === 'leader'">
        当前处决领先：<strong>{{ label(standing.nominee) }}</strong> · {{ standing.votes }} 票
      </p>
      <p v-else-if="standing.state === 'tie'">
        当前最高 {{ standing.votes }} 票平票，若现在结束白天则无人处决。
      </p>
      <p v-else>当前无人进入处决台。</p>
    </div>

    <ConfirmAction
      data-end-day
      label="结束白天"
      confirm-label="确认结束并入夜"
      summary="将按当前最高票执行处决；平票或无人通过时无人处决。"
      :disabled="!connected || ending"
      danger
      @confirm="$emit('end-day')"
    />
  </footer>
</template>
