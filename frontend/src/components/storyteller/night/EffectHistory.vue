<script setup>
import { effectStateLabel, effectTransitionLabel } from '../../../presentation/nightWorkflow.js'

defineProps({
  effects: { type: Array, default: () => [] },
  seat: { type: Number, default: null },
})
</script>

<template>
  <section class="night-card effect-history">
    <div class="night-card-heading"><h4>异常状态溯源</h4><span>{{ effects.length }} 条</span></div>
    <article v-for="effect in effects" :key="effect.id" class="effect-record" :class="`state-${effect.state}`">
      <div><strong>{{ effect.type }}</strong><span>{{ effectStateLabel(effect.state) }}</span></div>
      <p>目标 {{ effect.target_seat }}号 · 来源 {{ effect.source_seat ? `${effect.source_seat}号` : '系统' }} {{ effect.source_character || '' }}</p>
      <p>获得时间：{{ effect.started_at || '未知' }}<template v-if="effect.expected_end"> · 预计结束：{{ effect.expected_end }}</template></p>
      <ol v-if="effect.transitions?.length">
        <li v-for="(transition, index) in effect.transitions" :key="index">{{ effectTransitionLabel(transition) }} · {{ transition.at || '' }}</li>
      </ol>
    </article>
    <p v-if="!effects.length" class="inline-note">{{ seat ? `${seat}号当前没有状态记录。` : '当前没有状态记录。' }}</p>
  </section>
</template>
