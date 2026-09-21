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
  clearCsrfToken: vi.fn(),
  setCsrfToken: vi.fn(),
  getCsrfToken: vi.fn(),
  getStorytellerPassword: vi.fn().mockReturnValue(null),
  setStorytellerPassword: vi.fn(),
  clearStorytellerPassword: vi.fn(),
}))

beforeEach(() => vi.clearAllMocks())

it('renders the canonical Vue storyteller destination', async () => {
  resolveEntry.mockResolvedValue({ vuePage: 'storyteller' })
  const wrapper = mount(App)
  await flushPromises()
  expect(wrapper.get('[data-storyteller-page]').exists()).toBe(true)
})
