import { describe, expect, it } from 'vitest'
import { resolveEntry } from '../src/services/navigation.js'

describe('entry routing', () => {
  it('opens the canonical storyteller route in Vue', () => {
    expect(resolveEntry({ hash: '#/storyteller', session: null })).toEqual({ vuePage: 'storyteller' })
  })

  it('redirects the old preview route to the canonical storyteller route', () => {
    expect(resolveEntry({ hash: '#/storyteller-preview', session: null })).toEqual({
      redirectHash: '#/storyteller',
      vuePageAfterRedirect: 'storyteller',
    })
  })

  it('keeps a server-validated returning player in Vue', () => {
    expect(resolveEntry({ hash: '', session: { player_id: 'p1' } })).toEqual({ vuePage: 'player' })
  })

  it('returns sessions without a current player to join', () => {
    expect(resolveEntry({ hash: '', session: { account: 'Alice', player_id: null } }))
      .toEqual({ vuePage: 'join' })
  })
})
