<script setup>
import AdvancedSettings from './AdvancedSettings.vue'
import RoleAssignmentControls from './RoleAssignmentControls.vue'
import SetupControls from './SetupControls.vue'
import StartControl from './StartControl.vue'

defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, required: true },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
  manualActive: { type: Boolean, default: false },
})
defineEmits(['configure', 'set-sentinel', 'toggle-fabled', 'begin-manual', 'assign-random', 'start'])
</script>

<template>
  <div class="panel-content lobby-setup-panel">
    <SetupControls
      :view="view"
      :connected="connected"
      :pending="pending"
      :error="error"
      @configure="$emit('configure', $event)"
    />
    <RoleAssignmentControls
      :view="view"
      :connected="connected"
      :pending="pending"
      :error="error"
      :manual-active="manualActive"
      @begin-manual="$emit('begin-manual')"
      @assign-random="$emit('assign-random')"
    />
    <StartControl
      v-if="view.can_start && !manualActive"
      :connected="connected"
      :pending="pending"
      :error="error"
      @start="$emit('start')"
    />
    <AdvancedSettings
      :view="view"
      :connected="connected"
      :pending="pending"
      :error="error"
      @set-sentinel="$emit('set-sentinel', $event)"
      @toggle-fabled="$emit('toggle-fabled', $event)"
    />
  </div>
</template>
