import { mount } from '@vue/test-utils'
import { ref, shallowRef } from 'vue'
import { expect, it, vi } from 'vitest'
import ContextPanel from '../src/components/storyteller/ContextPanel.vue'
import StorytellerHeader from '../src/components/storyteller/StorytellerHeader.vue'
import StorytellerLiveView from '../src/components/storyteller/StorytellerLiveView.vue'
import { makeStorytellerDayView } from './fixtures/storytellerView.js'

const view = makeStorytellerDayView({
  day_stage: 'talk',
  chats: [
    {
      id: 1, owner: 1, color: '#aabbcc', closed: false,
      members: [{ who: '1', name: '阿青' }, { who: 'st', name: '说书人' }],
      invites: [], join_requests: [],
      messages: [{ seq: 1, from: 1, name: '阿青', text: '旧消息' }],
    },
    {
      id: 2, owner: 2, color: '#ccaabb', closed: false,
      members: [{ who: '2', name: '小白' }],
      invites: [{ who: 'st', name: '说书人' }], join_requests: [], messages: [],
    },
    {
      id: 3, owner: 3, color: '#bbccaa', closed: true,
      members: [{ who: '3', name: '阿紫' }],
      invites: [], join_requests: [],
      messages: [{ seq: 2, from: 3, name: '阿紫', text: '归档内容' }],
    },
  ],
})
const liveService = {
  sendStorytellerChat: vi.fn().mockResolvedValue({ status: 'playing' }),
}
vi.mock('../src/composables/useStorytellerView.js', () => ({
  useStorytellerView: () => ({ view: shallowRef(view), connectionStatus: ref('connected') }),
}))
vi.mock('../src/services/storyteller.js', () => ({
  createStorytellerService: () => liveService,
}))

const mountChat = (connected = true) => mount(ContextPanel, {
  props: { view, selectedSeat: null, adminTab: 'chats', connected },
})

it('shows active conversations and archived messages without offering send on closed chats', async () => {
  const wrapper = mountChat()
  expect(wrapper.text()).toContain('阿青')
  expect(wrapper.text()).toContain('小白')
  await wrapper.get('[data-chat-admin-open="1"]').trigger('click')
  expect(wrapper.text()).toContain('旧消息')
  expect(wrapper.get('[data-chat-admin-send="1"]').exists()).toBe(true)
  await wrapper.get('[data-chat-admin-open="3"]').trigger('click')
  expect(wrapper.text()).toContain('归档内容')
  expect(wrapper.find('[data-chat-admin-send="3"]').exists()).toBe(false)
})

it('answers invites, sends a trimmed message, and leaves own chat', async () => {
  const wrapper = mountChat()
  await wrapper.get('[data-chat-admin-accept="2"]').trigger('click')
  await wrapper.get('[data-chat-admin-reject="2"]').trigger('click')
  expect(wrapper.emitted('answer-chat-invite')).toEqual([
    [{ id: 2, accept: true }], [{ id: 2, accept: false }],
  ])
  await wrapper.get('[data-chat-admin-open="1"]').trigger('click')
  await wrapper.get('[data-chat-admin-draft="1"]').setValue('  今晚见  ')
  await wrapper.get('[data-chat-admin-send="1"]').trigger('click')
  expect(wrapper.emitted('send-storyteller-chat')).toEqual([[{ id: 1, text: '今晚见' }]])
  await wrapper.get('[data-chat-admin-leave="1"]').trigger('click')
  expect(wrapper.emitted('leave-storyteller-chat')).toEqual([[1]])
})

it('requires confirmation to close or recall and blocks writes offline', async () => {
  const wrapper = mountChat()
  await wrapper.get('[data-chat-admin-close="2"]').trigger('click')
  expect(wrapper.emitted('close-storyteller-chat')).toBeUndefined()
  await wrapper.get('[data-chat-admin-close="2"]').trigger('click')
  expect(wrapper.emitted('close-storyteller-chat')).toEqual([[2]])
  await wrapper.get('[data-chat-admin-recall]').trigger('click')
  expect(wrapper.emitted('recall-chats')).toBeUndefined()
  await wrapper.get('[data-chat-admin-recall]').trigger('click')
  expect(wrapper.emitted('recall-chats')).toEqual([[]])

  const offline = mountChat(false)
  expect(offline.get('[data-chat-admin-accept="2"]').attributes('disabled')).toBeDefined()
  expect(offline.get('[data-chat-admin-recall]').attributes('disabled')).toBeDefined()
})

it('offers a native chat entrance from the storyteller header', async () => {
  const wrapper = mount(StorytellerHeader, { props: { view, connectionStatus: 'connected' } })
  await wrapper.get('[data-open-chats]').trigger('click')
  expect(wrapper.emitted('open-chats')).toEqual([[]])
})

it('sends storyteller chat through the live command boundary', async () => {
  liveService.sendStorytellerChat.mockClear()
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  await wrapper.get('[data-open-chats]').trigger('click')
  await wrapper.get('[data-chat-admin-open="1"]').trigger('click')
  await wrapper.get('[data-chat-admin-draft="1"]').setValue('  晚上见  ')
  await wrapper.get('[data-chat-admin-send="1"]').trigger('click')
  await vi.waitFor(() => expect(liveService.sendStorytellerChat).toHaveBeenCalledWith(1, '晚上见'))
})

it('keeps chat records and recall available while nomination pauses storyteller messaging', async () => {
  const wrapper = mount(ContextPanel, {
    props: { view: { ...view, day_stage: 'nom' }, selectedSeat: null, adminTab: 'chats', connected: true },
  })
  await wrapper.get('[data-chat-admin-open="1"]').trigger('click')

  expect(wrapper.text()).toContain('旧消息')
  expect(wrapper.text()).toContain('提名阶段暂停私聊')
  expect(wrapper.get('[data-chat-admin-send="1"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-chat-admin-accept="2"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-chat-admin-recall]').attributes('disabled')).toBeUndefined()
})
