<script setup>
defineProps({ view: { type: Object, required: true } })
defineEmits(['select-participant'])
</script>

<template>
  <section class="public-board" aria-label="公开座位盘">
    <h2>小镇广场</h2>
    <div class="public-seats">
      <button
        v-for="slot in view.seats || []"
        :key="slot.seat"
        :data-seat="slot.seat"
        class="public-seat"
        :class="{ 'is-dead': slot.player?.alive === false, 'is-me': slot.is_me }"
        :disabled="!slot.player"
        type="button"
        @click="$emit('select-participant', slot.seat)"
      >
        <strong>{{ slot.seat }}号</strong>
        <span>{{ slot.player?.name || '空座' }}</span>
        <small v-if="slot.dead_vote_left">🗳 死票</small>
      </button>
    </div>
    <div v-if="view.travelers_public?.length" class="travelers">
      <h3>旅行者</h3>
      <button
        v-for="traveler in view.travelers_public"
        :key="traveler.id"
        :data-traveler="traveler.id"
        class="traveler"
        :class="{ 'is-dead': traveler.alive === false }"
        type="button"
        @click="$emit('select-participant', traveler.id)"
      >
        🎒 {{ traveler.name }}<span v-if="traveler.role"> · {{ traveler.role.name }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.public-board { padding: 16px; display: grid; gap: 12px; border: 1px solid var(--line); border-radius: 18px; background: var(--panel); }
.public-board h2 { font-size: 18px; }
.public-seats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.public-seat, .traveler { padding: 9px; border: 1px solid var(--line); border-radius: 12px; background: color-mix(in srgb, var(--panel) 80%, black); color: var(--text); }
.public-seat { min-height: 66px; display: grid; gap: 2px; }
.public-seat span, .public-seat small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.public-seat small { color: #ffd479; }
.public-seat:disabled { border-style: dashed; }
.public-seat.is-me { border-color: var(--accent); }
.is-dead { filter: grayscale(.8); opacity: .58; }
.travelers { display: grid; gap: 8px; }
.travelers h3 { color: var(--dim); font-size: 14px; }
.traveler { text-align: left; }
@media (max-width: 380px) { .public-seats { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
