<script setup>
import AdvancedSettings from './AdvancedSettings.vue'
import SetupControls from './SetupControls.vue'

defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, required: true },
  pending: { type: String, default: null },
  error: { type: Object, default: null },
})
defineEmits(['configure', 'set-sentinel', 'toggle-fabled'])
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
