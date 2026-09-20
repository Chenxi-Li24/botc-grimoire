import { mount } from '@vue/test-utils'
import { nextTick, ref, shallowRef } from 'vue'
import { beforeEach, expect, it, vi } from 'vitest'
import DayControlPanel from '../src/components/storyteller/day/DayControlPanel.vue'
import GameControlPanel from '../src/components/storyteller/GameControlPanel.vue'
import StorytellerLiveView from '../src/components/storyteller/StorytellerLiveView.vue'
import { makeStorytellerDayView } from './fixtures/storytellerView.js'

let liveView
let connectionStatus
const service = {
  configure: vi.fn(), assignRandom: vi.fn(), assignManual: vi.fn(),
  setSentinel: vi.fn(), toggleFabled: vi.fn(), start: vi.fn(),
  navigate: vi.fn(), selectNightTargets: vi.fn(), resolveOutcome: vi.fn(),
  deliverInformation: vi.fn(), applyNightEffect: vi.fn(), confirmPitHag: vi.fn(), undoNightEvent: vi.fn(),
  setDayStage: vi.fn(), startNomination: vi.fn(), toggleVote: vi.fn(),
  resolveNomination: vi.fn(), endDay: vi.fn(),
}

vi.mock('../src/composables/useStorytellerView.js', () => ({
  useStorytellerView: vi.fn(() => ({ view: liveView, connectionStatus })),
}))
vi.mock('../src/services/storyteller.js', () => ({
  createStorytellerService: vi.fn(() => service),
}))

beforeEach(() => {
  vi.clearAllMocks()
  liveView = shallowRef(makeStorytellerDayView({ current: null }))
  connectionStatus = ref('connected')
  Object.values(service).forEach((method) => method.mockResolvedValue({ status: 'playing' }))
})

it('runs every daytime command through the Vue storyteller service', async () => {
  const wrapper = mount(StorytellerLiveView, { props: { password: 'secret' } })
  const panel = wrapper.getComponent(DayControlPanel)

  panel.vm.$emit('set-stage', 'nom')
  panel.vm.$emit('start-nomination', { nominator: 1, nominee: 't1' })
  panel.vm.$emit('toggle-vote', 't1')
  panel.vm.$emit('resolve-nomination', true)
  panel.vm.$emit('end-day')
  await nextTick()

  await vi.waitFor(() => {
    expect(service.setDayStage).toHaveBeenCalledWith('nom')
    expect(service.startNomination).toHaveBeenCalledWith(1, 't1')
    expect(service.toggleVote).toHaveBeenCalledWith('t1')
    expect(service.resolveNomination).toHaveBeenCalledWith(true)
    expect(service.endDay).toHaveBeenCalledOnce()
  })
})

it('renders the native day workflow without the legacy day fallback', () => {
  const wrapper = mount(GameControlPanel, {
    props: { view: makeStorytellerDayView({ current: null }), connected: true, pending: [] },
  })
  expect(wrapper.getComponent(DayControlPanel).exists()).toBe(true)
  expect(wrapper.find('a[href="/legacy/#/storyteller"]').exists()).toBe(false)
  expect(wrapper.text()).toContain('白天流程')
})
