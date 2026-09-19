import { onBeforeUnmount, ref, shallowRef } from 'vue'
import { clearStorytellerPassword } from '../services/session.js'
import { openSocket } from '../services/websocket.js'

export function useStorytellerView(password, { onAuthFailure = () => {} } = {}) {
  const view = shallowRef(null)
  const connectionStatus = ref('connecting')

  const connection = openSocket({
    query: `who=storyteller&pw=${encodeURIComponent(password)}`,
    onMessage: (nextView) => { view.value = nextView },
    onStatus: (nextStatus) => { connectionStatus.value = nextStatus },
    onFatal: () => {
      clearStorytellerPassword()
      onAuthFailure()
    },
  })

  onBeforeUnmount(() => connection.close())

  return { view, connectionStatus }
}
