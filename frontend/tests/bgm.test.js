import { expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { BGM_TRACKS, sceneForView } from '../src/presentation/bgm.js'
import StorytellerBgm from '../src/components/storyteller/StorytellerBgm.vue'
import StageTransition from '../src/components/storyteller/StageTransition.vue'

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

it('shows a skippable lights-out transition only when a live day becomes night', async () => {
  const wrapper = mount(StorytellerBgm, { props: { view: { phase: 'day', day_no: 2 } } })
  expect(wrapper.find('[data-scene-transition]').exists()).toBe(false)
  await wrapper.setProps({ view: { phase: 'night', night_no: 3 } })
  expect(wrapper.get('[data-scene-transition="night"]').text()).toContain('灯光熄灭')
  await wrapper.get('[data-transition-skip]').trigger('click')
  expect(wrapper.find('[data-scene-transition]').exists()).toBe(false)
  wrapper.unmount()
})

it('separates a confirmed execution from the dusk scene and never depicts a tie as death', async () => {
  const day = { phase: 'day', day_no: 2, nominations: [] }
  const wrapper = mount(StorytellerBgm, { props: { view: day } })
  await wrapper.setProps({ view: { phase: 'night', night_no: 3,
    nominations: [{ day: 2, executed: true, nominee: 4 }] } })
  expect(wrapper.get('[data-scene-transition="execution"]').text()).toContain('处决')
  expect(wrapper.get('[data-bgm-scene]').text()).toContain('处决')
  await wrapper.get('[data-transition-skip]').trigger('click')
  expect(wrapper.get('[data-scene-transition="night"]').text()).toContain('灯光熄灭')
  expect(wrapper.get('[data-bgm-scene]').text()).toContain('夜晚')
  wrapper.unmount()

  const tie = mount(StorytellerBgm, { props: { view: day } })
  await tie.setProps({ view: { phase: 'night', night_no: 3,
    nominations: [{ day: 2, executed: false, nominee: 4 }] } })
  expect(tie.get('[data-scene-transition]').attributes('data-scene-transition')).toBe('night')
  tie.unmount()

  const travelerExile = mount(StorytellerBgm, { props: { view: day } })
  await travelerExile.setProps({ view: { phase: 'night', night_no: 3,
    nominations: [{ day: 2, executed: true, nominee: 'traveler-1' }] } })
  expect(travelerExile.get('[data-scene-transition]').attributes('data-scene-transition')).toBe('night')
  travelerExile.unmount()
})

it('introduces daylight after night without replaying an animation on initial connection', async () => {
  const wrapper = mount(StorytellerBgm, { props: { view: { phase: 'night', night_no: 2 } } })
  expect(wrapper.find('[data-scene-transition]').exists()).toBe(false)
  await wrapper.setProps({ view: { phase: 'day', day_no: 2 } })
  expect(wrapper.get('[data-scene-transition="day"]').text()).toContain('天亮')
  wrapper.unmount()
})

it('dismisses the scene on a tap without activating obscured storyteller controls', async () => {
  const wrapper = mount(StageTransition, { props: { view: { phase: 'day', day_no: 1 } } })
  await wrapper.setProps({ view: { phase: 'night', night_no: 2 } })
  await wrapper.get('[data-scene-transition]').trigger('click')
  expect(wrapper.find('[data-scene-transition]').exists()).toBe(false)
  wrapper.unmount()
})

it('rings the daytime bell only when storyteller sound is enabled, then stops on mute', async () => {
  const starts = []
  class FakeAudioContext {
    currentTime = 0
    state = 'running'
    destination = {}
    createOscillator() {
      return { type: '', frequency: { value: 0 }, connect: (target) => target,
        start: (at) => starts.push(at), stop: () => {} }
    }
    createGain() {
      return { gain: { setValueAtTime: () => {}, exponentialRampToValueAtTime: () => {} },
        connect: (target) => target }
    }
    resume() { return Promise.resolve() }
    close() { return Promise.resolve() }
  }
  vi.stubGlobal('AudioContext', FakeAudioContext)
  try {
    const wrapper = mount(StageTransition, { props: {
      view: { phase: 'night', night_no: 2 }, soundEnabled: true,
    } })
    await wrapper.setProps({ view: { phase: 'day', day_no: 2 } })
    expect(starts).toHaveLength(8)
    await vi.waitFor(() => expect(wrapper.emitted('sound-active')).toContainEqual([true]))
    await wrapper.setProps({ soundEnabled: false })
    expect(wrapper.emitted('sound-active').at(-1)).toEqual([false])
    wrapper.unmount()
  } finally {
    vi.unstubAllGlobals()
  }
})

it('does not duck music when the browser refuses bell audio activation', async () => {
  let closes = 0
  class BlockedAudioContext {
    currentTime = 0
    destination = {}
    createOscillator() {
      return { frequency: { value: 0 }, connect: (target) => target,
        start: () => {}, stop: () => {} }
    }
    createGain() {
      return { gain: { setValueAtTime: () => {}, exponentialRampToValueAtTime: () => {} },
        connect: (target) => target }
    }
    resume() { return Promise.reject(new Error('autoplay blocked')) }
    close() { closes += 1; return Promise.resolve() }
  }
  vi.stubGlobal('AudioContext', BlockedAudioContext)
  try {
    const wrapper = mount(StageTransition, { props: {
      view: { phase: 'night', night_no: 2 }, soundEnabled: true,
    } })
    await wrapper.setProps({ view: { phase: 'day', day_no: 2 } })
    await vi.waitFor(() => expect(closes).toBe(1))
    expect(wrapper.emitted('sound-active') || []).not.toContainEqual([true])
    wrapper.unmount()
  } finally {
    vi.unstubAllGlobals()
  }
})

it('does not treat an interrupted audio context as an audible bell', async () => {
  let closes = 0
  class InterruptedAudioContext {
    currentTime = 0
    state = 'interrupted'
    destination = {}
    createOscillator() {
      return { frequency: { value: 0 }, connect: (target) => target,
        start: () => {}, stop: () => {} }
    }
    createGain() {
      return { gain: { setValueAtTime: () => {}, exponentialRampToValueAtTime: () => {} },
        connect: (target) => target }
    }
    resume() { return Promise.resolve() }
    close() { closes += 1; return Promise.resolve() }
  }
  vi.stubGlobal('AudioContext', InterruptedAudioContext)
  try {
    const wrapper = mount(StageTransition, { props: {
      view: { phase: 'night', night_no: 2 }, soundEnabled: true,
    } })
    await wrapper.setProps({ view: { phase: 'day', day_no: 2 } })
    await vi.waitFor(() => expect(closes).toBe(1))
    expect(wrapper.emitted('sound-active') || []).not.toContainEqual([true])
    wrapper.unmount()
  } finally {
    vi.unstubAllGlobals()
  }
})

it('dismisses a scene automatically after its short cue', async () => {
  vi.useFakeTimers()
  try {
    const wrapper = mount(StageTransition, { props: { view: { phase: 'day', day_no: 1 } } })
    await wrapper.setProps({ view: { phase: 'night', night_no: 2 } })
    expect(wrapper.find('[data-scene-transition]').exists()).toBe(true)
    vi.advanceTimersByTime(2400)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-scene-transition]').exists()).toBe(false)
    wrapper.unmount()
  } finally {
    vi.useRealTimers()
  }
})
