<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  confirmLabel: { type: String, required: true },
  summary: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  danger: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm'])
const armed = ref(false)
let timer = null

function disarm() {
  armed.value = false
  if (timer !== null) clearTimeout(timer)
  timer = null
}

function activate() {
  if (props.disabled) return
  if (armed.value) {
    disarm()
    emit('confirm')
    return
  }
  armed.value = true
  timer = setTimeout(disarm, 3000)
}

watch(() => props.summary, disarm)
watch(() => props.disabled, (disabled) => { if (disabled) disarm() })
onBeforeUnmount(disarm)
</script>

<template>
  <div class="confirm-action" :class="{ 'is-armed': armed }">
    <p v-if="armed && summary" class="inline-warning">{{ summary }}</p>
    <button
      class="btn"
      :class="{ danger }"
      type="button"
      :disabled="disabled"
      :aria-pressed="armed"
      @click="activate"
    >
      {{ armed ? confirmLabel : label }}
    </button>
  </div>
</template>
