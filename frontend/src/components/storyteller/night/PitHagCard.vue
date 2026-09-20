<script setup>
import { computed } from 'vue'

const props = defineProps({
  step: { type: Object, default: null },
  preview: { type: Object, default: null },
  targetSeat: { type: Number, default: null },
  characterId: { type: String, default: null },
  roles: { type: Array, default: () => [] },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
const emit = defineEmits(['set-character', 'preview', 'confirm'])
const busy = computed(() => props.pending.some((key) => key.startsWith('night:pit-hag:')))
const timingLabels = {
  immediate_start_knowing: '立即补发首夜信息',
  later_this_night: '插入本夜后续夜序',
  next_night: '从下一夜开始行动',
  passive_or_no_action: '无需插入夜序',
}
const alignmentLabels = { good: '善良', evil: '邪恶' }
const consequenceLabels = {
  all_deaths_this_night_are_storyteller_arbitrary: '本夜所有死亡由说书人决定',
  created_demon_has_no_normal_kill_choice_this_night: '新生恶魔本夜没有常规刀人行动',
  passive_and_non_kill_ability_parts_start_immediately: '非刀人及被动能力立即生效',
  demon_kill_only_triggers_do_not_fire_for_arbitrary_deaths: '任意死亡不触发“被恶魔杀死”类能力',
}
function roleName(roleId) {
  return props.roles.find((role) => role.id === roleId)?.name || roleId || '无'
}
function consequenceLabel(value) {
  return consequenceLabels[value] || value
}
</script>

<template>
  <section class="night-card pit-hag-card">
    <div class="night-card-heading"><h4>麻脸巫婆 · 创建角色</h4><span>先预览，再确认</span></div>
    <template v-if="preview">
      <dl class="preview-summary">
        <div><dt>目标</dt><dd>{{ preview.target_seat }}号</dd></div>
        <div><dt>角色变化</dt><dd>{{ roleName(preview.old_character) }} → {{ roleName(preview.new_character) }}</dd></div>
        <div><dt>阵营</dt><dd>{{ alignmentLabels[preview.alignment] || preview.alignment || '未知' }}（保持）</dd></div>
        <div><dt>夜序位置</dt><dd>{{ timingLabels[preview.relative_order] || preview.relative_order || '按新角色夜序调整' }}</dd></div>
      </dl>
      <ul v-if="preview.warnings?.length || preview.demon_consequences?.length" class="night-hints">
        <li v-for="warning in preview.warnings || []" :key="warning">{{ warning }}</li>
        <li v-for="consequence in preview.demon_consequences || []" :key="consequence">{{ consequenceLabel(consequence) }}</li>
      </ul>
      <button class="btn primary" type="button" :disabled="!connected || busy" @click="emit('confirm', { action: 'confirm', preview_id: preview.id })">确认角色变化</button>
    </template>
    <template v-else>
      <label class="field-row">要创建的角色
        <select :value="characterId || ''" @change="emit('set-character', $event.target.value || null)">
          <option value="">请选择角色</option>
          <optgroup v-for="team in ['townsfolk', 'outsider', 'minion', 'demon']" :key="team" :label="team">
            <option v-for="role in roles.filter((item) => item.team === team)" :key="role.id" :value="role.id">{{ role.name }}</option>
          </optgroup>
        </select>
      </label>
      <p class="inline-note">先从座位图中选择一个目标；新角色若轮次尚未经过，会立即插入本夜后续顺序。新生恶魔本夜不能刀人，但其他能力仍按规则执行。</p>
      <button
        class="btn primary"
        type="button"
        :disabled="!connected || busy || !targetSeat || !characterId || !step?.actor_seat"
        @click="emit('preview', { action: 'preview', step_id: step.id, actor_seat: step.actor_seat, target_seat: targetSeat, character_id: characterId })"
      >预览角色变化</button>
    </template>
  </section>
</template>
