import { flushPromises, mount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import RecoveryPanel from '../src/components/storyteller/RecoveryPanel.vue'
import { lobbyView } from './fixtures/storytellerView.js'

it('shows a one-time code for the selected participant and never asks for an account password', async () => {
  const service = { issueRecoveryCode: vi.fn().mockResolvedValue({ code: 'one-time-code' }), revokeGuestSessions: vi.fn() }
  const view = { ...lobbyView, players: [{ id: 'p1', name: '阿青', seat: 1 }] }
  const wrapper = mount(RecoveryPanel, { props: { view, service, connected: true } })
  await wrapper.get('[data-recovery-player]').setValue('p1')
  await wrapper.get('[data-issue-recovery]').trigger('click')
  await flushPromises()
  expect(service.issueRecoveryCode).toHaveBeenCalledWith('p1')
  expect(wrapper.text()).toContain('one-time-code')
  expect(wrapper.text()).toContain('阿青')
  expect(wrapper.find('input[type="password"]').exists()).toBe(false)
})
