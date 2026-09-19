<script setup>
import { onMounted, ref } from 'vue'
import JoinPage from './pages/JoinPage.vue'
import { api } from './services/api.js'
import { goToLegacy, resolveEntry } from './services/navigation.js'
import { clearPlayerId, getPlayerId } from './services/session.js'

const ready = ref(false)

function onJoined() {
  goToLegacy('/legacy/')
}

onMounted(async () => {
  const playerId = getPlayerId()
  const destination = await resolveEntry({
    hash: window.location.hash,
    playerId,
    validatePlayer: (id) => api(`/api/me/${encodeURIComponent(id)}`),
  })

  if (destination !== 'join') {
    goToLegacy(destination.legacyUrl)
    return
  }

  if (playerId) clearPlayerId()
  ready.value = true
})
</script>

<template>
  <div data-app-shell>
    <JoinPage v-if="ready" @joined="onJoined" />
    <main v-else class="page center">
      <p>加载中…</p>
    </main>
  </div>
</template>
