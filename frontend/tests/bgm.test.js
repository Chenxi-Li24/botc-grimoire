import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { BGM_TRACKS, sceneForView } from '../src/presentation/bgm.js'
import StorytellerBgm from '../src/components/storyteller/StorytellerBgm.vue'

it('selects a storyteller-only cue from live phase without revealing it to players', () => {
  expect(sceneForView({ phase: 'night' })).toBe('night')
  expect(sceneForView({ phase: 'day', day_stage: 'talk', chats: [] })).toBe('public-chat')
  expect(sceneForView({ phase: 'day', day_stage: 'talk', chats: [{ closed: false }] })).toBe('private-chat')
  expect(sceneForView({ phase: 'day', day_stage: 'nom', current: { votes: [] } })).toBe('vote')
  expect(sceneForView({ phase: 'day', day_stage: 'nom', day_no: 2, nominations: [{ day: 2, executed: true }] })).toBe('execution')
  expect(sceneForView({ phase: 'day', winner: 'good' })).toBe('victory')
  expect(sceneForView({ phase: 'day', winner: 'good' }, true)).toBe('replay')
  expect(Object.keys(BGM_TRACKS)).toEqual(['night', 'day', 'vote', 'private-chat', 'public-chat', 'execution', 'replay', 'victory'])
})

it('shows manual track selection and remains silent until the storyteller starts it', async () => {
  const wrapper = mount(StorytellerBgm, { props: { view: { phase: 'night' } } })
  expect(wrapper.get('[data-bgm-toggle]').text()).toContain('启动配乐')
  expect(wrapper.get('[data-bgm-scene]').text()).toContain('夜晚')
  await wrapper.get('[data-bgm-select]').setValue('vote')
  expect(wrapper.get('[data-bgm-scene]').text()).toContain('投票')
  wrapper.unmount()
})
