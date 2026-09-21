import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import { goToLegacy, resolveEntry } from '../src/services/navigation.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
vi.mock('../src/services/navigation.js', () => ({
  goToLegacy: vi.fn(),
  resolveEntry: vi.fn().mockResolvedValue('join'),
}))
vi.mock('../src/services/session.js', () => ({
  clearPlayerId: vi.fn(),
  getPlayerId: vi.fn().mockReturnValue(null),
  getStorytellerPassword: vi.fn().mockReturnValue(null),
  setStorytellerPassword: vi.fn(),
  clearStorytellerPassword: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
  resolveEntry.mockResolvedValue('join')
  window.location.hash = ''
})

describe('App hash routing', () => {
  it('rechecks the entry route when the hash changes', async () => {
    const wrapper = mount(App)
    await flushPromises()
    resolveEntry.mockClear()

    window.location.hash = '#/storyteller'
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    await flushPromises()

    expect(resolveEntry).toHaveBeenCalledWith(expect.objectContaining({
      hash: '#/storyteller',
    }))
    wrapper.unmount()
  })

  it('ignores an older route result that resolves after a hash change', async () => {
    let resolveFirstRoute
    let calls = 0
    resolveEntry.mockImplementation(() => {
      calls += 1
      return calls === 1
        ? new Promise((resolve) => { resolveFirstRoute = resolve })
        : Promise.resolve({ vuePage: 'storyteller' })
    })

    const wrapper = mount(App)
    await vi.waitFor(() => expect(resolveEntry).toHaveBeenCalledTimes(1))

    window.location.hash = '#/storyteller'
    window.dispatchEvent(new HashChangeEvent('hashchange'))
    await vi.waitFor(() => expect(wrapper.find('[data-storyteller-page]').exists()).toBe(true))

    resolveFirstRoute({ vuePage: 'player' })
    await flushPromises()

    expect(wrapper.find('[data-storyteller-page]').exists()).toBe(true)
    expect(goToLegacy).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('does not redirect an obsolete legacy destination', async () => {
    resolveEntry.mockResolvedValue({ legacyUrl: '/legacy/' })
    const wrapper = mount(App)
    await flushPromises()
    expect(goToLegacy).not.toHaveBeenCalled()
    expect(wrapper.find('[data-submit]').exists()).toBe(true)
    wrapper.unmount()
  })
})
