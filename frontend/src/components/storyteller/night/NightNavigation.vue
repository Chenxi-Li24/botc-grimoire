<script setup>
import { computed } from 'vue'

const props = defineProps({
  steps: { type: Array, default: () => [] },
  currentStep: { type: Object, default: null },
  forceArmed: { type: Boolean, default: false },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
defineEmits(['previous', 'next'])

const index = computed(() => Math.max(0, props.steps.findIndex((item) => item.id === props.currentStep?.id)))
const atStart = computed(() => !props.currentStep || index.value === 0)
const atDawn = computed(() => props.currentStep?.character_id === 'dawn' || index.value === props.steps.length - 1)
const busy = computed(() => props.pending.some((key) => key.startsWith('night:step:')))
</script>

<template>
  <nav class="night-navigation" data-night-navigation aria-label="夜晚步骤导航">
    <button
      class="btn ghost"
      data-night-previous
      data-slot="left"
      type="button"
      :disabled="!connected || busy || atStart"
      @click="$emit('previous')"
    >← 上一步</button>
    <div class="night-navigation-progress">
      <strong>{{ steps.length ? index + 1 : 0 }} / {{ steps.length }}</strong>
      <span>当前夜序</span>
    </div>
    <button
      class="btn primary"
      data-night-next
      data-slot="right"
      type="button"
      :disabled="!connected || busy || !currentStep"
      @click="$emit('next')"
    >{{ forceArmed ? '仍然继续' : (atDawn ? '天亮' : '下一步') }} →</button>
  </nav>
</template>
