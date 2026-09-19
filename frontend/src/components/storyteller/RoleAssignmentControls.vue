<script setup>
import { computed } from 'vue'
import { getScriptName } from '../../presentation/storyteller.js'
import ConfirmAction from './ConfirmAction.vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, required: true },
  pending: { type: String, default: null },
  error: { type: Object, default: null },
  manualActive: { type: Boolean, default: false },
})
const emit = defineEmits(['begin-manual', 'assign-random'])
const teamLabels = ['镇民', '外来者', '爪牙', '恶魔']
const summary = computed(() => (
  `${getScriptName(props.view)} · ${props.view.player_count} 人 · ${teamLabels.map((label, index) => `${label}${props.view.composition?.[index] || 0}`).join(' / ')}。确认后会立即发牌并进入第一夜。`
))
</script>

<template>
  <section class="setup-section assignment-controls" aria-labelledby="assignment-heading">
    <div>
      <p class="panel-eyebrow">身份分配</p>
      <h3 id="assignment-heading">准备角色</h3>
    </div>
    <button
      class="btn"
      :class="{ primary: manualActive }"
      type="button"
      :disabled="!connected || Boolean(pending) || manualActive"
      @click="emit('begin-manual')"
    >{{ manualActive ? '正在手动发身份' : '手动发身份' }}</button>
    <ConfirmAction
      label="随机分配角色"
      confirm-label="确认发牌并进入第一夜"
      :summary="summary"
      :disabled="!connected || Boolean(pending) || manualActive"
      @confirm="emit('assign-random')"
    />
    <p v-if="error?.key === 'assign-random'" class="inline-error" role="alert">{{ error.message }}</p>
  </section>
</template>
