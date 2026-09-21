<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { playBell } from '../../presentation/bell.js'

const props = defineProps({
  view: { type: Object, required: true },
  soundEnabled: { type: Boolean, default: false },
  volume: { type: Number, default: 35 },
})
const emit = defineEmits(['sound-active', 'scene-change'])
const active = ref(null)
let waiting = []
let sceneTimer = null
let soundTimer = null
let soundStop = null

const labels = {
  night: { title: '夜幕降临', caption: '灯光熄灭，请所有玩家闭眼。' },
  day: { title: '天亮了', caption: '钟声响起，请所有玩家睁眼。' },
  execution: { title: '处决已定', caption: '钟摆停下，结果已经揭晓。' },
}

function stopSound() {
  clearTimeout(soundTimer)
  if (soundStop) soundStop()
  soundStop = null
  emit('sound-active', false)
}

function nextScene() {
  clearTimeout(sceneTimer)
  stopSound()
  active.value = waiting.shift() || null
  emit('scene-change', active.value)
  if (!active.value) return
  if (props.soundEnabled) {
    const bell = playBell(active.value, props.volume)
    if (bell) {
      soundStop = bell.stop
      emit('sound-active', true)
      soundTimer = setTimeout(stopSound, bell.durationMs)
    }
  }
  const reduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const duration = reduced ? 650 : active.value === 'execution' ? 1800 : 2400
  sceneTimer = setTimeout(nextScene, duration)
}

watch(() => props.view, (current, previous) => {
  if (!previous || !current || current.phase === previous.phase) return
  const scenes = []
  if (previous.phase === 'day' && current.phase === 'night') {
    if ((current.nominations || []).some((item) => item.day === previous.day_no && item.executed)) {
      scenes.push('execution')
    }
    scenes.push('night')
  } else if (previous.phase === 'night' && current.phase === 'day') {
    scenes.push('day')
  }
  if (!scenes.length) return
  waiting = scenes
  nextScene()
})

watch(() => props.soundEnabled, (enabled) => { if (!enabled) stopSound() })
onBeforeUnmount(() => {
  clearTimeout(sceneTimer)
  stopSound()
})
</script>

<template>
  <div v-if="active" class="stage-transition" :class="`stage-transition--${active}`"
       :data-scene-transition="active" role="status" aria-live="polite">
    <div class="stage-transition-art" aria-hidden="true">
      <div class="stage-transition-halo" />
      <div class="stage-transition-clock"><i /><b /></div>
    </div>
    <div class="stage-transition-copy">
      <span>血染钟楼</span>
      <h2>{{ labels[active].title }}</h2>
      <p>{{ labels[active].caption }}</p>
    </div>
    <button data-transition-skip type="button" @click="nextScene">跳过 →</button>
  </div>
</template>

<style scoped>
.stage-transition { position: fixed; inset: 0; z-index: 300; display: grid; place-items: center; overflow: hidden; pointer-events: none; color: #f6ebe1; background: #120c12e8; animation: scene-enter .5s ease-out both; }
.stage-transition--night { background: radial-gradient(circle at 50% 43%, #3d1b22ed, #100d13fa 68%); }
.stage-transition--day { color: #472c19; background: radial-gradient(circle at 50% 42%, #fff3d9ee, #f6b95bf5 70%, #ad6039); }
.stage-transition--execution { background: radial-gradient(circle at 50% 45%, #5b2028f5, #180d13fc 65%); }
.stage-transition-art { position: absolute; inset: 0; display: grid; place-items: center; }
.stage-transition-halo { width: min(67vw, 500px); aspect-ratio: 1; border-radius: 50%; background: #d3735036; filter: blur(24px); animation: halo-breathe 2.4s ease-in-out both; }
.stage-transition--day .stage-transition-halo { background: #ffe9a9bb; }
.stage-transition-clock { position: absolute; width: clamp(125px, 23vw, 230px); aspect-ratio: 1; border: 5px solid currentColor; border-radius: 50%; opacity: .36; box-shadow: 0 0 55px currentColor; }
.stage-transition-clock i, .stage-transition-clock b { position: absolute; left: 50%; bottom: 50%; width: 3px; background: currentColor; transform-origin: bottom; }
.stage-transition-clock i { height: 32%; transform: rotate(15deg); }
.stage-transition-clock b { height: 22%; transform: rotate(250deg); }
.stage-transition--night .stage-transition-art { animation: lights-out 2.4s ease-in both; }
.stage-transition--day .stage-transition-art { animation: lights-on 2.4s ease-out both; }
.stage-transition--execution .stage-transition-clock { animation: clock-stop 1s ease-out both; }
.stage-transition-copy { position: relative; text-align: center; padding: 20px; text-shadow: 0 2px 18px #0009; }
.stage-transition--day .stage-transition-copy { text-shadow: 0 2px 15px #fff9; }
.stage-transition-copy span { display: block; letter-spacing: .5em; font-size: 12px; }
.stage-transition-copy h2 { margin: 10px 0; font-size: clamp(30px, 5vw, 58px); font-weight: 500; letter-spacing: .12em; }
.stage-transition-copy p { margin: 0; font-size: 14px; }
.stage-transition button { position: absolute; right: 24px; top: 24px; pointer-events: auto; cursor: pointer; border: 1px solid currentColor; border-radius: 999px; padding: 9px 13px; background: #1510188c; color: #fff2e9; }
.stage-transition--day button { background: #6b432b; }
@keyframes scene-enter { from { opacity: 0; } to { opacity: 1; } }
@keyframes halo-breathe { from { transform: scale(1.2); opacity: .8; } to { transform: scale(.8); opacity: .4; } }
@keyframes lights-out { from { filter: brightness(2.4); opacity: .2; } to { filter: brightness(.2); opacity: 1; } }
@keyframes lights-on { from { filter: brightness(.2); opacity: .2; } to { filter: brightness(2); opacity: 1; } }
@keyframes clock-stop { from { transform: rotate(-20deg); } to { transform: rotate(0deg); } }
@media (prefers-reduced-motion: reduce) { .stage-transition * { animation: none !important; transition: none !important; } }
</style>
