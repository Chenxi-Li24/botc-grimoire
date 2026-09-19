<script setup>
defineProps({
  connected: { type: Boolean, required: true },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
defineEmits(['start'])
</script>

<template>
  <section class="start-control">
    <p class="inline-warning">所有座位都已有身份，可以在人未到齐时开局。迟到玩家入座后会继承该座身份。</p>
    <button class="btn primary" type="button" :disabled="!connected || pending.includes('start')" @click="$emit('start')">
      {{ pending.includes('start') ? '正在开始…' : '开始游戏' }}
    </button>
    <p v-if="error?.key === 'start'" class="inline-error" role="alert">{{ error.message }}</p>
  </section>
</template>
