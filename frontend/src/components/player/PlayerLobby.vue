<script setup>
import { ref } from 'vue'

const props = defineProps({
  view: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
})
const emit = defineEmits(['sit', 'wish', 'traveler'])
const customWish = ref('')

const blocked = (key) => !props.connected || props.pending.includes(key)

function saveCustomWish() {
  const wish = customWish.value.trim()
  if (!wish || blocked('wish')) return
  emit('wish', wish)
  customWish.value = ''
}
</script>

<template>
  <section class="lobby-card">
    <div>
      <p class="eyebrow">{{ view.status === 'playing' ? '迟到加入' : '等待开局' }}</p>
      <h1>{{ view.me?.seat == null ? '选择座位' : `已入座 ${view.me.seat} 号` }}</h1>
      <p class="sub">{{ view.status === 'playing' ? '选择空座继承该座身份，或以旅行者加入。' : '身份会在说书人开始游戏后揭晓。' }}</p>
    </div>

    <div class="seat-grid" aria-label="座位选择">
      <button
        v-for="slot in view.seats || []"
        :key="slot.seat"
        class="seat-choice"
        :class="{ occupied: !!slot.player, mine: slot.is_me }"
        :data-seat="slot.seat"
        :disabled="!!slot.player || blocked('sit')"
        type="button"
        @click="emit('sit', slot.seat)"
      >
        <strong>{{ slot.seat }}号</strong>
        <span>{{ slot.player?.name || '空座' }}</span>
      </button>
    </div>

    <button
      v-if="view.status === 'playing' && view.me?.seat == null"
      data-traveler
      class="btn primary"
      :disabled="blocked('traveler')"
      type="button"
      @click="emit('traveler')"
    >
      🎒 以旅行者身份加入
    </button>

    <section v-if="view.status === 'lobby'" class="wish-card">
      <h2>🙏 开局前许愿</h2>
      <p class="hint">仅你和说书人可见，用于配板参考。</p>
      <div class="wish-presets">
        <button
          v-for="wish in ['善良', '邪恶']"
          :key="wish"
          :data-wish="wish"
          class="btn"
          :class="{ selected: view.me_wish === wish }"
          :disabled="blocked('wish')"
          type="button"
          @click="emit('wish', view.me_wish === wish ? null : wish)"
        >
          {{ wish === '善良' ? '😇 善良阵营' : '😈 邪恶阵营' }}
        </button>
      </div>
      <div class="custom-wish">
        <input v-model="customWish" data-custom-wish class="input" maxlength="30" placeholder="例如：想玩信息角色">
        <button data-save-wish class="btn" :disabled="blocked('wish') || !customWish.trim()" type="button" @click="saveCustomWish">保存</button>
      </div>
      <p v-if="view.me_wish" class="hint">当前愿望：{{ view.me_wish }}</p>
      <button v-if="view.me_wish" data-clear-wish class="btn" :disabled="blocked('wish')" type="button" @click="emit('wish', null)">清除愿望</button>
    </section>
  </section>
</template>

<style scoped>
.lobby-card, .wish-card { display: grid; gap: 14px; }
.lobby-card { padding: 18px; border: 1px solid var(--line); border-radius: 18px; background: var(--panel); }
.eyebrow { color: var(--dim); font-size: 12px; letter-spacing: .08em; }
.seat-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.seat-choice { min-height: 66px; padding: 8px; display: grid; gap: 4px; border: 1px dashed var(--line); border-radius: 12px; background: color-mix(in srgb, var(--panel) 80%, black); color: var(--text); }
.seat-choice span { overflow: hidden; color: var(--dim); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.seat-choice.occupied { border-style: solid; opacity: .62; }
.seat-choice.mine { border-color: var(--accent); }
.wish-card { padding-top: 14px; border-top: 1px solid var(--line); }
.wish-card h2 { font-size: 17px; }
.wish-presets, .custom-wish { display: flex; gap: 8px; }
.wish-presets .btn { flex: 1; }
.wish-presets .selected { border-color: var(--accent); }
.custom-wish .input { min-width: 0; flex: 1; }
@media (max-width: 380px) { .seat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
