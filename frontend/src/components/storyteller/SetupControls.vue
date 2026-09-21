<script setup>
import { computed, ref, watch } from 'vue'
import ConfirmAction from './ConfirmAction.vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, required: true },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits(['configure'])
const script = ref(props.view.script)
const playerCount = ref(props.view.player_count)

const selectedScript = computed(() => (
  props.view.scripts?.find((item) => item.id === script.value) || props.view.scripts?.[0]
))
const minPlayers = computed(() => selectedScript.value?.min || 5)
const maxPlayers = computed(() => selectedScript.value?.max || 15)
const changed = computed(() => (
  script.value !== props.view.script || playerCount.value !== props.view.player_count
))
const summary = computed(() => (
  `改为${selectedScript.value?.name || script.value} · ${playerCount.value}人。修改配置会清空所有座位和角色分配。`
))

function clampCount(value) {
  return Math.max(minPlayers.value, Math.min(maxPlayers.value, Number(value) || minPlayers.value))
}

function updateScript() {
  playerCount.value = clampCount(playerCount.value)
}

function changeCount(delta) {
  playerCount.value = clampCount(playerCount.value + delta)
}

watch(() => [props.view.script, props.view.player_count], ([nextScript, nextCount]) => {
  script.value = nextScript
  playerCount.value = nextCount
})
</script>

<template>
  <section class="setup-section" aria-labelledby="setup-heading">
    <div class="section-heading">
      <div>
        <p class="panel-eyebrow">大厅配置</p>
        <h2 id="setup-heading">开局设置</h2>
      </div>
    </div>
    <label class="field-row">
      <span>剧本</span>
      <select v-model="script" :disabled="!connected || pending.includes('configure')" @change="updateScript">
        <option v-for="item in view.scripts" :key="item.id" :value="item.id">
          {{ item.name }} · {{ item.en }}
        </option>
      </select>
    </label>
    <div class="field-row">
      <span>玩家人数</span>
      <div class="stepper">
        <button type="button" :disabled="!connected || pending.includes('configure') || playerCount <= minPlayers" @click="changeCount(-1)">−</button>
        <strong>{{ playerCount }}</strong>
        <button type="button" :disabled="!connected || pending.includes('configure') || playerCount >= maxPlayers" @click="changeCount(1)">＋</button>
      </div>
    </div>
    <ConfirmAction
      v-if="changed"
      label="应用新配置"
      confirm-label="再次确认并清空座位"
      :summary="summary"
      :disabled="!connected || pending.includes('configure')"
      danger
      @confirm="emit('configure', { script, playerCount })"
    />
    <p v-if="!connected" class="inline-note">重连完成后才能修改配置。</p>
    <p v-if="error?.key === 'configure'" class="inline-error" role="alert">{{ error.message }}</p>
  </section>
</template>
