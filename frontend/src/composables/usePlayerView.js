import { onBeforeUnmount, ref, shallowRef } from 'vue'
import { openSocket } from '../services/websocket.js'

export function usePlayerView(playerId, { onInvalid = () => {} } = {}) {
  const view = shallowRef(null)
  const connectionStatus = ref('connecting')
  const connection = openSocket({
    query: `who=${encodeURIComponent(playerId)}`,
    onMessage: (nextView) => {
      view.value = nextView
    },
    onStatus: (status) => {
      connectionStatus.value = status
    },
    onFatal: onInvalid,
  })

  onBeforeUnmount(() => connection.close())

  return { view, connectionStatus }
}
