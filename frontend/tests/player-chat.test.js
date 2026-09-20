import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PlayerChat from '../src/components/player/PlayerChat.vue'

const seats = [
  { seat: 1, player: { name: '阿青' }, is_me: true },
  { seat: 2, player: { name: '小白' } },
]
const travelers = [{ id: 't1', name: '阿旅', alive: true, exiled: false }]

function activeChatView(overrides = {}) {
  return {
    who: '1',
    my_chat: {
      id: 1,
      color: '#9b5de5',
      owner: 1,
      is_owner: true,
      members: [{ who: '1', name: '阿青' }, { who: 'st', name: '说书人' }],
      requests: [],
      messages: [{ seq: 1, from: 1, name: '阿青', text: '在吗' }],
    },
    invites: [],
    chats_public: [],
    ...overrides,
  }
}

function mountChat(chat, extra = {}) {
  return mount(PlayerChat, {
    props: { chat, seats, travelers, connected: true, pending: [], ...extra },
  })
}

it('keeps the unsent message across a WebSocket projection update', async () => {
  const wrapper = mountChat(activeChatView())
  await wrapper.get('[data-chat-draft]').setValue('还没发出的内容')
  await wrapper.setProps({
    chat: { ...activeChatView(), chats_public: [{ id: 2, color: '#fff', members: [] }] },
  })
  expect(wrapper.get('[data-chat-draft]').element.value).toBe('还没发出的内容')
})

it('emits an exact send command and clears only after success notification', async () => {
  const wrapper = mountChat(activeChatView())
  await wrapper.get('[data-chat-draft]').setValue('你好')
  await wrapper.get('[data-chat-send]').trigger('click')

  expect(wrapper.emitted('command')[0][0]).toEqual({ type: 'send', cid: 1, text: '你好' })
  expect(wrapper.get('[data-chat-draft]').element.value).toBe('你好')
  wrapper.vm.markSent()
  await wrapper.vm.$nextTick()
  expect(wrapper.get('[data-chat-draft]').element.value).toBe('')
})

it('handles invitations and join requests in the chat lobby', async () => {
  const chat = {
    who: '1', my_chat: null,
    invites: [{ id: 4, color: '#fff', owner_name: '小白' }],
    chats_public: [
      { id: 5, color: '#000', members: [{ who: '2', name: '小白' }], requested: false },
      { id: 6, color: '#111', members: [{ who: 't1', name: '阿旅' }], requested: true },
    ],
  }
  const wrapper = mountChat(chat)

  await wrapper.get('[data-invite-accept="4"]').trigger('click')
  await wrapper.get('[data-invite-reject="4"]').trigger('click')
  await wrapper.get('[data-chat-request="5"]').trigger('click')

  expect(wrapper.emitted('command').map(([command]) => command)).toEqual([
    { type: 'respond-invite', cid: 4, accept: true },
    { type: 'respond-invite', cid: 4, accept: false },
    { type: 'request', cid: 5 },
  ])
  expect(wrapper.text()).toContain('已申请')
})

it('creates a chat with numeric, traveler and storyteller participants', async () => {
  const wrapper = mountChat({ who: '1', my_chat: null, invites: [], chats_public: [] })

  await wrapper.get('[data-chat-new]').trigger('click')
  await wrapper.get('[data-chat-pick="2"]').trigger('click')
  await wrapper.get('[data-chat-pick="t1"]').trigger('click')
  await wrapper.get('[data-chat-pick="st"]').trigger('click')
  await wrapper.get('[data-chat-create]').trigger('click')

  expect(wrapper.emitted('command')[0][0]).toEqual({
    type: 'create', invitees: [2, 't1', 'st'],
  })
})

it('supports owner approvals, invite-more, leave and close', async () => {
  const wrapper = mountChat(activeChatView({
    my_chat: {
      ...activeChatView().my_chat,
      requests: [{ who: 't1', name: '阿旅' }],
    },
  }))

  expect(wrapper.text()).toContain('🕯 说书人')
  await wrapper.get('[data-approve="t1"]').trigger('click')
  await wrapper.get('[data-reject="t1"]').trigger('click')
  await wrapper.get('[data-chat-invite-more]').trigger('click')
  await wrapper.get('[data-chat-pick="2"]').trigger('click')
  await wrapper.get('[data-chat-invite-submit]').trigger('click')
  await wrapper.get('[data-chat-leave]').trigger('click')
  await wrapper.get('[data-chat-close]').trigger('click')

  expect(wrapper.emitted('command').map(([command]) => command)).toEqual([
    { type: 'approve', cid: 1, who: 't1', approve: true },
    { type: 'approve', cid: 1, who: 't1', approve: false },
    { type: 'invite-more', cid: 1, invitees: [2] },
    { type: 'leave', cid: 1 },
    { type: 'close', cid: 1 },
  ])
})
