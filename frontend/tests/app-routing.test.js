import { describe, expect, it, vi } from 'vitest'
import { resolveEntry } from '../src/services/navigation.js'

describe('entry routing', () => {
  it('opens the canonical storyteller route in Vue', async () => {
    await expect(resolveEntry({
      hash: '#/storyteller', playerId: null, validatePlayer: vi.fn(),
    })).resolves.toEqual({ vuePage: 'storyteller' })
  })

  it('redirects the old preview route to the canonical storyteller route', async () => {
    await expect(resolveEntry({
      hash: '#/storyteller-preview', playerId: null, validatePlayer: vi.fn(),
    })).resolves.toEqual({
      redirectHash: '#/storyteller',
      vuePageAfterRedirect: 'storyteller',
    })
  })

  it('keeps a valid returning player in Vue', async () => {
    const validatePlayer = vi.fn().mockResolvedValue({})
    await expect(resolveEntry({ hash: '', playerId: 'p1', validatePlayer }))
      .resolves.toEqual({ vuePage: 'player' })
    expect(validatePlayer).toHaveBeenCalledWith('p1')
  })

  it('returns stale players to join', async () => {
    const validatePlayer = vi.fn().mockRejectedValue(new Error('gone'))
    await expect(resolveEntry({ hash: '', playerId: 'stale', validatePlayer }))
      .resolves.toBe('join')
  })
})
