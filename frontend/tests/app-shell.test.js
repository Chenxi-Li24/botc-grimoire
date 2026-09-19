import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import App from '../src/App.vue'

describe('App shell', () => {
  it('mounts a page container', () => {
    const wrapper = mount(App)
    expect(wrapper.get('[data-app-shell]').exists()).toBe(true)
  })
})
