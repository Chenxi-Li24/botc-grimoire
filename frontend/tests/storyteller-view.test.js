import { mount } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import { beforeEach, expect, it, vi } from 'vitest'
import { useStorytellerView } from '../src/composables/useStorytellerView.js'
import { clearStorytellerPassword } from '../src/services/session.js'

let socketOptions
const close = vi.fn()

vi.mock('../src/services/websocket.js', () => ({
  openSocket: vi.fn((options) => {
    socketOptions = options
    return { close }
  }),
}))
vi.mock('../src/services/session.js', () => ({ clearStorytellerPassword: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  socketOptions = null
})

function mountView(onAuthFailure = vi.fn()) {
  const Harness = defineComponent({
    setup() {
      return useStorytellerView('secret', { onAuthFailure })
    },
    template: '<div>{{ connectionStatus }}:{{ view?.room_code }}</div>',
  })
  return { wrapper: mount(Harness), onAuthFailure }
}

it('keeps the latest view visible while reconnecting', async () => {
  const { wrapper } = mountView()
  socketOptions.onMessage({ room_code: '2468' })
  socketOptions.onStatus('reconnecting')
  await nextTick()

  expect(wrapper.text()).toBe('reconnecting:2468')
})

it('clears only the storyteller credential after authentication failure', async () => {
  localStorage.setItem('botc_player_id', 'player-token')
  const { onAuthFailure } = mountView()
  socketOptions.onFatal(4003)
  await nextTick()

  expect(clearStorytellerPassword).toHaveBeenCalledOnce()
  expect(onAuthFailure).toHaveBeenCalledOnce()
  expect(localStorage.getItem('botc_player_id')).toBe('player-token')
})
