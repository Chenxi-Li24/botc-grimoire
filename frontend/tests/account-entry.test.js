import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../src/App.vue'
import AccountPage from '../src/pages/AccountPage.vue'
import { api } from '../src/services/api.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
})

it('keeps an offline retry state and restores the server session without local player id', async () => {
  api.mockRejectedValue(new TypeError('Failed to fetch'))
  const wrapper = mount(App, {
    global: { stubs: { PlayerPage: { template: '<div data-player-page />' } } },
  })
  await flushPromises()
  expect(wrapper.find('[data-retry-session]').exists()).toBe(true)
  expect(localStorage.getItem('botc_player_id')).toBeNull()
  api.mockResolvedValue({ account: 'Alice', player_id: 'p1', csrf_token: 'csrf' })
  await wrapper.get('[data-retry-session]').trigger('click')
  await flushPromises()
  expect(wrapper.find('[data-player-page]').exists()).toBe(true)
  wrapper.unmount()
})

it('shows join only after an explicit 401 from session validation', async () => {
  const error = new Error('unauthorized')
  error.status = 401
  api.mockRejectedValueOnce(error)
  const wrapper = mount(App)
  await flushPromises()
  expect(wrapper.find('[data-submit]').exists()).toBe(true)
  wrapper.unmount()
})

it('registers an optional account and shows its recovery code once', async () => {
  api.mockResolvedValue({ account_id: 'a1', recovery_code: 'save-this-once' })
  const wrapper = mount(AccountPage)
  await wrapper.get('[data-mode-register]').trigger('click')
  await wrapper.get('[data-username]').setValue('Alice')
  await wrapper.get('[data-password]').setValue('test-password-123')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(api).toHaveBeenCalledWith('/api/account/register', {
    method: 'POST', body: JSON.stringify({ username: 'Alice', password: 'test-password-123' }),
  })
  expect(wrapper.get('[data-account-recovery-code]').text()).toBe('save-this-once')
  await wrapper.get('[data-account-done]').trigger('click')
  expect(wrapper.find('[data-account-recovery-code]').exists()).toBe(false)
  expect(wrapper.emitted('authenticated')).toEqual([[]])
})
