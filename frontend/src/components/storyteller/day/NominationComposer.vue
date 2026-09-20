<script setup>
import { computed, ref, watch } from 'vue'
import { dayParticipants } from '../../../presentation/dayWorkflow.js'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  error: { type: Object, default: null },
})
const emit = defineEmits(['start-nomination'])

const nominator = ref(null)
const nominee = ref(null)
const submitted = ref(false)
const sawBusy = ref(false)

const participants = computed(() => dayParticipants(props.view))
const todaysNominations = computed(() => (
  props.view.nominations || []
).filter((item) => item.day === props.view.day_no))
const usedNominators = computed(() => new Set(todaysNominations.value.map((item) => item.nominator)))
const usedNominees = computed(() => new Set(todaysNominations.value.map((item) => item.nominee)))
const unavailable = computed(() => !props.connected || props.busy)
const ready = computed(() => (
  nominator.value !== null
  && nominee.value !== null
  && !unavailable.value
))

function canNominate(participant) {
  return participant.alive && !participant.exiled && !usedNominators.value.has(participant.id)
}

function canBeNominated(participant) {
  return !participant.exiled && !usedNominees.value.has(participant.id)
}

function submit() {
  if (!ready.value) return
  submitted.value = true
  emit('start-nomination', { nominator: nominator.value, nominee: nominee.value })
}

watch(() => props.busy, (busy) => {
  if (!submitted.value) return
  if (busy) {
    sawBusy.value = true
    return
  }
  if (!sawBusy.value) return
  if (!props.error) {
    nominator.value = null
    nominee.value = null
  }
  submitted.value = false
  sawBusy.value = false
})
</script>

<template>
  <section class="day-card nomination-composer" aria-labelledby="nomination-composer-title">
    <div class="day-card-heading">
      <div>
        <p class="panel-eyebrow">发起提名</p>
        <h3 id="nomination-composer-title">选择双方</h3>
      </div>
      <span class="day-status-chip">每天各一次</span>
    </div>

    <div class="nomination-columns">
      <fieldset>
        <legend>谁发起提名</legend>
        <button
          v-for="participant in participants"
          :key="`nominator-${participant.id}`"
          type="button"
          class="participant-choice"
          :class="{ selected: nominator === participant.id }"
          :data-nominator="participant.id"
          :disabled="unavailable || !canNominate(participant)"
          @click="nominator = participant.id"
        >
          <span>{{ participant.label }}</span>
          <small v-if="!participant.alive">已死亡</small>
        </button>
      </fieldset>

      <fieldset>
        <legend>谁被提名</legend>
        <button
          v-for="participant in participants"
          :key="`nominee-${participant.id}`"
          type="button"
          class="participant-choice"
          :class="{ selected: nominee === participant.id }"
          :data-nominee="participant.id"
          :disabled="unavailable || !canBeNominated(participant)"
          @click="nominee = participant.id"
        >
          <span>{{ participant.label }}</span>
          <small v-if="participant.exiled">已流放</small>
          <small v-else-if="!participant.alive">已死亡</small>
        </button>
      </fieldset>
    </div>

    <p v-if="error" class="inline-error" role="alert">{{ error.message || error }}</p>
    <button
      type="button"
      class="btn primary"
      data-confirm-nomination
      :disabled="!ready"
      @click="submit"
    >
      {{ busy ? '正在发起…' : '确认发起提名' }}
    </button>
  </section>
</template>
