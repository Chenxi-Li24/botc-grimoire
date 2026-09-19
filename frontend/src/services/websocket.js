export function openSocket({
  query,
  onMessage,
  onStatus = () => {},
  onFatal = () => {},
  WebSocketImpl = WebSocket,
  schedule = setTimeout,
  cancel = clearTimeout,
}) {
  let socket = null
  let retryTimer = null
  let stopped = false
  let attempts = 0

  const connect = () => {
    if (stopped) return
    onStatus(attempts ? 'reconnecting' : 'connecting')
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    socket = new WebSocketImpl(`${protocol}://${location.host}/ws?${query}`)
    socket.onopen = () => {
      attempts = 0
      onStatus('connected')
    }
    socket.onmessage = (event) => onMessage(JSON.parse(event.data))
    socket.onclose = (event) => {
      if (stopped) return
      if (event.code === 4001 || event.code === 4003) {
        stopped = true
        onFatal(event.code)
        return
      }
      attempts += 1
      onStatus('reconnecting')
      retryTimer = schedule(connect, Math.min(500 * (2 ** (attempts - 1)), 5000))
    }
  }

  connect()
  return {
    close() {
      stopped = true
      if (retryTimer !== null) cancel(retryTimer)
      if (socket && socket.readyState < 2) socket.close()
    },
  }
}
