import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import { resolveEntry } from '../src/services/navigation.js'
import { clearPlayerId, getPlayerId } from '../src/services/session.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
vi.mock('../src/services/navigation.js', () => ({
  goToLegacy: vi.fn(),
  resolveEntry: vi.fn(),
}))
vi.mock('../src/services/session.js', () => ({
  clearPlayerId: vi.fn(),
  getPlayerId: vi.fn(),
  getStorytellerPassword: vi.fn().mockReturnValue(null),
  setStorytellerPassword: vi.fn(),
  clearStorytellerPassword: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
  getPlayerId.mockReturnValue('p1')
  resolveEntry.mockResolvedValue({ vuePage: 'player' })
  window.location.hash = ''
})

it('renders the player page for a valid session and clears an invalid live session', async () => {
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
  await wrapper.get('[data-player-invalid]').trigger('click')
  await flushPromises()

  expect(clearPlayerId).toHaveBeenCalledTimes(1)
  expect(wrapper.find('[data-submit]').exists()).toBe(true)
})
