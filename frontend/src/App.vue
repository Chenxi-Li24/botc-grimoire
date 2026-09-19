<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import JoinPage from './pages/JoinPage.vue'
import { api } from './services/api.js'
import { goToLegacy, resolveEntry } from './services/navigation.js'
import { clearPlayerId, getPlayerId } from './services/session.js'

const ready = ref(false)
let routeVersion = 0

function onJoined() {
  goToLegacy('/legacy/')
}

async function routeCurrentEntry() {
  const version = ++routeVersion
  const playerId = getPlayerId()
  const destination = await resolveEntry({
    hash: window.location.hash,
    playerId,
    validatePlayer: (id) => api(`/api/me/${encodeURIComponent(id)}`),
  })

  if (version !== routeVersion) return

  if (destination !== 'join') {
    goToLegacy(destination.legacyUrl)
    return
  }

  if (playerId) clearPlayerId()
  ready.value = true
}

function onHashChange() {
  void routeCurrentEntry()
}

onMounted(() => {
  window.addEventListener('hashchange', onHashChange)
  void routeCurrentEntry()
})

onBeforeUnmount(() => {
  routeVersion += 1
  window.removeEventListener('hashchange', onHashChange)
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
