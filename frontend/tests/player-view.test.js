import { defineComponent, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import { openSocket } from '../src/services/websocket.js'

vi.mock('../src/services/websocket.js', () => ({ openSocket: vi.fn() }))

let socketOptions
const close = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
  socketOptions = null
  openSocket.mockImplementation((options) => {
    socketOptions = options
    return { close }
  })
})

it('projects player messages, connection state, fatal invalidation and cleanup', async () => {
  const { usePlayerView } = await import('../src/composables/usePlayerView.js')
  const onInvalid = vi.fn()
  const Harness = defineComponent({
    setup() {
      return usePlayerView('p/1', { onInvalid })
    },
    template: '<p>{{ connectionStatus }}|{{ view?.room_code || "none" }}</p>',
  })
  const wrapper = mount(Harness)

  expect(socketOptions.query).toBe('who=p%2F1')
  socketOptions.onStatus('connected')
  socketOptions.onMessage({ room_code: '2468' })
  await nextTick()
  expect(wrapper.text()).toBe('connected|2468')

  socketOptions.onFatal(4001)
  expect(onInvalid).toHaveBeenCalledWith(4001)
  wrapper.unmount()
  expect(close).toHaveBeenCalledTimes(1)
})
