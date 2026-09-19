<script setup>
import { computed } from 'vue'

const props = defineProps({ view: { type: Object, required: true } })
const seatedCount = computed(() => props.view.seats?.filter((seat) => seat.player).length || 0)
const joinedPlayers = computed(() => props.view.players?.length || seatedCount.value)
</script>

<template>
  <div class="panel-content join-context">
    <div>
      <p class="panel-eyebrow">当前任务</p>
      <h2>玩家加入</h2>
    </div>
    <img class="join-qr" :src="'/api/qr'" alt="玩家加入二维码">
    <div class="room-code-block">
      <span>房间号</span>
      <strong>{{ view.room_code }}</strong>
    </div>
    <p>已入座 {{ seatedCount }}/{{ view.player_count }}</p>
    <p class="hint">当前已加入 {{ joinedPlayers }} 人，扫码会自动预填房间号。</p>
  </div>
</template>
