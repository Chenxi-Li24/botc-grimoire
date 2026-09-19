import { beforeEach, expect, it, vi } from 'vitest'
import { openSocket } from '../src/services/websocket.js'

class FakeSocket {
  static instances = []
  static reset() { FakeSocket.instances = [] }

  constructor(url) {
    this.url = url
    this.readyState = 0
    FakeSocket.instances.push(this)
  }

  emitOpen() {
    this.readyState = 1
    this.onopen?.()
  }

  emitMessage(value) {
    this.onmessage?.({ data: JSON.stringify(value) })
  }

  emitClose(code) {
    this.readyState = 3
    this.onclose?.({ code })
  }

  close() {
    this.readyState = 3
  }
}

beforeEach(() => FakeSocket.reset())

it('parses messages and reports a connected socket', () => {
  const onMessage = vi.fn()
  const onStatus = vi.fn()
  openSocket({ query: 'who=storyteller&pw=secret', onMessage, onStatus, WebSocketImpl: FakeSocket })
  const socket = FakeSocket.instances[0]
  expect(socket.url).toContain('/ws?who=storyteller&pw=secret')
  socket.emitOpen()
  socket.emitMessage({ room_code: '2468' })
  expect(onStatus).toHaveBeenLastCalledWith('connected')
  expect(onMessage).toHaveBeenCalledWith({ room_code: '2468' })
})

it('keeps ownership alive and schedules one reconnect after a transient close', () => {
  let retry
  const schedule = vi.fn((fn) => { retry = fn; return 7 })
  const onFatal = vi.fn()
  openSocket({ query: 'who=storyteller', onMessage: vi.fn(), onStatus: vi.fn(), onFatal,
    WebSocketImpl: FakeSocket, schedule })
  FakeSocket.instances[0].emitClose(1006)
  expect(schedule).toHaveBeenCalledTimes(1)
  expect(onFatal).not.toHaveBeenCalled()
  retry()
  expect(FakeSocket.instances).toHaveLength(2)
})

it('treats authentication close as fatal without reconnecting', () => {
  const schedule = vi.fn()
  const onFatal = vi.fn()
  openSocket({ query: 'who=storyteller', onMessage: vi.fn(), onStatus: vi.fn(), onFatal,
    WebSocketImpl: FakeSocket, schedule })
  FakeSocket.instances[0].emitClose(4003)
  expect(onFatal).toHaveBeenCalledWith(4003)
  expect(schedule).not.toHaveBeenCalled()
})
