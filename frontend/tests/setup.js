import { afterEach } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'

enableAutoUnmount(afterEach)

// jsdom has no media decoder; keep storyteller audio lifecycle tests deterministic.
HTMLMediaElement.prototype.load = () => {}
HTMLMediaElement.prototype.pause = () => {}
HTMLMediaElement.prototype.play = () => Promise.resolve()
