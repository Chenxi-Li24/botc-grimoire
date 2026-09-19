import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearPlayerId,
  clearStorytellerPassword,
  getPlayerId,
  getStorytellerPassword,
  setPlayerId,
  setStorytellerPassword,
} from '../src/services/session.js'

beforeEach(() => localStorage.clear())

describe('player session', () => {
  it('stores, reads, and clears the player id', () => {
    expect(getPlayerId()).toBeNull()
    setPlayerId('abc123')
    expect(getPlayerId()).toBe('abc123')
    clearPlayerId()
    expect(getPlayerId()).toBeNull()
  })

  it('stores, reads, and clears the storyteller password', () => {
    setStorytellerPassword('secret')
    expect(getStorytellerPassword()).toBe('secret')
    clearStorytellerPassword()
    expect(getStorytellerPassword()).toBeNull()
  })
})
