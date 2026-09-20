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
</script>

<template>
  <section class="night-card pit-hag-card">
    <div class="night-card-heading"><h4>麻脸巫婆 · 创建角色</h4><span>先预览，再确认</span></div>
    <template v-if="preview">
      <dl class="preview-summary">
        <div><dt>目标</dt><dd>{{ preview.target_seat }}号</dd></div>
        <div><dt>角色变化</dt><dd>{{ preview.old_character || '无' }} → {{ preview.new_character }}</dd></div>
        <div><dt>阵营</dt><dd>{{ preview.old_alignment || '未知' }} → {{ preview.new_alignment || '保持' }}</dd></div>
        <div><dt>夜序位置</dt><dd>{{ preview.relative_timing || '按新角色夜序调整' }}</dd></div>
      </dl>
      <ul v-if="preview.warnings?.length || preview.consequences?.length" class="night-hints">
        <li v-for="warning in preview.warnings || []" :key="warning">{{ warning }}</li>
        <li v-for="consequence in preview.consequences || []" :key="consequence">{{ consequence }}</li>
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
