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

it('resets a password using an account recovery code and rotates that code', async () => {
  api.mockResolvedValue({ ok: true, recovery_code: 'fresh-code' })
  const wrapper = mount(AccountPage)
  await wrapper.get('[data-mode-reset]').trigger('click')
  await wrapper.get('[data-username]').setValue('Alice')
  await wrapper.get('[data-account-recovery-input]').setValue('old-code')
  await wrapper.get('[data-password]').setValue('new-password-123')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(api).toHaveBeenCalledWith('/api/account/reset-password', {
    method: 'POST', body: JSON.stringify({
      username: 'Alice', recovery_code: 'old-code', new_password: 'new-password-123',
    }),
  })
  expect(wrapper.get('[data-account-recovery-code]').text()).toBe('fresh-code')
})

it('lets authenticated users change password and log out', async () => {
  api.mockResolvedValue({ ok: true })
  const wrapper = mount(AccountPage, { props: { account: 'Alice' } })
  expect(wrapper.text()).toContain('Alice')
  await wrapper.get('[data-old-password]').setValue('old-password-123')
  await wrapper.get('[data-new-password]').setValue('new-password-123')
  await wrapper.get('[data-change-password]').trigger('click')
  await flushPromises()
  expect(api).toHaveBeenCalledWith('/api/account/change-password', {
    method: 'POST', body: JSON.stringify({ old_password: 'old-password-123', new_password: 'new-password-123' }),
  })
  await wrapper.get('[data-account-logout]').trigger('click')
  await flushPromises()
  expect(api).toHaveBeenCalledWith('/api/account/logout', { method: 'POST' })
  expect(wrapper.emitted('authenticated')).toEqual([[]])
})

it('lets logged-in users inspect history before joining another game', async () => {
  api.mockResolvedValue({ account: 'Alice', player_id: null, csrf_token: 'csrf' })
  const wrapper = mount(App, {
    global: { stubs: { AccountHistoryPage: { template: '<div data-history-page />' } } },
  })
  await flushPromises()
  await wrapper.get('[data-join-history]').trigger('click')
  expect(wrapper.find('[data-history-page]').exists()).toBe(true)
  wrapper.unmount()
})

it('requires an explicit UID login mode and sends the password with it', async () => {
  api.mockResolvedValue({ ok: true })
  const wrapper = mount(AccountPage)
  await wrapper.get('[data-login-uid]').trigger('click')
  await wrapper.get('[data-username]').setValue('1234')
  await wrapper.get('[data-password]').setValue('four')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(api).toHaveBeenCalledWith('/api/account/login', {
    method: 'POST', body: JSON.stringify({ username: '1234', password: 'four', mode: 'uid' }),
  })
})

it('shows the account profile and changes an eight-grapheme nickname', async () => {
  api.mockImplementation((path) => path === '/api/account/profile'
    ? Promise.resolve({ uid: '1234', username: 'Alice', nickname: '旧名', has_avatar: false })
    : Promise.resolve({ nickname: '👩‍👩‍👧‍👦Ab中文123' }))
  const wrapper = mount(AccountPage, { props: { account: 'Alice' } })
  await flushPromises()
  expect(wrapper.get('[data-account-uid]').text()).toContain('1234')
  expect(wrapper.get('[data-account-username]').text()).toContain('Alice')
  await wrapper.get('[data-nickname]').setValue('👩‍👩‍👧‍👦Ab中文123')
  expect(wrapper.get('[data-nickname-remaining]').text()).toContain('0')
  await wrapper.get('[data-change-nickname]').trigger('click')
  await flushPromises()
  expect(api).toHaveBeenCalledWith('/api/account/nickname', {
    method: 'POST', body: JSON.stringify({ nickname: '👩‍👩‍👧‍👦Ab中文123' }),
  })
})

it('labels HTTPS visits correctly instead of calling them HTTP tests', () => {
  const oldDescriptor = Object.getOwnPropertyDescriptor(window, 'location')
  // A queryable copy lets the component use the same protocol logic as a browser visit.
  const wrapper = mount(AccountPage, { props: { account: null, protocol: 'https:' } })
  expect(wrapper.text()).not.toContain('当前为 HTTP 小规模测试')
  expect(wrapper.text()).toContain('HTTPS')
  wrapper.unmount()
  expect(oldDescriptor).toBeDefined()
})

it('validates password length in Unicode code points, not UTF-16 units', async () => {
  const wrapper = mount(AccountPage)
  await wrapper.get('[data-mode-register]').trigger('click')
  await wrapper.get('[data-username]').setValue('Alice')
  await wrapper.get('[data-password]').setValue('😀😀')
  await wrapper.get('form').trigger('submit')
  expect(wrapper.get('[role="alert"]').text()).toContain('4–128')
  expect(api).not.toHaveBeenCalled()
})
