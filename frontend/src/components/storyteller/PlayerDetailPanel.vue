<script setup>
import { computed } from 'vue'

const teamLabels = {
  townsfolk: '镇民', outsider: '外来者', minion: '爪牙', demon: '恶魔', traveler: '旅行者',
}
const markerLabels = {
  poisoned: '中毒', drunk: '醉酒', mad: '疯狂', redherring: '宿敌',
  'role-change': '角色转变', 'team-change': '阵营转变',
}

const props = defineProps({ seat: { type: Object, required: true } })
defineEmits(['close'])

const role = computed(() => props.seat.player?.role || props.seat.assigned_role || null)
const teamLabel = computed(() => teamLabels[role.value?.team] || role.value?.team || '未分配')
const markers = computed(() => (props.seat.markers || []).map((marker) => markerLabels[marker] || marker))
</script>

<template>
  <div class="panel-content player-context">
    <div class="context-heading">
      <div>
        <p class="panel-eyebrow">{{ seat.seat }}号玩家</p>
        <h2>{{ seat.player.name }}</h2>
      </div>
      <button data-clear-selection class="context-close" type="button" @click="$emit('close')">
        返回当前任务
      </button>
    </div>
    <dl class="player-summary">
      <div><dt>角色</dt><dd>{{ role?.name || '未分配' }}</dd></div>
      <div><dt>阵营</dt><dd>{{ teamLabel }}</dd></div>
      <div><dt>状态</dt><dd>{{ seat.player.alive ? '存活' : '死亡' }}</dd></div>
    </dl>
    <div v-if="markers.length" class="detail-markers">
      <span v-for="marker in markers" :key="marker">{{ marker }}</span>
    </div>
    <p v-else class="hint">当前没有状态标记</p>
    <a class="btn primary" href="/legacy/#/storyteller">在完整控制台中操作</a>
  </div>
</template>
