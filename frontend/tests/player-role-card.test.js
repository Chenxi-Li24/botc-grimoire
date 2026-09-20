import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import PlayerRoleCard from '../src/components/player/PlayerRoleCard.vue'
import { makeLobbyPlayerView, makePlayerView } from './fixtures/playerView.js'

it('does not reveal an identity before the game starts', () => {
  const wrapper = mount(PlayerRoleCard, {
    props: { view: makeLobbyPlayerView({ me: { id: 'p1', name: '阿青', seat: 1, alive: true } }) },
  })
  expect(wrapper.text()).toContain('等待说书人开始游戏')
  expect(wrapper.text()).not.toContain('厨师')
})

it('shows perceived identity, changes, madness and private meeting facts', async () => {
  const wrapper = mount(PlayerRoleCard, {
    props: {
      view: makePlayerView({
        role_changed: { id: 'empath', name: '共情者', en: 'Empath', team: 'townsfolk', ability: '获得信息。' },
        team_changed: 'evil',
        my_mad: { role: { name: '送葬者' } },
        bluffs: [{ id: 'washerwoman', name: '洗衣妇' }],
        demon_seats: [{ seat: 5, name: '阿魔' }],
        minion_seats: [{ seat: 4, name: '阿爪' }],
        lunatic_seats: [{ seat: 3, name: '阿疯' }],
      }),
    },
  })

  expect(wrapper.text()).toContain('共情者')
  expect(wrapper.text()).toContain('阵营已变为邪恶')
  expect(wrapper.text()).toContain('必须声称自己是「送葬者」')
  expect(wrapper.text()).toContain('洗衣妇')
  expect(wrapper.text()).toContain('5号 阿魔')
  expect(wrapper.text()).toContain('4号 阿爪')
  expect(wrapper.text()).toContain('3号 阿疯')

  await wrapper.get('[data-role-card]').trigger('click')
  expect(wrapper.text()).toContain('身份已隐藏')
  expect(wrapper.text()).not.toContain('共情者')
  expect(wrapper.text()).not.toContain('洗衣妇')
  await wrapper.get('[data-role-cover]').trigger('click')
  expect(wrapper.text()).toContain('共情者')
})

it('renders traveler identity and only the traveler private alignment', () => {
  const wrapper = mount(PlayerRoleCard, {
    props: {
      view: makePlayerView({
        me: { id: 'p1', name: '阿旅', seat: null, alive: true },
        traveler: {
          id: 't1', name: '阿旅', alive: true, align: 'evil', joined_phase: 'day', joined_no: 1,
          role: { id: 'scapegoat', name: '替罪羊', en: 'Scapegoat', ability: '可能代替处决。' },
        },
      }),
    },
  })

  expect(wrapper.text()).toContain('替罪羊')
  expect(wrapper.text()).toContain('邪恶')
  expect(wrapper.text()).toContain('第 1 天加入')
})

it('shows official composition, Sentinel uncertainty and public fabled roles', () => {
  const wrapper = mount(PlayerRoleCard, {
    props: {
      view: makePlayerView({
        sentinel: true,
        fabled: [{ id: 'doomsayer', name: '末日预言者' }],
      }),
    },
  })

  expect(wrapper.text()).toContain('镇民 3')
  expect(wrapper.text()).toContain('外来者 0')
  expect(wrapper.text()).toContain('可能比官方配比 +1 或 −1')
  expect(wrapper.text()).toContain('末日预言者')
})
