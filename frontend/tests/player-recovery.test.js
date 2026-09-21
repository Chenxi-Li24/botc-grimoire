import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, expect, it, vi } from 'vitest'
import RecoverIdentity from '../src/components/player/RecoverIdentity.vue'
import { api } from '../src/services/api.js'

vi.mock('../src/services/api.js', () => ({ api: vi.fn() }))
beforeEach(() => vi.clearAllMocks())

it('redeems a storyteller code and lets the app recheck its server session', async () => {
  api.mockResolvedValue({ player_id: 'original-player' })
  const wrapper = mount(RecoverIdentity, { props: { initialRoom: '2468' } })
  await wrapper.get('[data-recovery-code]').setValue('one-time-code')
  await wrapper.get('form').trigger('submit')
  await flushPromises()
  expect(api).toHaveBeenCalledWith('/api/recover-participant', {
    method: 'POST', body: JSON.stringify({ room_code: '2468', code: 'one-time-code' }),
  })
  expect(wrapper.emitted('recovered')).toEqual([[]])
  expect(localStorage.getItem('one-time-code')).toBeNull()
})
