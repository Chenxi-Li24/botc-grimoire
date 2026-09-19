<script setup>
import { computed } from 'vue'
import { eligibleBluffRoles, TEAM_ORDER } from '../../presentation/manualAssignment.js'
import BluffPicker from './BluffPicker.vue'
import RolePicker from './RolePicker.vue'
import SpecialRoleFields from './SpecialRoleFields.vue'

const props = defineProps({
  view: { type: Object, required: true },
  selectedSeat: { type: Number, default: null },
  assignments: { type: Object, required: true },
  bluffs: { type: Array, required: true },
  fakes: { type: Object, required: true },
  lunaticMinions: { type: Object, required: true },
  lunaticBluffs: { type: Object, required: true },
  godfatherAdjustment: { type: Number, required: true },
  summary: { type: Object, required: true },
  connected: { type: Boolean, required: true },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits([
  'toggle-role', 'toggle-bluff', 'set-fake', 'toggle-lunatic-minion',
  'toggle-lunatic-bluff', 'set-godfather', 'cancel', 'confirm',
])

const selectedRoleId = computed(() => props.assignments[String(props.selectedSeat)] || '')
const bluffRoles = computed(() => eligibleBluffRoles(props.view, props.assignments))
const hasGodfather = computed(() => Object.values(props.assignments).includes('godfather'))
const teamSummary = computed(() => TEAM_ORDER.map(([, label], index) => ({
  label,
  selected: props.summary.selected[index],
  expected: props.summary.expected[index],
})))
</script>

<template>
  <div class="panel-content manual-assignment-panel">
    <div class="context-heading">
      <div>
        <p class="panel-eyebrow">手动发身份</p>
        <h2>{{ selectedSeat ? `${selectedSeat}号座位` : '选择一个座位' }}</h2>
      </div>
      <button class="context-close" type="button" @click="emit('cancel')">取消</button>
    </div>
    <div class="manual-summary">
      <strong>已分配 {{ summary.assignedCount }}/{{ view.player_count }}</strong>
      <div class="composition-row">
        <span v-for="team in teamSummary" :key="team.label" :class="{ mismatch: team.selected !== team.expected }">
          {{ team.label }} {{ team.selected }}/{{ team.expected }}
        </span>
      </div>
      <p v-for="warning in summary.warnings" :key="warning" class="inline-warning">{{ warning }}</p>
      <p v-for="item in summary.hardErrors" :key="item" class="inline-error">{{ item }}</p>
    </div>
    <template v-if="selectedSeat">
      <RolePicker
        :roles="view.roles"
        :assignments="assignments"
        :selected-seat="selectedSeat"
        @toggle-role="emit('toggle-role', $event)"
      />
      <SpecialRoleFields
        v-if="selectedRoleId"
        :view="view"
        :seat="selectedSeat"
        :role-id="selectedRoleId"
        :fake-role="fakes[String(selectedSeat)] || ''"
        :lunatic-minions="lunaticMinions[String(selectedSeat)] || []"
        :lunatic-bluffs="lunaticBluffs[String(selectedSeat)] || []"
        @set-fake="emit('set-fake', $event)"
        @toggle-minion="emit('toggle-lunatic-minion', $event)"
        @toggle-bluff="emit('toggle-lunatic-bluff', $event)"
      />
    </template>
    <p v-else class="manual-empty">点击中央魔典中的座位，再为它选择角色。</p>
    <section v-if="hasGodfather" class="manual-subsection">
      <h4>教父外来者调整</h4>
      <div class="segmented-control">
        <button type="button" :class="{ active: godfatherAdjustment === 1 }" @click="emit('set-godfather', 1)">+1 外来者</button>
        <button type="button" :class="{ active: godfatherAdjustment === -1 }" @click="emit('set-godfather', -1)">−1 外来者</button>
      </div>
    </section>
    <BluffPicker :roles="bluffRoles" :selected="bluffs" title="恶魔的三个伪装" @toggle="emit('toggle-bluff', $event)" />
    <p v-if="error?.key === 'assign-manual'" class="inline-error" role="alert">{{ error.message }}</p>
    <div class="manual-actions">
      <button class="btn" type="button" @click="emit('cancel')">放弃草稿</button>
      <button class="btn primary" type="button" :disabled="!connected || pending.includes('assign-manual') || !summary.valid" @click="emit('confirm')">
        {{ pending.includes('assign-manual') ? '正在提交…' : '确认发身份' }}
      </button>
    </div>
  </div>
</template>
