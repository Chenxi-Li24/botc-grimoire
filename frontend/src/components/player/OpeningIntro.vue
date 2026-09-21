<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const emit = defineEmits(['close'])
let timer = null
const skipButton = ref(null)

onMounted(() => {
  skipButton.value?.focus()
  const reduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  timer = setTimeout(() => emit('close'), reduced ? 900 : 3200)
})
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <section class="opening-intro" data-opening-intro role="dialog" aria-modal="true" aria-label="首夜结束">
    <div class="opening-sky" aria-hidden="true">
      <div class="opening-moon" />
      <div class="opening-tower"><div class="opening-clock" /></div>
    </div>
    <div class="opening-copy">
      <span class="opening-kicker">血染钟楼</span>
      <h2>说书人被吊死在钟楼之上</h2>
      <p>天亮了，故事由你们继续。</p>
    </div>
    <button ref="skipButton" class="opening-skip" data-opening-skip type="button" @click="emit('close')">跳过 →</button>
  </section>
</template>

<style scoped>
.opening-intro { position: fixed; inset: 0; z-index: 1000; overflow: hidden; display: grid; place-items: center; background: #100b10; color: #f3e8dc; }
.opening-sky { position: absolute; inset: 0; background: radial-gradient(circle at 52% 22%, #663534 0, #251820 35%, #0d0b13 75%); }
.opening-moon { position: absolute; width: min(43vw, 320px); aspect-ratio: 1; border-radius: 50%; top: 10%; left: 50%; transform: translateX(-50%); background: radial-gradient(circle at 35% 30%, #ffe0ad, #b95d52 63%, #68343a); box-shadow: 0 0 110px #b6665360; animation: opening-moon 3.2s ease-out both; }
.opening-tower { position: absolute; left: 50%; bottom: -9vh; width: clamp(135px, 22vw, 230px); height: 75vh; transform: translateX(-50%); background: linear-gradient(90deg, #090a0f, #19141b 48%, #08090d); clip-path: polygon(0 24%, 22% 24%, 22% 12%, 50% 0, 78% 12%, 78% 24%, 100% 24%, 88% 100%, 12% 100%); box-shadow: 0 0 55px #000; }
.opening-clock { position: absolute; top: 25%; left: 50%; width: 57%; aspect-ratio: 1; transform: translateX(-50%); border: 6px solid #76554c; border-radius: 50%; background: radial-gradient(circle, #f1c18b 0 5%, #271c20 7% 100%); box-shadow: inset 0 0 18px #000, 0 0 20px #8b4a4260; }
.opening-clock::before, .opening-clock::after { content: ''; position: absolute; left: 50%; bottom: 50%; width: 3px; transform-origin: bottom; background: #e3b477; }
.opening-clock::before { height: 32%; transform: rotate(30deg); }
.opening-clock::after { height: 23%; transform: rotate(240deg); }
.opening-copy { z-index: 1; align-self: end; margin-bottom: clamp(95px, 18vh, 180px); padding: 20px; text-align: center; text-shadow: 0 2px 12px #000, 0 0 30px #000; animation: opening-copy 1.5s ease both; }
.opening-kicker { display: block; color: #d7a978; letter-spacing: .5em; font-size: 13px; }
.opening-copy h2 { margin: 15px 0 7px; font-size: clamp(25px, 5vw, 48px); font-weight: 500; letter-spacing: .06em; }
.opening-copy p { margin: 0; color: #dac7bd; font-size: 14px; }
.opening-skip { position: absolute; z-index: 2; right: max(20px, env(safe-area-inset-right)); top: max(20px, env(safe-area-inset-top)); padding: 10px 14px; border: 1px solid #a98c81; border-radius: 999px; background: #1c151ac9; color: #f3e8dc; cursor: pointer; }
@keyframes opening-moon { from { opacity: .25; transform: translateX(-50%) scale(.8); } to { opacity: 1; transform: translateX(-50%) scale(1); } }
@keyframes opening-copy { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }
@media (prefers-reduced-motion: reduce) { .opening-intro * { animation: none !important; transition: none !important; } }
</style>
