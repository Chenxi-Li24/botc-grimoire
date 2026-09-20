import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PublicTimeline from '../src/components/player/PublicTimeline.vue'
import { makeDayPlayerView } from './fixtures/playerView.js'

it('renders live vote chips for seats and travelers', () => {
  const wrapper = mount(PublicTimeline, {
    props: {
      view: makeDayPlayerView({
        travelers_public: [{ id: 't1', name: '阿旅', alive: true }],
        current: { nominator: 't1', nominee: 2, votes: [1, 't1'] },
      }),
    },
  })

  expect(wrapper.text()).toContain('🎒 阿旅 提名 2号 小白')
  expect(wrapper.text()).toContain('1号 阿青')
  expect(wrapper.text()).toContain('赞成 2 票')
})

it('groups public deaths by day including empty seats and travelers', () => {
  const wrapper = mount(PublicTimeline, {
    props: {
      view: makeDayPlayerView({
        deaths: [
          { seat: 1, name: '阿青', day: 1 },
          { seat: 3, name: '厨师', day: 2, empty: true },
          { seat: 't1', name: '阿旅', day: 2, exiled: true },
        ],
      }),
    },
  })

  expect(wrapper.text()).toContain('第 1 天')
  expect(wrapper.text()).toContain('1号 阿青')
  expect(wrapper.text()).toContain('3号 厨师（空座）')
  expect(wrapper.text()).toContain('🎒 阿旅（流放）')
})

it('renders failed, pending and executed nomination history', () => {
  const wrapper = mount(PublicTimeline, {
    props: {
      view: makeDayPlayerView({
        nominations: [
          { day: 1, nominator: 1, nominee: 2, votes: [], passed: false, executed: false },
          { day: 1, nominator: 2, nominee: 1, votes: [2], passed: true, executed: false },
          { day: 2, nominator: 't1', nominee: 't2', votes: ['t1'], passed: true, executed: true },
        ],
        travelers_public: [
          { id: 't1', name: '阿甲', alive: true },
          { id: 't2', name: '阿乙', alive: false },
        ],
      }),
    },
  })

  expect(wrapper.text()).toContain('未通过')
  expect(wrapper.text()).toContain('待处决')
  expect(wrapper.text()).toContain('已流放')
})
