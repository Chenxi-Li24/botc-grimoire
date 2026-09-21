<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
const emit = defineEmits(['submit'])

const prompt = computed(() => props.view.night_workflow?.prompt || null)
const targets = ref([])
const character = ref(null)

function seedDraft(next, previous) {
  if (!next) {
    targets.value = []
    character.value = null
    return
  }
  const changed = !previous || next.id !== previous.id
  const values = next.values || {}
  if (changed || Object.prototype.hasOwnProperty.call(values, 'targets')) {
    targets.value = [...(values.targets || [])]
  }
  if (changed || Object.prototype.hasOwnProperty.call(values, 'character')) {
    character.value = values.character || null
  }
}

watch(prompt, seedDraft, { immediate: true })

const requiredTargetCount = computed(() => prompt.value?.player_count || 0)
const needsCharacter = computed(() => prompt.value?.required_fields?.includes('character'))
const busy = computed(() => props.pending.includes('night-action'))
const canSubmit = computed(() => Boolean(
  prompt.value
  && props.connected
  && !busy.value
  && targets.value.length === requiredTargetCount.value
  && (!needsCharacter.value || character.value),
))

function seatLabel(seat) {
  const slot = props.view.seats?.find((item) => item.seat === seat)
  return `${seat}号${slot?.player?.name ? ` ${slot.player.name}` : ''}`
}

function toggleTarget(seat) {
  if (targets.value.includes(seat)) {
    targets.value = targets.value.filter((item) => item !== seat)
    return
  }
  if (requiredTargetCount.value === 1) {
    targets.value = [seat]
    return
  }
  if (targets.value.length < requiredTargetCount.value) {
    targets.value = [...targets.value, seat]
  }
}

function submit() {
  if (!canSubmit.value) return
  emit('submit', {
    step_id: prompt.value.id,
    selected_seats: [...targets.value],
    ...(needsCharacter.value ? { character_id: character.value } : {}),
  })
}

function resultText(result) {
  return typeof result === 'string' ? result : JSON.stringify(result)
}
</script>

<template>
  <section v-if="prompt || view.night_workflow?.deliveries?.length || view.night_workflow?.lunatic_choices?.length || view.my_mad" class="night-action">
    <template v-if="prompt">
      <header>
        <p class="eyebrow">第 {{ view.night_workflow.night_no }} 夜 · 轮到你行动</p>
        <h2>{{ prompt.name || prompt.character_id }}</h2>
        <p>{{ prompt.reminder }}</p>
      </header>

      <div v-if="prompt.target_seats?.length" class="target-grid">
        <button
          v-for="seat in prompt.target_seats"
          :key="seat"
          :data-target="seat"
          class="target"
          :class="{ on: targets.includes(seat) }"
          type="button"
          @click="toggleTarget(seat)"
        >{{ seatLabel(seat) }}</button>
      </div>
      <p v-if="requiredTargetCount" class="hint">已选择 {{ targets.length }}/{{ requiredTargetCount }} 人</p>

      <label v-if="needsCharacter" class="character-field">选择角色
        <select v-model="character" data-character>
          <option :value="null">请选择角色</option>
          <option v-for="candidate in prompt.character_candidates" :key="candidate.id" :value="candidate.id">
            {{ candidate.name }}
          </option>
        </select>
      </label>

      <section v-if="prompt.character_id === 'widow' && view.grimoire" class="widow-grimoire">
        <h3>📖 临时魔典</h3>
        <p v-for="seat in view.grimoire.seats" :key="seat.seat">{{ seat.seat }}号 {{ seat.name || '线下/未领取' }} · {{ seat.role?.name || '未配置' }}</p>
        <p class="hint">此信息只在你的行动步骤内显示。</p>
      </section>

      <button data-submit-night class="btn primary" :disabled="!canSubmit" type="button" @click="submit">
        {{ requiredTargetCount || needsCharacter ? '提交夜晚选择' : '确认已知晓' }}
      </button>
    </template>

    <section v-if="view.night_workflow?.lunatic_choices?.length" class="night-note">
      <h3>🩻 疯子的选择</h3>
      <p v-for="choice in view.night_workflow.lunatic_choices" :key="choice.outcome_id || choice.lunatic_seat">
        疯子 {{ choice.lunatic_seat }}号选择了 {{ choice.target_seats.map((seat) => `${seat}号`).join('、') }}
      </p>
    </section>

    <section v-if="view.night_workflow?.deliveries?.length" class="night-note">
      <h3>📩 说书人信息</h3>
      <p v-for="delivery in view.night_workflow.deliveries" :key="delivery.id" :class="{ retracted: delivery.retracted }">
        {{ resultText(delivery.delivered_result) }}{{ delivery.retracted ? '（已撤回）' : '' }}
      </p>
    </section>

    <p v-if="view.my_mad" class="madness-note">🎭 你必须声称自己是「{{ view.my_mad.role.name }}」，直到说书人解除。</p>
  </section>
</template>

<style scoped>
.night-action { padding: 16px; display: grid; gap: 14px; border: 1px solid #8e3640; border-radius: 18px; background: color-mix(in srgb, var(--panel) 82%, #341015); }
.night-action header { display: grid; gap: 7px; }
.night-action h2 { font-size: 21px; }
.night-action h3 { font-size: 15px; }
.eyebrow, .hint { color: var(--dim); font-size: 12px; }
.target-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.target { min-height: 44px; padding: 8px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); color: var(--text); }
.target.on { border-color: #cf5961; background: #4b2026; }
.character-field { display: grid; gap: 7px; color: var(--dim); font-size: 13px; }
.character-field select { padding: 10px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); color: var(--text); }
.night-note, .widow-grimoire, .madness-note { padding: 12px; display: grid; gap: 6px; border: 1px solid var(--line); border-radius: 12px; line-height: 1.5; }
.widow-grimoire { border-color: #8e4760; }
.madness-note { color: #e5c2ff; }
.retracted { text-decoration: line-through; opacity: .55; }
@media (max-width: 380px) { .target-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
