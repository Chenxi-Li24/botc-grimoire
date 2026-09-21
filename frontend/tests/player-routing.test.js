import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import { resolveEntry } from '../src/services/navigation.js'
import { api } from '../src/services/api.js'
import { clearCsrfToken } from '../src/services/session.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
vi.mock('../src/services/navigation.js', () => ({
  goToLegacy: vi.fn(),
  resolveEntry: vi.fn(),
}))
vi.mock('../src/services/session.js', () => ({
  clearCsrfToken: vi.fn(),
  setCsrfToken: vi.fn(),
  getCsrfToken: vi.fn(),
  getStorytellerPassword: vi.fn().mockReturnValue(null),
  setStorytellerPassword: vi.fn(),
  clearStorytellerPassword: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
  resolveEntry.mockImplementation(({ session }) => ({ vuePage: session?.player_id ? 'player' : 'join' }))
  api.mockResolvedValueOnce({ account: null, player_id: 'p1', csrf_token: 'csrf' })
  window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
})

it('renders the player page for a valid session and rechecks after invalidation', async () => {
  const wrapper = mount(App, {
    global: {
      stubs: {
        PlayerPage: {
          emits: ['invalid'],
          template: '<button data-player-invalid @click="$emit(\'invalid\')">invalid</button>',
        },
      },
    },
  })
  await flushPromises()

  expect(wrapper.find('[data-player-invalid]').exists()).toBe(true)
  const unauthorized = new Error('expired')
  unauthorized.status = 401
  api.mockRejectedValueOnce(unauthorized)
  await wrapper.get('[data-player-invalid]').trigger('click')
  await flushPromises()

  expect(clearCsrfToken).toHaveBeenCalledTimes(1)
  expect(wrapper.find('[data-submit]').exists()).toBe(true)
  wrapper.unmount()
})
