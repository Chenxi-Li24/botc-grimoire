import { mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import StorytellerLogin from '../src/components/storyteller/StorytellerLogin.vue'
import { api } from '../src/services/api.js'
import { setStorytellerPassword } from '../src/services/session.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
vi.mock('../src/services/session.js', () => ({ setStorytellerPassword: vi.fn() }))

beforeEach(() => vi.clearAllMocks())

it('stores an accepted password and opens the live view', async () => {
  api.mockResolvedValue({ ok: true })
  const wrapper = mount(StorytellerLogin)
  await wrapper.get('[data-password]').setValue('secret')
  await wrapper.get('form').trigger('submit')
  await vi.waitFor(() => expect(setStorytellerPassword).toHaveBeenCalledWith('secret'))

  expect(api).toHaveBeenCalledWith('/api/login', {
    method: 'POST', body: JSON.stringify({ password: 'secret' }),
  })
  expect(wrapper.emitted('authenticated')).toEqual([['secret']])
})

it('shows a rejected password and re-enables submit', async () => {
  api.mockResolvedValue({ ok: false })
  const wrapper = mount(StorytellerLogin)
  await wrapper.get('[data-password]').setValue('wrong')
  await wrapper.get('form').trigger('submit')
  await vi.waitFor(() => expect(wrapper.get('[data-error]').text()).toBe('密码错误'))
  expect(wrapper.get('[data-submit]').attributes('disabled')).toBeUndefined()
})
