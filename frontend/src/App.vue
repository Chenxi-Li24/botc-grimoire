<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import JoinPage from './pages/JoinPage.vue'
import PlayerPage from './pages/PlayerPage.vue'
import StorytellerPage from './pages/StorytellerPage.vue'
import { api } from './services/api.js'
import { resolveEntry } from './services/navigation.js'
import { clearPlayerId, getPlayerId } from './services/session.js'

const page = ref('loading')
const activePlayerId = ref(null)
let routeVersion = 0

function onJoined(playerId) {
  activePlayerId.value = playerId
  page.value = 'player'
}

function onPlayerInvalid() {
  routeVersion += 1
  clearPlayerId()
  activePlayerId.value = null
  page.value = 'join'
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

  if (destination?.vuePage) {
    if (destination.vuePage === 'player') activePlayerId.value = playerId
    page.value = destination.vuePage
    return
  }

  if (destination?.redirectHash) {
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${destination.redirectHash}`)
    page.value = destination.vuePageAfterRedirect
    return
  }

  if (playerId) clearPlayerId()
  activePlayerId.value = null
  page.value = 'join'
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
    <StorytellerPage v-if="page === 'storyteller'" />
    <PlayerPage
      v-else-if="page === 'player' && activePlayerId"
      :player-id="activePlayerId"
      @invalid="onPlayerInvalid"
    />
    <JoinPage v-else-if="page === 'join'" @joined="onJoined" />
    <main v-else class="page center">
      <p>加载中…</p>
    </main>
  </div>
</template>
