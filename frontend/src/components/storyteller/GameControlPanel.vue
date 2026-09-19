<script setup>
import { computed } from 'vue'
import { getScriptName } from '../../presentation/storyteller.js'

const props = defineProps({ view: { type: Object, required: true } })
const scriptName = computed(() => getScriptName(props.view))
const seatedCount = computed(() => props.view.seats?.filter((seat) => seat.player).length || 0)
</script>

<template>
  <div class="panel-content">
    <div>
      <p class="panel-eyebrow">本局控制</p>
      <h2>{{ scriptName }}</h2>
    </div>
    <dl class="control-summary">
      <div><dt>人数</dt><dd>{{ view.player_count }} 人</dd></div>
      <div><dt>入座</dt><dd>已入座 {{ seatedCount }}/{{ view.player_count }}</dd></div>
      <div><dt>房间</dt><dd>{{ view.room_code }}</dd></div>
    </dl>
    <details class="advanced-summary">
      <summary>高级设置</summary>
      <p>配板、身份分配与高级设置暂时保留在完整控制台。</p>
    </details>
    <a class="btn" href="/legacy/#/storyteller">前往完整控制台</a>
  </div>
</template>
