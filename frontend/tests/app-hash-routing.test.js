import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import { resolveEntry } from '../src/services/navigation.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
vi.mock('../src/services/navigation.js', () => ({
  goToLegacy: vi.fn(),
  resolveEntry: vi.fn().mockResolvedValue('join'),
}))
vi.mock('../src/services/session.js', () => ({
  clearPlayerId: vi.fn(),
  getPlayerId: vi.fn().mockReturnValue(null),
}))

beforeEach(() => {
  vi.clearAllMocks()
  resolveEntry.mockResolvedValue('join')
  window.location.hash = ''
})

describe('App hash routing', () => {
  it('rechecks the entry route when the hash changes', async () => {
    mount(App)
    await flushPromises()
    resolveEntry.mockClear()

    window.location.hash = '#/storyteller'
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    await flushPromises()

    expect(resolveEntry).toHaveBeenCalledWith(expect.objectContaining({
      hash: '#/storyteller',
    }))
  })
})
