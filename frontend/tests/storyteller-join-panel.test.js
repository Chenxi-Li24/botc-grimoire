import { mount, flushPromises } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import JoinPanel from '../src/components/storyteller/JoinPanel.vue'
import { lobbyView } from './fixtures/storytellerView.js'

afterEach(() => vi.unstubAllGlobals())

it('shows separate local and public QR codes with their own join links', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    json: async () => ({
      local_url: 'http://192.168.1.23:8000/#/?room=2468',
      public_url: 'https://join.example.test:30677/#/?room=2468',
    }),
  })))

  const wrapper = mount(JoinPanel, { props: { view: lobbyView } })
  await flushPromises()

  expect(wrapper.get('[data-join-qr="local"]').attributes('src')).toBe('/api/qr?mode=local&room=2468')
  expect(wrapper.get('[data-join-qr="public"]').attributes('src')).toBe('/api/qr?mode=public&room=2468')
  expect(wrapper.get('[data-join-link="local"]').attributes('href')).toBe('http://192.168.1.23:8000/#/?room=2468')
  expect(wrapper.get('[data-join-link="public"]').attributes('href')).toBe('https://join.example.test:30677/#/?room=2468')
  expect(wrapper.text()).toContain('优先使用本地码')
})

it('refreshes both codes and links when the room code changes', async () => {
  let room = '2468'
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    json: async () => ({
      local_url: `http://192.168.1.23:8000/#/?room=${room}`,
      public_url: `https://join.example.test:30677/#/?room=${room}`,
    }),
  })))

  const wrapper = mount(JoinPanel, { props: { view: lobbyView } })
  await flushPromises()
  room = '7777'
  await wrapper.setProps({ view: { ...lobbyView, room_code: '7777' } })
  await flushPromises()

  expect(wrapper.get('[data-join-qr="local"]').attributes('src')).toBe('/api/qr?mode=local&room=7777')
  expect(wrapper.get('[data-join-qr="public"]').attributes('src')).toBe('/api/qr?mode=public&room=7777')
  expect(wrapper.get('[data-join-link="public"]').attributes('href')).toBe('https://join.example.test:30677/#/?room=7777')
})

it('keeps the local code usable when the public tunnel URL is not configured', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    json: async () => ({ local_url: 'http://192.168.1.23:8000/#/?room=2468', public_url: null }),
  })))

  const wrapper = mount(JoinPanel, { props: { view: lobbyView } })
  await flushPromises()

  expect(wrapper.get('[data-join-qr="local"]').exists()).toBe(true)
  expect(wrapper.find('[data-join-qr="public"]').exists()).toBe(false)
  expect(wrapper.text()).toContain('公网码尚未配置')
})
