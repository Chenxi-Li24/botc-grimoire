<script setup>
import { phaseLabel } from '../../presentation/player.js'

defineProps({
  view: { type: Object, required: true },
  connectionStatus: { type: String, required: true },
})
</script>

<template>
  <div class="player-shell">
    <header class="player-header">
      <slot name="header">
        <div>
          <strong>{{ view.me?.name || '玩家' }}</strong>
          <span class="player-meta">{{ phaseLabel(view) }} · 房间 {{ view.room_code }}</span>
        </div>
        <span class="connection" :data-status="connectionStatus">
          {{ connectionStatus === 'connected' ? '已连接' : '连接中' }}
        </span>
      </slot>
    </header>
    <main class="player-content"><slot /></main>
    <footer v-if="$slots.actions" class="player-actions"><slot name="actions" /></footer>
  </div>
</template>

<style scoped>
.player-shell { min-height: 100dvh; padding-bottom: 84px; }
.player-header { position: sticky; top: 0; z-index: 10; min-height: 62px; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); background: color-mix(in srgb, var(--panel) 94%, black); }
.player-header div { min-width: 0; display: grid; gap: 2px; }
.player-meta { color: var(--dim); font-size: 12px; }
.connection { padding: 4px 8px; border: 1px solid var(--line); border-radius: 999px; color: #ffd479; font-size: 12px; }
.connection[data-status='connected'] { color: #8bd6a1; }
.player-content { width: min(680px, 100%); margin: 0 auto; padding: 16px; display: grid; gap: 16px; }
.player-actions { position: fixed; z-index: 12; right: 0; bottom: 0; left: 0; min-height: 68px; padding: 10px 16px max(10px, env(safe-area-inset-bottom)); display: flex; justify-content: center; gap: 10px; border-top: 1px solid var(--line); background: color-mix(in srgb, var(--panel) 96%, black); }
</style>
