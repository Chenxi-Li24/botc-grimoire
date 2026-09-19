<script setup>
import { computed } from 'vue'
import { eligibleFakeRoles } from '../../presentation/manualAssignment.js'
import BluffPicker from './BluffPicker.vue'

const props = defineProps({
  view: { type: Object, required: true },
  seat: { type: Number, required: true },
  roleId: { type: String, required: true },
  fakeRole: { type: String, default: '' },
  lunaticMinions: { type: Array, default: () => [] },
  lunaticBluffs: { type: Array, default: () => [] },
})
defineEmits(['set-fake', 'toggle-minion', 'toggle-bluff'])

const fakeRoles = computed(() => eligibleFakeRoles(props.view, props.roleId))
const lunaticBluffRoles = computed(() => (props.view.roles || []).filter((role) => (
  props.view.script === 'trouble-brewing'
    ? role.team === 'townsfolk'
    : ['townsfolk', 'outsider'].includes(role.team)
)))
</script>

<template>
  <section v-if="fakeRoles.length" class="manual-subsection special-role-fields">
    <h4>{{ roleId === 'lunatic' ? '疯子认知' : '酒鬼认知' }}</h4>
    <p class="inline-note">该玩家看到的假身份</p>
    <div class="choice-grid">
      <button
        v-for="role in fakeRoles"
        :key="role.id"
        class="choice-chip"
        :class="[`team-${role.team}`, { active: fakeRole === role.id }]"
        type="button"
        :title="role.ability"
        @click="$emit('set-fake', role.id)"
      >{{ role.name }}</button>
    </div>
    <template v-if="roleId === 'lunatic'">
      <p class="inline-note">疯子以为的爪牙座位（至少一个）</p>
      <div class="choice-grid">
        <button
          v-for="target in view.player_count"
          v-show="target !== seat"
          :key="target"
          class="choice-chip"
          :class="{ active: lunaticMinions.includes(target) }"
          type="button"
          @click="$emit('toggle-minion', target)"
        >{{ target }}号</button>
      </div>
      <BluffPicker
        :roles="lunaticBluffRoles"
        :selected="lunaticBluffs"
        title="疯子看到的三个伪装"
        @toggle="$emit('toggle-bluff', $event)"
      />
    </template>
  </section>
</template>
