<script setup>
const props = defineProps({ view: { type: Object, required: true } })
defineEmits(['select-participant'])

function seatPosition(index) {
  const count = props.view.seats?.length || 1
  const angle = (2 * Math.PI * index) / count - Math.PI / 2
  const percent = (value) => `${Number(value.toFixed(3))}%`
  return {
    '--seat-x': percent(50 + 36 * Math.cos(angle)),
    '--seat-y': percent(50 + 36 * Math.sin(angle)),
  }
}
</script>

<template>
  <section class="public-board" aria-label="公开座位盘">
    <h2>小镇广场</h2>
    <div
      class="public-seats"
      :style="{ '--seat-size-percent': `${220 / (view.seats?.length || 1)}%` }"
    >
      <button
        v-for="(slot, index) in view.seats || []"
        :key="slot.seat"
        :data-seat="slot.seat"
        class="public-seat"
        :class="{ 'is-dead': slot.player?.alive === false, 'is-me': slot.is_me }"
        :style="seatPosition(index)"
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
.public-seats { position: relative; width: min(100%, 560px); aspect-ratio: 1; margin: 4px auto; border: 1px solid var(--line); border-radius: 50%; background: radial-gradient(circle, color-mix(in srgb, var(--panel) 86%, #493923), var(--panel) 72%); }
.public-seat, .traveler { padding: 9px; border: 1px solid var(--line); border-radius: 12px; background: color-mix(in srgb, var(--panel) 80%, var(--surface-tint)); color: var(--text); }
.public-seat { position: absolute; left: var(--seat-x); top: var(--seat-y); width: min(72px, 22%, var(--seat-size-percent)); min-height: 0; aspect-ratio: 1; padding: 3px; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px; border-radius: 50%; line-height: 1.1; cursor: pointer; }
.public-seat strong { font-size: clamp(8px, 1.8vw, 10px); }
.public-seat span { font-size: clamp(8px, 2.1vw, 12px); }
.public-seat small { font-size: clamp(7px, 1.8vw, 9px); }
.public-seat span, .public-seat small { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.public-seat small { color: #ffd479; }
.public-seat:disabled { border-style: dashed; }
.public-seat.is-me { border: 2px solid var(--accent); }
.is-dead { filter: grayscale(.8); opacity: .58; }
.travelers { display: grid; gap: 8px; }
.travelers h3 { color: var(--dim); font-size: 14px; }
.traveler { text-align: left; }
</style>
