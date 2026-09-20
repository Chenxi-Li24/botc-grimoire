<script setup>
const props = defineProps({
  drafts: { type: Array, default: () => [] },
  results: { type: Object, default: () => ({}) },
  claims: { type: Object, default: () => ({}) },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
const emit = defineEmits(['set-result', 'set-claims', 'deliver'])

function stringify(value) {
  if (typeof value === 'string') return value
  return value == null ? '' : JSON.stringify(value, null, 2)
}
function parse(value) {
  if (typeof value !== 'string') return value
  const trimmed = value.trim()
  if (!trimmed) return ''
  try { return JSON.parse(trimmed) } catch { return value }
}
function rows(draft) {
  return props.claims[draft.id] || []
}
function setRows(draft, next) {
  emit('set-claims', { id: draft.id, claims: next })
}
function addClaim(draft) {
  setRows(draft, [...rows(draft), { label: '信息项', value: '', truthful: true }])
}
function updateClaim(draft, index, field, value) {
  setRows(draft, rows(draft).map((claim, offset) => (
    offset === index ? { ...claim, [field]: field === 'value' ? parse(value) : value } : claim
  )))
}
function deliver(draft) {
  emit('deliver', {
    action: 'deliver',
    draft_id: draft.id,
    delivered_result: parse(props.results[draft.id] ?? stringify(draft.true_result)),
    claims: rows(draft),
    reason: draft.reason || '',
  })
}
</script>

<template>
  <section v-if="drafts.length" class="night-stack">
    <article v-for="draft in drafts" :key="draft.id" class="night-card information-editor">
      <div class="night-card-heading"><h4>编辑并发送信息</h4><span>{{ draft.actor_seat }}号</span></div>
      <p v-if="draft.effect_snapshot?.length" class="state-alert">异常状态：{{ draft.reason || '存在认知影响' }}</p>
      <details class="information-reference">
        <summary>查看系统计算结果</summary>
        <p><strong>真实结果</strong></p>
        <pre>{{ stringify(draft.true_result) }}</pre>
        <p><strong>可发送结果</strong></p>
        <pre>{{ stringify(draft.legal_results) }}</pre>
      </details>
      <label class="field-row">实际发送内容
        <textarea
          rows="4"
          :value="results[draft.id] ?? stringify(draft.true_result)"
          @input="$emit('set-result', { id: draft.id, result: $event.target.value })"
        />
      </label>
      <div class="claim-editor">
        <div class="night-card-heading"><h5>真假标记（复盘溯源）</h5><button class="chip-button" type="button" @click="addClaim(draft)">＋ 信息项</button></div>
        <div v-for="(claim, index) in rows(draft)" :key="index" class="claim-row">
          <input :value="claim.label" placeholder="名称" @input="updateClaim(draft, index, 'label', $event.target.value)">
          <input :value="stringify(claim.value)" placeholder="内容" @input="updateClaim(draft, index, 'value', $event.target.value)">
          <select :value="String(claim.truthful)" @change="updateClaim(draft, index, 'truthful', $event.target.value === 'true')">
            <option value="true">正确</option><option value="false">错误</option>
          </select>
          <button class="icon-button" type="button" aria-label="删除" @click="setRows(draft, rows(draft).filter((_, offset) => offset !== index))">×</button>
        </div>
        <p v-if="draft.reason && !rows(draft).length" class="inline-warning">受中毒、醉酒或规则影响的信息必须至少标记一条真假记录。</p>
      </div>
      <button
        class="btn primary"
        type="button"
        :disabled="!connected || pending.includes(`night:information:${draft.id}`) || (draft.reason && !rows(draft).length)"
        @click="deliver(draft)"
      >发送并记录</button>
    </article>
  </section>
</template>
