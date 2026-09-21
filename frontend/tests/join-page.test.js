import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import JoinPage from '../src/pages/JoinPage.vue'
import { api } from '../src/services/api.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  window.location.hash = '#/?room=2468'
})

describe('JoinPage', () => {
  it('leaves the join form usable without showing the storyteller death before the first night', () => {
    const wrapper = mount(JoinPage, { attachTo: document.body })
    expect(wrapper.find('[data-opening-intro]').exists()).toBe(false)
    expect(wrapper.get('[data-join-content]').attributes('inert')).toBeUndefined()
    expect(wrapper.get('[data-room]').element.value).toBe('2468')
    wrapper.unmount()
  })
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

  it('counts visible nickname characters including a combined emoji', async () => {
    const wrapper = mount(JoinPage)
    await wrapper.get('[data-name]').setValue('👩‍👩‍👧‍👦Ab中文123')
    expect(wrapper.get('[data-name-remaining]').text()).toContain('0')
    await wrapper.get('[data-name]').setValue('👩‍👩‍👧‍👦Ab中文1234')
    expect(wrapper.get('[data-name-remaining]').text()).toContain('-1')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('[data-error]').text()).toContain('8')
    expect(api).not.toHaveBeenCalled()
  })

  it('lets an account join with its saved nickname without entering a new guest name', async () => {
    api.mockResolvedValue({ player_id: 'p1' })
    const wrapper = mount(JoinPage, { props: { account: 'LongLegacyName' } })
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.emitted('joined')).toEqual([['p1']]))
  })
})
