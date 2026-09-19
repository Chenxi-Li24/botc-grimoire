<script setup>
import { computed } from 'vue'
import { TEAM_ORDER } from '../../presentation/manualAssignment.js'

const props = defineProps({
  roles: { type: Array, required: true },
  assignments: { type: Object, required: true },
  selectedSeat: { type: Number, required: true },
})
const emit = defineEmits(['toggle-role'])
const usedBy = computed(() => Object.fromEntries(
  Object.entries(props.assignments).map(([seat, roleId]) => [roleId, Number(seat)]),
))
</script>

<template>
  <div class="role-picker">
    <section v-for="([team, label]) in TEAM_ORDER" :key="team" class="role-picker-group" :class="`team-${team}`">
      <h4>{{ label }}</h4>
      <div class="choice-grid">
        <button
          v-for="role in roles.filter((item) => item.team === team)"
          :key="role.id"
          class="choice-chip role-choice"
          :class="{ active: assignments[String(selectedSeat)] === role.id, used: usedBy[role.id] && usedBy[role.id] !== selectedSeat }"
          type="button"
          :aria-pressed="assignments[String(selectedSeat)] === role.id"
          :disabled="Boolean(usedBy[role.id] && usedBy[role.id] !== selectedSeat)"
          :title="role.ability"
          @click="emit('toggle-role', role.id)"
        >
          {{ role.name }}
          <small v-if="usedBy[role.id] && usedBy[role.id] !== selectedSeat">{{ usedBy[role.id] }}号</small>
        </button>
      </div>
    </section>
  </div>
</template>
