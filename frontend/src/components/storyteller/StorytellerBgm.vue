<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { BGM_TRACKS, sceneForView } from '../../presentation/bgm.js'

const props = defineProps({
  view: { type: Object, required: true },
  reviewOpen: { type: Boolean, default: false },
})
const enabled = ref(false)
const muted = ref(false)
const volume = ref(Number(globalThis.localStorage?.getItem('botc_bgm_volume') ?? 35))
const selection = ref('auto')
const introDay = ref(false)
const error = ref('')
let audio = null
let introTimer = null

const automaticScene = computed(() => sceneForView(props.view, props.reviewOpen))
const scene = computed(() => selection.value !== 'auto' ? selection.value : introDay.value ? 'day' : automaticScene.value)
const track = computed(() => BGM_TRACKS[scene.value])

watch(() => props.view.phase, (phase, previous) => {
  if (phase !== 'day' || previous !== 'night' || props.view.winner) return
  introDay.value = true
  clearTimeout(introTimer)
  introTimer = setTimeout(() => { introDay.value = false }, 12000)
})

function play() {
  if (!audio) return
  audio.volume = Math.max(0, Math.min(1, Number(volume.value) / 100))
  audio.muted = muted.value
  audio.loop = scene.value !== 'victory'
  if (audio.getAttribute('src') !== track.value.src) {
    audio.setAttribute('src', track.value.src)
    audio.load()
  }
  if (enabled.value) {
    audio.play().then(() => { error.value = '' }).catch(() => {
      error.value = '浏览器阻止了自动播放，请点击“启动配乐”重试。'
      enabled.value = false
    })
  } else audio.pause()
}

watch([scene, enabled, muted, volume], () => {
  globalThis.localStorage?.setItem('botc_bgm_volume', String(volume.value))
  play()
})
onMounted(() => { audio = new Audio(); audio.preload = 'none'; play() })
onBeforeUnmount(() => { clearTimeout(introTimer); audio?.pause(); audio = null })
</script>

<template>
  <div data-storyteller-bgm class="storyteller-bgm" aria-label="说书人背景音乐">
    <span data-bgm-scene>🎵 {{ selection === 'auto' ? '自动' : '手动' }}：{{ track.label }}</span>
    <button data-bgm-toggle class="btn" type="button" @click="enabled = !enabled">{{ enabled ? '暂停配乐' : '启动配乐' }}</button>
    <label>曲目
      <select v-model="selection" data-bgm-select>
        <option value="auto">自动跟随阶段</option>
        <option v-for="(item, key) in BGM_TRACKS" :key="key" :value="key">{{ item.label }}</option>
      </select>
    </label>
    <label>音量 <input v-model="volume" data-bgm-volume type="range" min="0" max="100" /></label>
    <button data-bgm-mute class="btn" type="button" @click="muted = !muted">{{ muted ? '取消静音' : '静音' }}</button>
    <small v-if="error" role="status">{{ error }}</small>
  </div>
</template>

<style scoped>
.storyteller-bgm { min-height: 44px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 5px 16px; border-top: 1px solid var(--line); font-size: 12px; }
.storyteller-bgm > span { min-width: 100px; color: var(--dim); }
.storyteller-bgm label { display: inline-flex; align-items: center; gap: 5px; }
.storyteller-bgm select { max-width: 145px; padding: 5px; border: 1px solid var(--line); border-radius: 7px; background: var(--panel); color: var(--text); }
.storyteller-bgm input { width: 90px; }
.storyteller-bgm small { color: #ffbe89; }
@media (max-width: 700px) { .storyteller-bgm { gap: 5px; padding: 5px 8px; } .storyteller-bgm input { width: 65px; } }
</style>
