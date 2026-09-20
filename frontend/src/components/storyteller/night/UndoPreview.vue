<script setup>
defineProps({
  previews: { type: Array, default: () => [] },
  selected: { type: Object, default: null },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
defineEmits(['preview', 'confirm', 'close'])
</script>

<template>
  <section class="night-card undo-preview">
    <div class="night-card-heading"><h4>撤销操作</h4><span>不会随“上一步”自动撤销</span></div>
    <template v-if="selected">
      <p>本次撤销会回滚 {{ selected.event_ids?.length || 0 }} 条关联记录：</p>
      <ul class="undo-event-list">
        <li v-for="event in selected.events || []" :key="event.id || event.event_id">{{ event.kind || '事件' }} · {{ event.id || event.event_id }}</li>
      </ul>
      <p v-if="selected.retractions?.length" class="inline-warning">还会撤回 {{ selected.retractions.length }} 条已经发送的信息。</p>
      <div class="split-actions">
        <button class="btn ghost" type="button" @click="$emit('close')">取消</button>
        <button
          class="btn danger"
          type="button"
          :disabled="!connected || pending.includes(`night:undo:${selected.root_event_id}`)"
          @click="$emit('confirm', selected.root_event_id)"
        >确认完整撤销</button>
      </div>
    </template>
    <template v-else>
      <button
        v-for="preview in previews.slice(0, 8)"
        :key="preview.event_id"
        type="button"
        class="undo-row"
        @click="$emit('preview', preview.event_id)"
      >
        <span>{{ preview.kind }}</span><small>{{ preview.created_at }}</small><strong>查看影响</strong>
      </button>
      <p v-if="!previews.length" class="inline-note">当前没有可以撤销的夜晚操作。</p>
    </template>
  </section>
</template>
