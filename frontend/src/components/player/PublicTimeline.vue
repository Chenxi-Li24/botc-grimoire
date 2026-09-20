<script setup>
import { computed } from 'vue'
import { groupDeaths, groupNominations, participantLabel } from '../../presentation/player.js'

const props = defineProps({ view: { type: Object, required: true } })
const deathGroups = computed(() => groupDeaths(props.view.deaths || []))
const nominationGroups = computed(() => groupNominations(props.view.nominations || []))
const label = (id) => participantLabel(id, props.view.seats, props.view.travelers_public)

function nominationState(item) {
  if (item.executed) return typeof item.nominee === 'string' ? '已流放' : '已处决'
  if (item.passed) return '待处决'
  return '未通过'
}

function deathLabel(item) {
  const base = typeof item.seat === 'number' ? `${item.seat}号 ${item.name}` : `🎒 ${item.name}`
  return `${base}${item.empty ? '（空座）' : ''}${item.exiled ? '（流放）' : ''}`
}
</script>

<template>
  <section v-if="view.current || deathGroups.length || nominationGroups.length" class="public-timeline">
    <section v-if="view.current" class="timeline-card live-vote">
      <h2>🗳 实时投票</h2>
      <p>{{ label(view.current.nominator) }} 提名 {{ label(view.current.nominee) }}</p>
      <p>赞成 {{ view.current.votes.length }} 票</p>
      <div class="vote-chips">
        <span v-for="voter in view.current.votes" :key="voter">{{ label(voter) }}</span>
      </div>
    </section>

    <section v-if="deathGroups.length" class="timeline-card">
      <h2>☠ 已死亡</h2>
      <div v-for="group in deathGroups" :key="group.day" class="day-group">
        <h3>第 {{ group.day }} 天</h3>
        <p v-for="item in group.items" :key="item.seat">{{ deathLabel(item) }}</p>
      </div>
    </section>

    <section v-if="nominationGroups.length" class="timeline-card">
      <h2>📜 投票记录</h2>
      <div v-for="group in nominationGroups" :key="group.day" class="day-group">
        <h3>第 {{ group.day }} 天</h3>
        <p v-for="(item, index) in group.items" :key="index">
          {{ label(item.nominator) }} 提名 {{ label(item.nominee) }} · {{ item.votes.length }} 票 · {{ nominationState(item) }}
        </p>
      </div>
    </section>
  </section>
</template>

<style scoped>
.public-timeline { display: grid; gap: 12px; }
.timeline-card { padding: 14px; display: grid; gap: 10px; border: 1px solid var(--line); border-radius: 16px; background: var(--panel); }
.timeline-card h2 { font-size: 17px; }
.day-group { display: grid; gap: 5px; }
.day-group + .day-group { padding-top: 8px; border-top: 1px solid var(--line); }
.day-group h3 { color: var(--dim); font-size: 13px; }
.day-group p { font-size: 13px; line-height: 1.45; }
.vote-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.vote-chips span { padding: 4px 7px; border-radius: 999px; background: #57472a; font-size: 12px; }
</style>
