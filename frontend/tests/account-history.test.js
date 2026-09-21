import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import AccountHistoryPage from '../src/pages/AccountHistoryPage.vue'
import { api } from '../src/services/api.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
beforeEach(() => vi.clearAllMocks())

it('shows only returned own role history and never chat content', async () => {
  api.mockResolvedValueOnce([{
    game_id: 'g1', script_id: 'trouble-brewing', seat: 2,
    roles: [{ id: 'chef', name: '厨师' }], guesses: [], winner: 'good', finished: true,
  }])
  const wrapper = mount(AccountHistoryPage)
  await flushPromises()
  expect(api).toHaveBeenCalledWith('/api/account/history')
  expect(wrapper.text()).toContain('厨师')
  expect(wrapper.text()).toContain('善良获胜')
  expect(wrapper.text()).not.toContain('私聊')
})
