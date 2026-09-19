import { expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { useStorytellerCommand } from '../src/composables/useStorytellerCommand.js'

it('refuses disconnected writes and records a local error', async () => {
  const state = useStorytellerCommand({ connected: ref(false) })
  const operation = vi.fn()
  await state.run('configure', operation)
  expect(operation).not.toHaveBeenCalled()
  expect(state.error.value).toEqual({ key: 'configure', message: '连接中，暂时不能操作' })
})

it('tracks only each initiating command and cleans up failures', async () => {
  const state = useStorytellerCommand({ connected: ref(true) })
  let finish
  const first = state.run('sentinel', () => new Promise((resolve) => { finish = resolve }))
  expect(state.pending.value).toEqual(['sentinel'])

  await state.run('fabled:angel', () => Promise.reject(new Error('不能修改传奇角色')))
  expect(state.pending.value).toEqual(['sentinel'])
  expect(state.error.value).toEqual({ key: 'fabled:angel', message: '不能修改传奇角色' })

  finish({ ok: true })
  await first
  expect(state.pending.value).toEqual([])
})
