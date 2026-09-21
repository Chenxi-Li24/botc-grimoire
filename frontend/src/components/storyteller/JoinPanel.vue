<script setup>
import { computed, ref, watch } from 'vue'
import { api } from '../../services/api.js'

const props = defineProps({ view: { type: Object, required: true } })
const seatedCount = computed(() => props.view.seats?.filter((seat) => seat.player).length || 0)
const joinedPlayers = computed(() => props.view.players?.length || seatedCount.value)
const links = ref({ local_url: null, public_url: null })
const linkError = ref(false)

watch(() => props.view.room_code, async (_, __, onCleanup) => {
  let active = true
  onCleanup(() => { active = false })
  links.value = { local_url: null, public_url: null }
  linkError.value = false
  try {
    const result = await api('/api/join-links')
    if (active) links.value = result
  } catch {
    if (active) linkError.value = true
  }
}, { immediate: true })

function qrSrc(mode) {
  return `/api/qr?mode=${mode}&room=${encodeURIComponent(props.view.room_code)}`
}
</script>

<template>
  <div class="panel-content join-context">
    <div>
      <p class="panel-eyebrow">当前任务</p>
      <h2>玩家加入</h2>
    </div>
    <div class="join-code-card join-code-primary">
      <div class="join-code-heading"><strong>本地码</strong><span>优先使用本地码</span></div>
      <img data-join-qr="local" class="join-qr" :src="qrSrc('local')" alt="本地玩家加入二维码">
      <a v-if="links.local_url" data-join-link="local" class="join-link" :href="links.local_url">{{ links.local_url }}</a>
    </div>
    <div v-if="links.public_url" class="join-code-card">
      <div class="join-code-heading"><strong>公网备用码</strong></div>
      <img data-join-qr="public" class="join-qr" :src="qrSrc('public')" alt="公网玩家加入二维码">
      <a data-join-link="public" class="join-link" :href="links.public_url">{{ links.public_url }}</a>
    </div>
    <p v-else class="hint">{{ linkError ? '公网链接暂时无法读取' : '公网码尚未配置' }}</p>
    <p class="hint">本地连接不上时，请改扫公网备用码。</p>
    <div class="room-code-block">
      <span>房间号</span>
      <strong>{{ view.room_code }}</strong>
    </div>
    <p>已入座 {{ seatedCount }}/{{ view.player_count }}</p>
    <p class="hint">当前已加入 {{ joinedPlayers }} 人，扫码会自动预填房间号。</p>
  </div>
</template>
