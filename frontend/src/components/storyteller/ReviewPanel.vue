<script setup>
const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})
const emit = defineEmits(['mark-review', 'back'])

function mark(item) {
  if (!item.mark || !props.connected || props.pending.includes('review:mark')) return
  emit('mark-review', {
    seat: item.mark.seat,
    night: item.mark.night,
    wrong: !item.wrong,
  })
}
</script>

<template>
  <main data-review-panel class="review-screen">
    <header class="review-screen-header">
      <div><p class="panel-eyebrow">终局复盘</p><h1>📜 复盘时间线</h1></div>
      <button data-review-back class="btn" type="button" @click="emit('back')">返回魔典</button>
    </header>
    <p v-if="error?.key === 'review:mark'" class="inline-error">{{ error.message }}</p>
    <p v-if="!view.review?.has_data" class="inline-note">本局没有可用的复盘记录（可能来自旧存档）。</p>
    <section v-for="group in view.review?.groups || []" :key="`${group.phase}:${group.label}`" class="review-screen-group">
      <h2>{{ group.label }}</h2>
      <div v-for="(item, index) in group.items" :key="index" class="review-screen-item" :class="{ wrong: item.wrong }">
        <p>{{ item.wrong ? '⚠ ' : '' }}{{ item.text }}<span v-if="item.why">（{{ item.why }}）</span></p>
        <button v-if="item.mark" :data-review-mark="`${item.mark.seat}:${item.mark.night}`" class="btn" type="button" :disabled="!connected || pending.includes('review:mark')" @click="mark(item)">{{ item.wrong ? '撤销标错' : '标错' }}</button>
      </div>
    </section>
  </main>
</template>
