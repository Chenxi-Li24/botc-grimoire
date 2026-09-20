<script setup>
import { computed } from 'vue'
import { canVote, currentVoteSummary, dayParticipants } from '../../../presentation/dayWorkflow.js'
import { participantLabel } from '../../../presentation/player.js'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
defineEmits(['toggle-vote'])

const participants = computed(() => dayParticipants(props.view))
const votes = computed(() => props.view.current?.votes || [])
const summary = computed(() => currentVoteSummary(props.view))
const nomineeLabel = computed(() => participantLabel(
  props.view.current?.nominee,
  props.view.seats,
  props.view.travelers,
))

function isOn(id) {
  return votes.value.includes(id)
}

function isBusy(id) {
  return props.pending.includes(`day:vote:${id}`)
}

function isDisabled(participant) {
  return !props.connected || isBusy(participant.id) || (!isOn(participant.id) && !canVote(participant, props.view))
}
</script>

<template>
  <section class="day-card vote-board" aria-labelledby="vote-board-title">
    <div class="day-card-heading">
      <div>
        <p class="panel-eyebrow">进行中的提名</p>
        <h3 id="vote-board-title">{{ nomineeLabel }}</h3>
      </div>
      <strong
        class="vote-summary"
        :class="summary.passes ? 'reached' : 'below'"
        data-vote-summary
      >{{ summary.votes }} / {{ summary.quorum }} 票</strong>
    </div>

    <p class="inline-note">点击玩家代记举手；已举手的死者仍可放下并收回本次死亡票。</p>
    <div class="voter-grid">
      <button
        v-for="participant in participants"
        :key="`vote-${participant.id}`"
        type="button"
        class="participant-choice voter-choice"
        :class="{ on: isOn(participant.id) }"
        :data-voter="participant.id"
        :disabled="isDisabled(participant)"
        @click="$emit('toggle-vote', participant.id)"
      >
        <span>{{ participant.label }}</span>
        <small v-if="isOn(participant.id)">已举手</small>
        <small v-else-if="!participant.alive && participant.deadVoteLeft">可用死亡票</small>
        <small v-else-if="!participant.alive">死亡票已用</small>
      </button>
    </div>
  </section>
</template>
