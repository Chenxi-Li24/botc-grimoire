<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import JoinPage from './pages/JoinPage.vue'
import AccountPage from './pages/AccountPage.vue'
import PlayerPage from './pages/PlayerPage.vue'
import StorytellerPage from './pages/StorytellerPage.vue'
import { api } from './services/api.js'
import { resolveEntry } from './services/navigation.js'
import { clearCsrfToken, setCsrfToken } from './services/session.js'

const page = ref('loading')
const activePlayerId = ref(null)
let routeVersion = 0

function onJoined(playerId) {
  void routeCurrentEntry()
}

function onPlayerInvalid() {
  void routeCurrentEntry()
}

async function routeCurrentEntry() {
  const version = ++routeVersion
  const hash = window.location.hash
  page.value = 'loading'
  let destination = await resolveEntry({ hash, session: null })
  if (version !== routeVersion) return

  if (destination?.redirectHash) {
    window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}${destination.redirectHash}`)
    page.value = destination.vuePageAfterRedirect
    return
  }
  if (destination?.vuePage === 'storyteller') {
    page.value = 'storyteller'
    return
  }

  let session
  try {
    session = await api('/api/session')
  } catch (error) {
    if (version !== routeVersion) return
    if (error?.status === 401) {
      clearCsrfToken()
      activePlayerId.value = null
      page.value = destination?.vuePage === 'account' ? 'account' : 'join'
    } else {
      page.value = 'offline'
    }
    return
  }

  if (version !== routeVersion) return
  setCsrfToken(session.csrf_token)
  activePlayerId.value = session.player_id || null
  destination = await resolveEntry({ hash, session })
  if (version !== routeVersion) return

  if (destination?.vuePage) {
    page.value = destination.vuePage
    return
  }
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
    <JoinPage v-else-if="page === 'join'" @joined="onJoined" @account="page = 'account'" />
    <AccountPage v-else-if="page === 'account'" @authenticated="routeCurrentEntry" @back="page = activePlayerId ? 'player' : 'join'" />
    <main v-else-if="page === 'offline'" class="page center">
      <p>连接暂时不可用，身份仍保留在此设备。恢复网络后重试。</p>
      <button data-retry-session class="btn primary" type="button" @click="routeCurrentEntry">重试连接</button>
    </main>
    <main v-else class="page center">
      <p>加载中…</p>
    </main>
  </div>
</template>
