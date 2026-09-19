import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import { resolveEntry } from '../src/services/navigation.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
vi.mock('../src/services/navigation.js', () => ({
  goToLegacy: vi.fn(),
  resolveEntry: vi.fn(),
}))
vi.mock('../src/services/session.js', () => ({
  clearPlayerId: vi.fn(),
  getPlayerId: vi.fn().mockReturnValue(null),
}))

beforeEach(() => vi.clearAllMocks())

it('renders the Vue storyteller preview destination', async () => {
  resolveEntry.mockResolvedValue({ vuePage: 'storyteller-preview' })
  const wrapper = mount(App)
  await flushPromises()
  expect(wrapper.get('[data-storyteller-preview]').exists()).toBe(true)
})
