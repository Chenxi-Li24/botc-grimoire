<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { teamLabel } from '../../presentation/player.js'
import { roleIconUrl } from '../../presentation/roleIcons.js'

const props = defineProps({
  view: { type: Object, required: true },
  playerId: { type: String, required: true },
})
const emit = defineEmits(['active-change'])
const stage = ref(null)
const flipped = ref(false)
const welcomeButton = ref(null)
const flipButton = ref(null)
const enterButton = ref(null)
const role = computed(() => props.view.traveler?.role || props.view.role_changed || props.view.me?.role || null)
const team = computed(() => props.view.traveler?.align || props.view.team_changed || role.value?.team)
const roleIcon = computed(() => roleIconUrl(role.value?.id))
const welcomeKey = computed(() => `botc_welcome_${props.playerId}`)
const roleKey = computed(() => `botc_role_seen_${props.playerId}`)

function updateStage(next) {
  stage.value = next
  emit('active-change', Boolean(next))
}

watch(() => props.view, () => {
  if (stage.value) return
  if (globalThis.sessionStorage?.getItem(welcomeKey.value) !== '1') {
    updateStage('welcome')
  } else if (role.value && globalThis.sessionStorage?.getItem(roleKey.value) !== '1') {
    updateStage('role')
  } else {
    updateStage(null)
  }
}, { immediate: true })

watch([stage, flipped], async () => {
  await nextTick()
  if (stage.value === 'welcome') welcomeButton.value?.focus()
  else if (stage.value === 'role') (flipped.value ? enterButton.value : flipButton.value)?.focus()
}, { immediate: true, flush: 'post' })

function enterTown() {
  globalThis.sessionStorage?.setItem(welcomeKey.value, '1')
  updateStage(role.value && globalThis.sessionStorage?.getItem(roleKey.value) !== '1' ? 'role' : null)
}

function enterSquare() {
  globalThis.sessionStorage?.setItem(roleKey.value, '1')
  updateStage(null)
}
</script>

<template>
  <section v-if="stage === 'welcome'" class="ceremony ceremony-welcome" data-player-welcome role="dialog" aria-modal="true" aria-label="欢迎入局">
    <div class="ceremony-tower" aria-hidden="true">♜</div>
    <div class="ceremony-text">
      <span class="ceremony-kicker">BLOOD ON THE CLOCKTOWER</span>
      <h1>欢迎来到鸦木布拉夫镇</h1>
      <p>{{ view.me?.name || '旅人' }}，钟楼之下，故事即将开始。</p>
      <small>剧本 · {{ view.script }}</small>
      <button ref="welcomeButton" data-welcome-enter class="ceremony-action" type="button" @click="enterTown">进入小镇 →</button>
    </div>
  </section>

  <section v-else-if="stage === 'role' && role" class="ceremony ceremony-identity" data-identity-reveal role="dialog" aria-modal="true" aria-label="领取身份">
    <span class="ceremony-kicker">仅你可见 · 请勿向他人展示屏幕</span>
    <div class="identity-flip-wrap" :class="{ flipped }">
      <button v-if="!flipped" ref="flipButton" data-identity-flip class="identity-face identity-back" type="button" @click="flipped = true">
        <span class="identity-sigil">✦</span>
        <strong>你的身份已抵达</strong>
        <small>轻触翻开卡片</small>
      </button>
      <article v-else class="identity-face identity-front" :data-team="team">
        <span>{{ teamLabel(team) }}</span>
        <img v-if="roleIcon" :src="roleIcon" alt="" width="110" height="110" />
        <strong>{{ role.name }}</strong>
        <small v-if="role.en">{{ role.en }}</small>
        <p>{{ role.ability }}</p>
      </article>
    </div>
    <button v-if="flipped" ref="enterButton" data-identity-enter class="ceremony-action" type="button" @click="enterSquare">记住身份，进入广场 →</button>
  </section>
</template>

<style scoped>
.ceremony { position: fixed; inset: 0; z-index: 1100; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 28px; overflow: auto; padding: max(22px, env(safe-area-inset-top)) 20px max(22px, env(safe-area-inset-bottom)); color: #f6ebdc; text-align: center; background: radial-gradient(circle at 50% 30%, #4b3036 0, #201820 50%, #100c11 100%); }
.ceremony-welcome::before { content: ''; position: absolute; inset: 0; pointer-events: none; opacity: .18; background: repeating-linear-gradient(90deg, transparent 0 59px, #d7ad74 60px 61px); mask-image: linear-gradient(transparent, black 60%, black); }
.ceremony-tower { font-size: clamp(110px, 35vw, 210px); line-height: 1; color: #b88961; text-shadow: 0 0 55px #b3564b; animation: tower-rise .7s ease-out both; }
.ceremony-text { position: relative; display: grid; justify-items: center; gap: 15px; }
.ceremony-kicker { color: #d6ad75; font-size: 11px; letter-spacing: .26em; }
.ceremony h1 { margin: 0; font-size: clamp(27px, 7vw, 46px); font-weight: 500; letter-spacing: .06em; }
.ceremony p { margin: 0; line-height: 1.65; }
.ceremony-text small { color: #d8bca6; }
.ceremony-action { min-height: 48px; margin-top: 12px; padding: 11px 22px; border: 1px solid #d4a86d; border-radius: 999px; background: #a96745; color: #fff5e9; font: inherit; cursor: pointer; }
.identity-flip-wrap { width: min(82vw, 330px); min-height: min(55vh, 450px); perspective: 900px; }
.identity-face { width: 100%; min-height: min(55vh, 450px); padding: 24px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 13px; border: 2px solid #c69c68; border-radius: 22px; background: linear-gradient(155deg, #49352e, #211b22 65%); box-shadow: 0 20px 65px #0008, inset 0 0 0 6px #a27a4830; color: #f6e8d7; text-align: center; animation: card-flip .55s ease both; }
.identity-back { cursor: pointer; font: inherit; }
.identity-back strong { font-size: 23px; }
.identity-back small, .identity-front small { color: #d7bea9; }
.identity-sigil { font-size: 90px; color: #d8b077; }
.identity-front[data-team='townsfolk'], .identity-front[data-team='outsider'], .identity-front[data-team='good'] { border-color: #5fa5db; background: linear-gradient(155deg, #243b56, #18232f 65%); }
.identity-front[data-team='minion'], .identity-front[data-team='demon'], .identity-front[data-team='evil'] { border-color: #d46a68; background: linear-gradient(155deg, #592a32, #28171f 65%); }
.identity-front img { object-fit: contain; max-width: 100%; }
.identity-front strong { font-size: 32px; }
.identity-front p { max-width: 26ch; font-size: 14px; }
@keyframes tower-rise { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
@keyframes card-flip { from { transform: rotateY(90deg); opacity: .3; } to { transform: rotateY(0); opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .ceremony *, .ceremony::before { animation: none !important; transition: none !important; } }
</style>
