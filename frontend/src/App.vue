<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import JoinPage from './pages/JoinPage.vue'
import StorytellerPreviewPage from './pages/StorytellerPreviewPage.vue'
import { api } from './services/api.js'
import { goToLegacy, resolveEntry } from './services/navigation.js'
import { clearPlayerId, getPlayerId } from './services/session.js'

const page = ref('loading')
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

  if (destination?.vuePage) {
    page.value = destination.vuePage
    return
  }

  if (destination !== 'join') {
    goToLegacy(destination.legacyUrl)
    return
  }

  if (playerId) clearPlayerId()
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
    <StorytellerPreviewPage v-if="page === 'storyteller-preview'" />
    <JoinPage v-else-if="page === 'join'" @joined="onJoined" />
    <main v-else class="page center">
      <p>加载中…</p>
    </main>
  </div>
</template>
