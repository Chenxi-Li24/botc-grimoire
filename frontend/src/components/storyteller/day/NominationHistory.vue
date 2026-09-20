<script setup>
import { computed } from 'vue'
import { groupDeaths, groupNominations, participantLabel } from '../../../presentation/player.js'

const props = defineProps({ view: { type: Object, required: true } })
const nominationGroups = computed(() => groupNominations(props.view.nominations))
const deathGroups = computed(() => groupDeaths(props.view.deaths))

function label(id) {
  return participantLabel(id, props.view.seats, props.view.travelers)
}

function resultLabel(nomination) {
  if (!nomination.passed) return '未通过'
  if (typeof nomination.nominee === 'string' && nomination.executed) return '已流放'
  if (nomination.executed) return '已处决'
  return '进入处决台'
}
</script>

<template>
  <section class="day-card nomination-history" data-nomination-history>
    <div class="day-card-heading">
      <div>
        <p class="panel-eyebrow">公开记录</p>
        <h3>提名与死亡历史</h3>
      </div>
    </div>
    <p v-if="!nominationGroups.length && !deathGroups.length" class="inline-note">今天还没有历史记录。</p>
    <div v-for="group in nominationGroups" :key="`nom-day-${group.day}`" class="history-day">
      <h4>第 {{ group.day }} 天</h4>
      <p v-for="(nomination, index) in group.items" :key="index">
        {{ label(nomination.nominator) }} → {{ label(nomination.nominee) }} ·
        {{ nomination.votes?.length || 0 }} 票 · {{ resultLabel(nomination) }}
      </p>
    </div>
    <div v-for="group in deathGroups" :key="`death-day-${group.day}`" class="history-day death-history">
      <h4>第 {{ group.day }} 天死亡</h4>
      <p v-for="death in group.items" :key="`${death.seat}-${death.cause || ''}`">
        {{ label(death.seat) }}{{ death.cause ? ` · ${death.cause}` : '' }}
      </p>
    </div>
  </section>
</template>
