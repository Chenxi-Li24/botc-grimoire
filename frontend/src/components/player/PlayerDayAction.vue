<script setup>
import { computed, ref, watch } from 'vue'
import { participantLabel } from '../../presentation/player.js'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  selectedParticipant: { type: [Number, String], default: null },
})
const emit = defineEmits(['nominate', 'vote'])

const nominee = ref(null)
const deadVoteArmed = ref(false)
const selfId = computed(() => props.view.traveler?.id ?? props.view.me?.seat)
const selfState = computed(() => props.view.traveler || props.view.me || {})
const currentVotes = computed(() => props.view.current?.votes || [])
const hasVoted = computed(() => currentVotes.value.includes(selfId.value))
const nominationOpen = computed(() => (
  props.view.status === 'playing'
  && props.view.phase === 'day'
  && props.view.day_stage === 'nom'
  && !props.view.current
))
const nominatedToday = computed(() => (props.view.nominations || []).some((item) => (
  item.day === props.view.day_no && item.nominator === selfId.value
)))
const canNominate = computed(() => (
  nominationOpen.value && selfState.value.alive !== false && !nominatedToday.value
))
const voteDisabled = computed(() => (
  !props.connected
  || props.pending.includes('vote')
  || (!hasVoted.value && selfState.value.alive === false && selfState.value.dead_vote_used)
))
const candidates = computed(() => [
  ...(props.view.seats || [])
    .filter((slot) => slot.player)
    .map((slot) => ({ id: slot.seat, label: participantLabel(slot.seat, props.view.seats, props.view.travelers_public) })),
  ...(props.view.travelers_public || [])
    .filter((traveler) => !traveler.exiled)
    .map((traveler) => ({ id: traveler.id, label: participantLabel(traveler.id, props.view.seats, props.view.travelers_public) })),
])

watch(() => props.selectedParticipant, (value) => {
  if (value !== null && value !== undefined && canNominate.value) nominee.value = value
}, { immediate: true })
watch(() => props.view.current, () => { deadVoteArmed.value = false })

function confirmNomination() {
  if (!canNominate.value || nominee.value === null || !props.connected) return
  emit('nominate', nominee.value)
  nominee.value = null
}

function vote() {
  if (voteDisabled.value || !props.view.current) return
  if (hasVoted.value || selfState.value.alive !== false) {
    deadVoteArmed.value = false
    emit('vote')
    return
  }
  if (!deadVoteArmed.value) {
    deadVoteArmed.value = true
    return
  }
  deadVoteArmed.value = false
  emit('vote')
}
</script>

<template>
  <section class="day-action">
    <header>
      <p class="eyebrow">第 {{ view.day_no }} 天</p>
      <h2>{{ view.day_stage === 'talk' ? '公聊与私聊' : view.current ? '正在投票' : '提名阶段' }}</h2>
    </header>

    <template v-if="view.day_stage === 'talk'">
      <p class="hint">说书人开启提名阶段后才能操作。</p>
    </template>

    <template v-else-if="view.current">
      <p>{{ participantLabel(view.current.nominator, view.seats, view.travelers_public) }} 提名 {{ participantLabel(view.current.nominee, view.seats, view.travelers_public) }}</p>
      <button data-vote class="btn" :class="{ primary: !hasVoted, danger: deadVoteArmed }" :disabled="voteDisabled" type="button" @click="vote">
        <template v-if="hasVoted">✋ 放下（取消举手）</template>
        <template v-else-if="selfState.alive !== false">🖐 举手赞成</template>
        <template v-else-if="selfState.dead_vote_used">🗳 死票已交</template>
        <template v-else-if="deadVoteArmed">确认交出死票</template>
        <template v-else>🖐 使用唯一死票</template>
      </button>
      <p v-if="deadVoteArmed" class="warning">死票每局只有一次，再点一次确认。</p>
    </template>

    <template v-else-if="canNominate">
      <p class="hint">选择目标后还需确认，避免误触。</p>
      <div class="nominee-grid">
        <button
          v-for="candidate in candidates"
          :key="candidate.id"
          :data-nominee="candidate.id"
          class="nominee"
          :class="{ on: nominee === candidate.id }"
          :disabled="!connected || pending.includes('nominate')"
          type="button"
          @click="nominee = candidate.id"
        >{{ candidate.label }}</button>
      </div>
      <div v-if="nominee !== null" class="nomination-confirm">
        <span>提名 {{ participantLabel(nominee, view.seats, view.travelers_public) }}？</span>
        <button data-confirm-nomination class="btn primary" :disabled="!connected || pending.includes('nominate')" type="button" @click="confirmNomination">确认提名</button>
        <button class="btn" type="button" @click="nominee = null">换人</button>
      </div>
    </template>

    <p v-else-if="nominatedToday" class="hint">你今天已经提名过了。</p>
    <p v-else class="hint">你当前不能发起提名。</p>
  </section>
</template>

<style scoped>
.day-action { padding: 16px; display: grid; gap: 12px; border: 1px solid #765f2d; border-radius: 18px; background: color-mix(in srgb, var(--panel) 90%, #382e18); }
.day-action header { display: grid; gap: 4px; }
.day-action h2 { font-size: 20px; }
.eyebrow, .hint { color: var(--dim); font-size: 12px; }
.nominee-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.nominee { min-height: 42px; padding: 8px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); color: var(--text); }
.nominee.on { border-color: #e0ba62; background: #57472a; }
.nomination-confirm { padding: 10px; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; border: 1px solid #765f2d; border-radius: 12px; }
.nomination-confirm span { flex: 1 0 100%; }
.warning { color: #ffd479; font-size: 13px; }
</style>
