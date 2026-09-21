import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import JoinPage from '../src/pages/JoinPage.vue'
import { api } from '../src/services/api.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
  window.location.hash = '#/?room=2468'
})

describe('JoinPage', () => {
  it('prefills the room from the QR hash', () => {
    const wrapper = mount(JoinPage)
    expect(wrapper.get('[data-room]').element.value).toBe('2468')
  })

  it('rejects a room code that is not four digits', async () => {
    const wrapper = mount(JoinPage)
    await wrapper.get('[data-name]').setValue('小明')
    await wrapper.get('[data-room]').setValue('12')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('[data-error]').text()).toBe('房间号需为 4 位数字')
    expect(api).not.toHaveBeenCalled()
  })

  it('joins without storing the public player id as a credential', async () => {
    api.mockResolvedValue({ player_id: 'player-token' })
    const wrapper = mount(JoinPage)
    await wrapper.get('[data-name]').setValue('小明')
    await wrapper.get('[data-room]').setValue('2468')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.emitted('joined')).toBeDefined())
    expect(localStorage.getItem('botc_player_id')).toBeNull()
    expect(wrapper.emitted('joined')).toEqual([['player-token']])
  })

  it('shows the server error and re-enables submit', async () => {
    api.mockRejectedValue(new Error('房间号错误'))
    const wrapper = mount(JoinPage)
    await wrapper.get('[data-name]').setValue('小明')
    await wrapper.get('[data-room]').setValue('2468')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.get('[data-error]').text()).toBe('房间号错误'))
    expect(wrapper.get('[data-submit]').attributes('disabled')).toBeUndefined()
  })
})
