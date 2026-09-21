<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits(['set-winner', 'open-review'])
const armed = ref(null)
let timer = null

function disarm() {
  armed.value = null
  if (timer) clearTimeout(timer)
  timer = null
}

function choose(winner) {
  if (!props.connected || props.pending.includes('end')) return
  const key = winner ?? 'undo'
  if (armed.value === key) {
    disarm()
    emit('set-winner', winner)
    return
  }
  disarm()
  armed.value = key
  timer = setTimeout(disarm, 3000)
}

watch(() => props.view.winner, disarm)
watch(() => props.connected, (connected) => { if (!connected) disarm() })
onBeforeUnmount(disarm)
</script>

<template>
  <div class="panel-content end-game-panel">
    <div><p class="panel-eyebrow">说书人裁定</p><h2>🏁 结算</h2></div>
    <template v-if="view.winner">
      <p class="end-winner">{{ view.winner === 'good' ? '善良' : '邪恶' }}阵营获胜</p>
      <button data-end-undo class="btn" type="button" :disabled="!connected || pending.includes('end')" :aria-pressed="armed === 'undo'" @click="choose(null)">{{ armed === 'undo' ? '确认撤销结算？' : '撤销结算' }}</button>
      <button class="btn primary" type="button" @click="emit('open-review')">📜 查看复盘</button>
    </template>
    <template v-else>
      <p class="inline-note">确认胜负后，所有玩家将收到结算。选定获胜方需要再次点击确认。</p>
      <button data-end-good class="btn" type="button" :disabled="!connected || pending.includes('end')" :aria-pressed="armed === 'good'" @click="choose('good')">{{ armed === 'good' ? '确认善良获胜？' : '善良阵营获胜' }}</button>
      <button data-end-evil class="btn danger" type="button" :disabled="!connected || pending.includes('end')" :aria-pressed="armed === 'evil'" @click="choose('evil')">{{ armed === 'evil' ? '确认邪恶获胜？' : '邪恶阵营获胜' }}</button>
    </template>
    <p v-if="error?.key === 'end'" class="inline-error">{{ error.message }}</p>
  </div>
</template>
