<script setup>
import { outcomeLabel } from '../../../presentation/nightWorkflow.js'

const props = defineProps({
  outcomes: { type: Array, default: () => [] },
  choices: { type: Object, default: () => ({}) },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
const emit = defineEmits(['update-choice', 'resolve'])
const resolutions = ['secret_death', 'no_death', 'delayed', 'redirected', 'transformation', 'choice_only']

function choice(outcome) {
  return props.choices[outcome.id] || {
    resolution: outcome.source_character === 'lunatic' ? 'choice_only' : 'secret_death',
    affected_seats: [...(outcome.selected_seats || [])],
    rationale: '',
  }
}
function update(outcome, field, value) {
  emit('update-choice', { id: outcome.id, value: { ...choice(outcome), [field]: value } })
}
</script>

<template>
  <section v-if="outcomes.length" class="night-stack">
    <article v-for="outcome in outcomes" :key="outcome.id" class="night-card outcome-card">
      <div class="night-card-heading"><h4>结果裁定</h4><span>{{ outcome.source_character }}</span></div>
      <p>选择目标：{{ outcome.selected_seats.map((seat) => `${seat}号`).join('、') || '无' }}</p>
      <ul v-if="outcome.hints?.length" class="night-hints">
        <li v-for="(hint, index) in outcome.hints" :key="index">{{ hint.message || hint.code || JSON.stringify(hint) }}</li>
      </ul>
      <label class="field-row">裁定结果
        <select :value="choice(outcome).resolution" @change="update(outcome, 'resolution', $event.target.value)">
          <option v-for="resolution in resolutions" :key="resolution" :value="resolution">{{ outcomeLabel(resolution) }}</option>
        </select>
      </label>
      <label class="field-row">裁定依据（复盘可见）
        <textarea :value="choice(outcome).rationale" rows="2" @input="update(outcome, 'rationale', $event.target.value)" />
      </label>
      <button
        class="btn primary"
        type="button"
        :disabled="!connected || pending.includes(`night:outcome:${outcome.id}`)"
        @click="$emit('resolve', { outcome_id: outcome.id, resolution: choice(outcome).resolution, affected_seats: choice(outcome).affected_seats || outcome.selected_seats, rationale: choice(outcome).rationale || '' })"
      >确认裁定</button>
    </article>
  </section>
</template>
