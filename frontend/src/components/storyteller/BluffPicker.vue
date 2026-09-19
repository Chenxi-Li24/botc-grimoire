<script setup>
defineProps({
  roles: { type: Array, required: true },
  selected: { type: Array, required: true },
  title: { type: String, required: true },
})
defineEmits(['toggle'])
</script>

<template>
  <section class="manual-subsection">
    <div class="manual-subheading">
      <h4>{{ title }}</h4>
      <span>{{ selected.length }}/3</span>
    </div>
    <div class="choice-grid">
      <button
        v-for="role in roles"
        :key="role.id"
        class="choice-chip"
        :class="[`team-${role.team}`, { active: selected.includes(role.id) }]"
        type="button"
        :disabled="!selected.includes(role.id) && selected.length >= 3"
        :title="role.ability"
        @click="$emit('toggle', role.id)"
      >{{ role.name }}</button>
    </div>
  </section>
</template>
