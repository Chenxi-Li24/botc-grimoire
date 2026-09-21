<script setup>
defineProps({
  phase: { type: String, default: 'lobby' },
  leftOpen: { type: Boolean, default: false },
  rightOpen: { type: Boolean, default: false },
})

const emit = defineEmits(['close-drawer'])
</script>

<template>
  <div class="storyteller-shell" :data-phase="phase">
    <header data-shell-header class="storyteller-header">
      <slot name="header" />
    </header>
    <slot name="music" />
    <div class="storyteller-grid">
      <aside
        data-shell-controls
        class="storyteller-panel storyteller-controls"
        :class="{ 'is-open': leftOpen }"
      >
        <slot name="controls" />
      </aside>
      <section data-shell-board class="storyteller-panel storyteller-board">
        <slot name="board" />
      </section>
      <aside
        data-shell-context
        class="storyteller-panel storyteller-context"
        :class="{ 'is-open': rightOpen }"
      >
        <slot name="context" />
      </aside>
    </div>
    <button
      v-if="leftOpen || rightOpen"
      class="storyteller-backdrop"
      type="button"
      aria-label="关闭侧栏"
      @click="emit('close-drawer')"
    />
  </div>
</template>
