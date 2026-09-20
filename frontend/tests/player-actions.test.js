import { ref } from 'vue'
import { expect, it, vi } from 'vitest'

it('keeps only one pending invocation for the same key', async () => {
  const { usePlayerActions } = await import('../src/composables/usePlayerActions.js')
  let resolveFirst
  const firstResult = new Promise((resolve) => { resolveFirst = resolve })
  const actions = usePlayerActions({ service: {}, connected: ref(true) })
  const operation = vi.fn(() => firstResult)
  const duplicate = vi.fn()

  const first = actions.run('vote', operation)
  expect(actions.pending.value).toEqual(['vote'])
  expect(await actions.run('vote', duplicate)).toBeNull()
  expect(duplicate).not.toHaveBeenCalled()

  resolveFirst({ ok: true })
  await expect(first).resolves.toEqual({ ok: true })
  expect(actions.pending.value).toEqual([])
})

it('refuses disconnected actions and retains structured command errors', async () => {
  const { usePlayerActions } = await import('../src/composables/usePlayerActions.js')
  const connected = ref(false)
  const actions = usePlayerActions({ service: { vote: vi.fn() }, connected })

  await expect(actions.run('vote', actions.service.vote)).resolves.toBeNull()
  expect(actions.service.vote).not.toHaveBeenCalled()
  expect(actions.error.value).toEqual({ key: 'vote', message: '连接中，暂时不能操作' })

  connected.value = true
  const failure = Object.assign(new Error('不能投票'), {
    code: 'VOTE_CLOSED',
    details: { stage: 'talk' },
    status: 409,
  })
  await actions.run('vote', vi.fn().mockRejectedValue(failure))
  expect(actions.error.value).toEqual({
    key: 'vote',
    message: '不能投票',
    code: 'VOTE_CLOSED',
    details: { stage: 'talk' },
    status: 409,
  })
  actions.clearError('vote')
  expect(actions.error.value).toBeNull()
})
