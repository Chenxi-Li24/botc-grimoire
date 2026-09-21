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
const balloonistVersion = ref(props.view.balloonist_version || '')
const balloonistOutsiderDelta = ref(props.view.balloonist_outsider_delta == null
  ? '' : String(props.view.balloonist_outsider_delta))

const selectedScript = computed(() => (
  props.view.scripts?.find((item) => item.id === script.value) || props.view.scripts?.[0]
))
const minPlayers = computed(() => selectedScript.value?.min || 5)
const maxPlayers = computed(() => selectedScript.value?.max || 15)
const hasBalloonist = computed(() => Boolean(selectedScript.value?.has_balloonist))
const selectedDelta = computed(() => balloonistVersion.value === 'old'
  ? 1 : balloonistOutsiderDelta.value === '' ? null : Number(balloonistOutsiderDelta.value))
const balloonistComplete = computed(() => !hasBalloonist.value || (
  ['new', 'old'].includes(balloonistVersion.value)
  && [0, 1].includes(selectedDelta.value)
))
const changed = computed(() => (
  script.value !== props.view.script || playerCount.value !== props.view.player_count
  || (hasBalloonist.value && (
    balloonistVersion.value !== (props.view.balloonist_version || '')
    || selectedDelta.value !== props.view.balloonist_outsider_delta
  ))
))
const summary = computed(() => (
  `改为${selectedScript.value?.name || script.value} · ${playerCount.value}人${hasBalloonist.value
    ? ` · 气球驾驶员${balloonistVersion.value === 'old' ? '旧版' : '新版'} · 外来者 +${selectedDelta.value}` : ''}。修改配置会清空所有座位和角色分配。`
))

function clampCount(value) {
  return Math.max(minPlayers.value, Math.min(maxPlayers.value, Number(value) || minPlayers.value))
}

function updateScript() {
  playerCount.value = clampCount(playerCount.value)
  balloonistVersion.value = script.value === props.view.script ? (props.view.balloonist_version || '') : ''
  balloonistOutsiderDelta.value = script.value === props.view.script && props.view.balloonist_outsider_delta != null
    ? String(props.view.balloonist_outsider_delta) : ''
}

function updateBalloonistVersion() {
  balloonistOutsiderDelta.value = balloonistVersion.value === 'old' ? '1' : ''
}

function confirmConfig() {
  if (!balloonistComplete.value) return
  emit('configure', {
    script: script.value, playerCount: playerCount.value,
    ...(hasBalloonist.value ? {
      balloonistVersion: balloonistVersion.value,
      balloonistOutsiderDelta: selectedDelta.value,
    } : {}),
  })
}

function changeCount(delta) {
  playerCount.value = clampCount(playerCount.value + delta)
}

watch(() => [props.view.script, props.view.player_count,
  props.view.balloonist_version, props.view.balloonist_outsider_delta],
([nextScript, nextCount, nextVersion, nextDelta]) => {
  script.value = nextScript
  playerCount.value = nextCount
  balloonistVersion.value = nextVersion || ''
  balloonistOutsiderDelta.value = nextDelta == null ? '' : String(nextDelta)
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
    <section v-if="hasBalloonist" class="night-card" data-balloonist-setup>
      <h3>气球驾驶员规则</h3>
      <label class="field-row">规则版本
        <select v-model="balloonistVersion" data-balloonist-version :disabled="!connected" @change="updateBalloonistVersion">
          <option value="">请选择新版或旧版</option>
          <option value="new">新版：每夜与前次登记类型不同</option>
          <option value="old">旧版：每个登记类型最多一次</option>
        </select>
      </label>
      <label v-if="balloonistVersion === 'new'" class="field-row">外来者调整
        <select v-model="balloonistOutsiderDelta" data-balloonist-delta :disabled="!connected">
          <option value="">请选择 +0 或 +1</option>
          <option value="0">+0</option>
          <option value="1">+1</option>
        </select>
      </label>
      <p v-else-if="balloonistVersion === 'old'" class="inline-note">旧版固定外来者 +1。</p>
      <p v-if="!balloonistComplete" class="inline-warning">请选择新版或旧版，并确定外来者调整后再应用配置。</p>
    </section>
    <ConfirmAction
      v-if="changed"
      label="应用新配置"
      confirm-label="再次确认并清空座位"
      :summary="summary"
      :disabled="!connected || pending.includes('configure') || !balloonistComplete"
      danger
      @confirm="confirmConfig"
    />
    <p v-if="!connected" class="inline-note">重连完成后才能修改配置。</p>
    <p v-if="error?.key === 'configure'" class="inline-error" role="alert">{{ error.message }}</p>
  </section>
</template>
