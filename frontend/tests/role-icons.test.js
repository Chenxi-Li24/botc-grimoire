import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import RolePicker from '../src/components/storyteller/RolePicker.vue'
import SeatNode from '../src/components/storyteller/SeatNode.vue'

it('shows assigned role icons on claimed and unclaimed storyteller seats', () => {
  const props = {
    seat: { seat: 1, player: null, assigned_role: { id: 'chef', name: '厨师', team: 'townsfolk' } },
    position: { '--seat-x': '50%', '--seat-y': '10%' },
  }
  const wrapper = mount(SeatNode, { props })
  expect(wrapper.get('img').attributes('src')).toBe('/role-icons/chef.webp')

  wrapper.setProps({ seat: { ...props.seat, player: {
    name: '阿青', alive: true, role: { id: 'imp', name: '小恶魔', team: 'demon' },
  } } })
  return wrapper.vm.$nextTick().then(() => {
    expect(wrapper.get('img').attributes('src')).toBe('/role-icons/imp.webp')
  })
})

it('adds icons only to roles with available assets in the manual role picker', () => {
  const wrapper = mount(RolePicker, { props: {
    roles: [
      { id: 'chef', name: '厨师', team: 'townsfolk', ability: '得知信息' },
      { id: 'custom-role', name: '自定义', team: 'townsfolk', ability: '定制能力' },
    ],
    assignments: {}, selectedSeat: 1,
  } })
  expect(wrapper.get('img').attributes('src')).toBe('/role-icons/chef.webp')
  expect(wrapper.findAll('img')).toHaveLength(1)
})
