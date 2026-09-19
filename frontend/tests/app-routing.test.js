import { describe, expect, it, vi } from 'vitest'
import { resolveEntry } from '../src/services/navigation.js'

describe('entry routing', () => {
  it('keeps the complete storyteller route on legacy', async () => {
    await expect(resolveEntry({
      hash: '#/storyteller', playerId: null, validatePlayer: vi.fn(),
    })).resolves.toEqual({ legacyUrl: '/legacy/#/storyteller' })
  })

  it('opens only the explicit storyteller preview in Vue', async () => {
    await expect(resolveEntry({
      hash: '#/storyteller-preview', playerId: null, validatePlayer: vi.fn(),
    })).resolves.toEqual({ vuePage: 'storyteller-preview' })
  })

  it('sends a valid returning player to legacy', async () => {
    const validatePlayer = vi.fn().mockResolvedValue({})
    await expect(resolveEntry({ hash: '', playerId: 'p1', validatePlayer }))
      .resolves.toEqual({ legacyUrl: '/legacy/' })
    expect(validatePlayer).toHaveBeenCalledWith('p1')
  })

  it('returns stale players to join', async () => {
    const validatePlayer = vi.fn().mockRejectedValue(new Error('gone'))
    await expect(resolveEntry({ hash: '', playerId: 'stale', validatePlayer }))
      .resolves.toBe('join')
  })
})
