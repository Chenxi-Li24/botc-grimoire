<script setup>
const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, required: true },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits(['set-sentinel', 'toggle-fabled'])

const sentinelChoices = [
  { value: 0, label: '关闭' },
  { value: 1, label: '+1 外来者' },
  { value: -1, label: '−1 外来者' },
  { value: 2, label: '在场不调整' },
]

function hasFabled(id) {
  return props.view.fabled?.some((item) => item.id === id) || false
}
</script>

<template>
  <details class="advanced-settings">
    <summary>高级设置</summary>
    <div class="advanced-body">
      <div>
        <p class="field-label">哨兵调整</p>
        <div class="segmented-control">
          <button
            v-for="choice in sentinelChoices"
            :key="choice.value"
            type="button"
            :aria-pressed="view.sentinel === choice.value"
            :class="{ active: view.sentinel === choice.value }"
            :disabled="!connected || pending.includes('sentinel')"
            @click="emit('set-sentinel', choice.value)"
          >{{ choice.label }}</button>
        </div>
      </div>
      <div v-if="view.fabled_pool?.length">
        <p class="field-label">传奇角色</p>
        <div class="choice-grid">
          <button
            v-for="role in view.fabled_pool"
            :key="role.id"
            class="choice-chip"
            :class="{ active: hasFabled(role.id) }"
            type="button"
            :aria-pressed="hasFabled(role.id)"
            :title="role.ability"
            :disabled="!connected || pending.includes(`fabled:${role.id}`)"
            @click="emit('toggle-fabled', { id: role.id, on: !hasFabled(role.id) })"
          >{{ role.name }}</button>
        </div>
      </div>
      <p v-if="error?.key === 'sentinel' || error?.key?.startsWith('fabled:')" class="inline-error" role="alert">
        {{ error.message }}
      </p>
    </div>
  </details>
</template>
