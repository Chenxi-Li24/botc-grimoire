import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearCsrfToken,
  clearStorytellerPassword,
  getCsrfToken,
  getStorytellerPassword,
  setCsrfToken,
  setStorytellerPassword,
} from '../src/services/session.js'

beforeEach(() => localStorage.clear())

describe('player session', () => {
  it('keeps the CSRF token only in memory', () => {
    clearCsrfToken()
    expect(getCsrfToken()).toBeNull()
    setCsrfToken('csrf123')
    expect(getCsrfToken()).toBe('csrf123')
    expect(localStorage.getItem('csrf123')).toBeNull()
    clearCsrfToken()
    expect(getCsrfToken()).toBeNull()
  })

  it('stores, reads, and clears the storyteller password', () => {
    setStorytellerPassword('secret')
    expect(getStorytellerPassword()).toBe('secret')
    clearStorytellerPassword()
    expect(getStorytellerPassword()).toBeNull()
  })
})
