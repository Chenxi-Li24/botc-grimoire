<script setup>
import { computed, ref } from 'vue'
import { teamLabel } from '../../presentation/player.js'

const props = defineProps({ view: { type: Object, required: true } })
const tab = ref('result')

const alignment = computed(() => (
  props.view.traveler?.align
  || props.view.team_changed
  || props.view.me?.role?.team
  || null
))
const normalizedTeam = computed(() => (
  ['good', 'townsfolk', 'outsider'].includes(alignment.value) ? 'good'
    : ['evil', 'minion', 'demon'].includes(alignment.value) ? 'evil'
      : null
))
const won = computed(() => (
  normalizedTeam.value ? normalizedTeam.value === props.view.result.winner : null
))
const winnerLabel = computed(() => teamLabel(props.view.result.winner))
function guessLabel(item) {
  if (item.category === 'role') return `角色：${props.view.script_roles?.find((role) => role.id === item.data.role)?.name || item.data.role}`
  if (item.category === 'alignment') return `阵营：${teamLabel(item.data.alignment)}`
  if (item.category === 'status') return `状态：${({ poisoned: '中毒', drunk: '醉酒', mad: '疯狂' })[item.data.status] || item.data.status}`
  return '角色/阵营变化'
}
function verdictLabel(verdict) { return ({ correct: '正确', incorrect: '错误', unverified: '无法核对' })[verdict] || '无法核对' }
</script>

<template>
  <section data-player-result class="player-result">
    <div class="result-tabs" role="tablist" aria-label="结算与复盘">
      <button data-result-tab="result" :class="{ on: tab === 'result' }" type="button" @click="tab = 'result'">🏁 结算</button>
      <button data-result-tab="review" :class="{ on: tab === 'review' }" type="button" @click="tab = 'review'">📜 复盘</button>
    </div>

    <template v-if="tab === 'result'">
      <div class="result-banner" :class="{ win: won === true, lose: won === false }">
        <h1>{{ won === null ? '本局结束' : won ? '🎉 你赢了' : '💀 你输了' }}</h1>
        <p>{{ winnerLabel }}阵营获胜 · 第 {{ view.day_no }} 天 · {{ view.script }}</p>
      </div>

      <section class="reveal-list">
        <h2>全场角色揭晓</h2>
        <p v-for="seat in view.result.seats" :key="seat.seat" :class="{ dead: seat.alive === false }">
          <span v-if="seat.role" class="team-pill" :data-team="seat.role.team">{{ teamLabel(seat.role.team) }}</span>
          {{ seat.seat }}号 {{ seat.name || '空座' }}：{{ seat.role?.name || '—' }}{{ seat.seat === view.me?.seat ? '（你）' : '' }}
        </p>
        <p v-for="traveler in view.result.travelers" :key="traveler.id" :class="{ dead: traveler.alive === false }">
          🎒 {{ traveler.name }}：{{ traveler.role?.name || '—' }}（{{ teamLabel(traveler.align) }}）{{ traveler.id === view.traveler?.id ? '（你）' : '' }}
        </p>
      </section>
      <p class="hint">结果由说书人宣布，如有异议请现场确认。</p>
    </template>

    <section v-else class="review-list">
      <div v-if="view.inference_replay?.length" data-inference-replay class="review-group">
        <h2>我的推测对照</h2>
        <p v-for="item in view.inference_replay" :key="item.seq">{{ item.target }}号 · {{ guessLabel(item) }} · {{ verdictLabel(item.verdict) }}</p>
        <p class="hint">只对可靠的最终角色或阵营作对照；缺少真实历史的状态标为“无法核对”。</p>
      </div>
      <template v-if="view.review?.has_data">
        <div v-for="group in view.review.groups" :key="`${group.phase}:${group.n}`" class="review-group">
          <h2>{{ group.label }}</h2>
          <p v-for="(item, index) in group.items" :key="index" :class="{ wrong: item.wrong }">
            {{ item.wrong ? '⚠ ' : '' }}{{ item.text }}<span v-if="item.why">（{{ item.why }}）</span>
          </p>
        </div>
      </template>
      <p v-else class="hint empty-review">本局没有可用的复盘记录（可能来自旧存档）。</p>
    </section>
  </section>
</template>

<style scoped>
.player-result { display: grid; gap: 14px; }
.result-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.result-tabs button { border: 1px solid var(--line); border-radius: 10px; background: var(--panel); color: var(--text); }
.result-tabs button.on { border-color: #d6ad55; background: #57442a; }
.result-banner, .reveal-list, .review-group, .empty-review { padding: 16px; border: 1px solid var(--line); border-radius: 18px; background: var(--panel); }
.result-banner { display: grid; gap: 6px; text-align: center; }
.result-banner.win { border-color: #3e8a59; background: color-mix(in srgb, var(--panel) 84%, #173c24); }
.result-banner.lose { border-color: #8b3d43; background: color-mix(in srgb, var(--panel) 84%, #411b20); }
.result-banner p, .hint { color: var(--dim); font-size: 12px; }
.reveal-list, .review-list, .review-group { display: grid; gap: 9px; }
.reveal-list h2, .review-group h2 { font-size: 17px; }
.reveal-list p, .review-group p { font-size: 13px; line-height: 1.5; }
.dead { opacity: .55; text-decoration: line-through; }
.team-pill { padding: 2px 5px; border-radius: 999px; background: rgb(255 255 255 / 8%); font-size: 11px; }
.wrong { color: #ffb1b7; }
</style>
