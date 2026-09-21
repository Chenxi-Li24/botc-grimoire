<script setup>
import { computed } from 'vue'
import { nightErrorMessage, nightStepSummary } from '../../../presentation/nightWorkflow.js'
import EffectHistory from './EffectHistory.vue'
import InformationEditor from './InformationEditor.vue'
import OutcomeAdjudicator from './OutcomeAdjudicator.vue'
import PitHagCard from './PitHagCard.vue'
import SeatTargetPicker from './SeatTargetPicker.vue'
import UndoPreview from './UndoPreview.vue'

const props = defineProps({
  view: { type: Object, required: true },
  night: { type: Object, required: true },
  connected: { type: Boolean, default: false },
  pending: { type: Array, default: () => [] },
  error: { type: Object, default: null },
})

const workflow = computed(() => props.night.workflow || {})
const step = computed(() => props.night.inspectedStep || props.night.currentTask)
const current = computed(() => props.night.currentTask)
const isCurrent = computed(() => Boolean(step.value && current.value?.id === step.value.id))
const actorRoleId = computed(() => step.value?.source?.ability_character || step.value?.perceived_as || step.value?.character_id)
const role = computed(() => props.view.roles?.find((item) => item.id === actorRoleId.value) || null)
const selection = computed(() => {
  const configured = role.value?.selection
  const required = step.value?.required_fields || []
  if (!configured || (!required.includes('targets') && !required.includes('character'))) return null
  return {
    ...configured,
    players: required.includes('targets') ? configured.players : 0,
    characters: required.includes('character') ? configured.characters : 0,
  }
})
const targetSeat = computed(() => props.night.selectedTargets?.[0] || null)
const selectedSeat = computed(() => props.view.seats?.find((item) => item.seat === props.night.selectedSeat) || null)
const stepOutcomes = computed(() => (workflow.value.outcomes?.pending || []).filter((item) => (
  item.metadata?.step_id === step.value?.id || (!item.metadata?.step_id && item.source_seat === step.value?.actor_seat)
)))
const stepDrafts = computed(() => (workflow.value.information?.drafts || []).filter((item) => (
  item.actor_seat === step.value?.actor_seat
)))
const notices = computed(() => (workflow.value.information?.notices || []).filter((item) => (
  item.actor_seat === step.value?.actor_seat || item.seat === step.value?.actor_seat
)))
const pitHagPreview = computed(() => (workflow.value.transformations?.pending || []).find((item) => (
  item.actor_seat === step.value?.actor_seat
)) || null)
const selectedEffects = computed(() => (workflow.value.effects?.history || []).filter((item) => (
  item.target_seat === props.night.selectedSeat
)))
const stepEffects = computed(() => (workflow.value.effects?.history || []).filter((item) => (
  item.source_seat === step.value?.actor_seat
)))
const stepInformationHandled = computed(() => Boolean(
  role.value?.information_resolver
  && Object.prototype.hasOwnProperty.call(step.value?.values || {}, 'targets')
))
const recordedTargets = computed(() => step.value?.values?.targets || [])
const recordedCharacter = computed(() => step.value?.values?.character || null)
const recordedCharacterName = computed(() => props.view.roles?.find((item) => item.id === recordedCharacter.value)?.name || recordedCharacter.value)
const stepSelectionRecorded = computed(() => Object.prototype.hasOwnProperty.call(step.value?.values || {}, 'targets'))
const stepOutcomeHandled = computed(() => Boolean(
  Object.prototype.hasOwnProperty.call(step.value?.values || {}, 'targets')
  && (role.value?.team === 'demon' || actorRoleId.value === 'lunatic')
))
const omissions = computed(() => props.night.forceOmissions?.[current.value?.id] || [])
const actionBusy = computed(() => props.pending.some((key) => key.startsWith('night:')))

const omissionLabels = {
  targets: '尚未选择玩家',
  character: '尚未选择角色',
  acknowledged: '尚未确认手动步骤',
}
function omissionLabel(value) {
  if (omissionLabels[value]) return omissionLabels[value]
  if (value.startsWith('outcome:')) return '选择结果尚未裁定'
  if (value.startsWith('information:')) return '信息尚未发送'
  if (value.startsWith('transformation:')) return '角色变化尚未确认'
  return value
}
function noticeText(notice) {
  if (notice.message || notice.text) return notice.message || notice.text
  const recipient = notice.actor_seat ? `${notice.actor_seat}号` : '对应玩家'
  const payload = typeof notice.payload === 'string'
    ? notice.payload
    : JSON.stringify(notice.payload)
  return `已自动发送给 ${recipient}：${payload}`
}
function targetRoleTeams() {
  return selection.value?.character_teams || []
}
function setClaimedCharacter(event) {
  props.night.setSelectedCharacter(event.target.value || null, step.value?.id)
}
function handleOutcomeChoice({ id, value }) {
  props.night.setOutcomeChoice(id, value)
}
function handleClaimUpdate({ id, claims }) {
  props.night.setInformationClaims(id, claims)
}
function handleResultUpdate({ id, result }) {
  props.night.setInformationResult(id, result)
}
function roleCanCreateOutcome() {
  return Boolean(selection.value?.players)
    && (role.value?.team === 'demon' || actorRoleId.value === 'lunatic')
}
async function submitAction() {
  if (!step.value || !isCurrent.value) return
  const targets = props.night.selectedTargets || []
  const base = { step_id: step.value.id, selected_seats: targets }
  if (['poisoner', 'widow', 'cerenovus'].includes(actorRoleId.value)) {
    await props.night.applyNightEffect({
      action: actorRoleId.value,
      source_seat: step.value.actor_seat,
      step_id: step.value.id,
      target_seat: targets[0],
      ...(actorRoleId.value === 'cerenovus' ? { claimed_character: props.night.selectedCharacter } : {}),
    })
    return
  }
  if (role.value?.information_resolver) {
    await props.night.deliverInformation({
      action: 'prepare',
      step_id: step.value.id,
      actor_seat: step.value.actor_seat,
      targets,
    })
    return
  }
  await props.night.selectNightTargets({
    ...base,
    create_outcome: roleCanCreateOutcome(),
    character_id: props.night.selectedCharacter,
    acknowledged: step.value.required_fields?.includes('acknowledged') || !step.value.required_fields?.length,
  })
}
function actionLabel() {
  if (role.value?.information_resolver) return '生成角色信息'
  if (['poisoner', 'widow', 'cerenovus'].includes(actorRoleId.value)) return '确认并记录状态'
  if (roleCanCreateOutcome()) return '记录选择并进入裁定'
  return step.value?.required_fields?.length ? '确认本步操作' : '标记已处理'
}
function previewUndo(eventId) {
  props.night.undoNightEvent({ event_id: eventId, confirm: false })
}
function confirmUndo(eventId) {
  props.night.undoNightEvent({ event_id: eventId, confirm: true })
}
</script>

<template>
  <div class="night-task-panel" data-night-task>
    <header class="night-task-header">
      <div>
        <p class="panel-eyebrow">第 {{ workflow.night_no }} 夜 · {{ isCurrent ? '当前任务' : '查看记录' }}</p>
        <h3>{{ nightStepSummary(step) }}</h3>
      </div>
      <button v-if="!isCurrent" class="chip-button" type="button" @click="night.inspectCurrentTask()">回到当前</button>
    </header>

    <div class="night-task-body">
      <template v-if="selectedSeat">
        <section class="night-card seat-night-detail">
          <div class="night-card-heading"><h4>{{ selectedSeat.seat }}号 · {{ selectedSeat.player?.name || '线下/未领取' }}</h4><button class="chip-button" type="button" @click="night.setSelectedSeat(null)">返回任务</button></div>
          <p>{{ selectedSeat.player?.role?.name || selectedSeat.assigned_role?.name || '未配置角色' }}</p>
          <p v-if="selectedSeat.secret_dead" class="state-alert">本夜已判定死亡，天亮前仅说书人可见。</p>
        </section>
        <EffectHistory :effects="selectedEffects" :seat="selectedSeat.seat" />
      </template>

      <template v-else-if="step">
        <section class="night-card task-reminder">
          <div class="night-card-heading"><h4>{{ step.name || step.character_id }}</h4><span>{{ step.actor_seat ? `${step.actor_seat}号` : '全体流程' }}</span></div>
          <p>{{ step.reminder || '按剧本规则完成此步骤。' }}</p>
          <p v-if="step.source?.claimed_by == null && step.actor_seat" class="inline-warning">该角色座位尚未被线上玩家领取，按线下玩家继续执行。</p>
          <p v-if="!isCurrent" class="inline-note">当前为只读查看；点击“回到当前”后才能执行操作。</p>
        </section>

        <section v-if="recordedTargets.length || recordedCharacter" class="night-card" data-night-recorded-choice>
          <div class="night-card-heading"><h4>已记录选择</h4><span>来自当前夜晚记录</span></div>
          <p v-if="recordedTargets.length">玩家：{{ recordedTargets.map((seat) => `${seat}号`).join('、') }}</p>
          <p v-if="recordedCharacter">角色：{{ recordedCharacterName }}</p>
        </section>

        <section v-if="workflow.context?.lunatic_choices?.length && role?.team === 'demon'" class="night-card lunatic-context">
          <div class="night-card-heading"><h4>疯子的选择</h4><span>恶魔可据此决定</span></div>
          <p v-for="choice in workflow.context.lunatic_choices" :key="choice.outcome_id">{{ choice.lunatic_seat }}号疯子选择了 {{ choice.target_seats.map((seat) => `${seat}号`).join('、') }}</p>
        </section>

        <SeatTargetPicker
          v-if="isCurrent && selection?.players && !stepSelectionRecorded && !stepOutcomeHandled && !stepInformationHandled"
          :seats="view.seats"
          :roles="view.roles"
          :selected="night.selectedTargets"
          :actor-seat="step.actor_seat"
          :selection="selection"
          @toggle="night.toggleTarget($event, step.id)"
          @inspect="night.setSelectedSeat($event)"
        />

        <PitHagCard
          v-if="isCurrent && actorRoleId === 'pithag'"
          :step="step"
          :preview="pitHagPreview"
          :target-seat="targetSeat"
          :character-id="night.selectedCharacter"
          :roles="view.roles"
          :connected="connected"
          :pending="pending"
          @set-character="night.setSelectedCharacter($event, step.id)"
          @preview="night.confirmPitHag"
          @confirm="night.confirmPitHag"
        />

        <label v-else-if="isCurrent && selection?.characters" class="night-card field-row">选择角色
          <select :value="night.selectedCharacter || ''" @change="setClaimedCharacter">
            <option value="">请选择角色</option>
            <option
              v-for="candidate in view.roles.filter((item) => !targetRoleTeams().length || targetRoleTeams().includes(item.team))"
              :key="candidate.id"
              :value="candidate.id"
            >{{ candidate.name }}</option>
          </select>
        </label>

        <button
          v-if="isCurrent && step.actor_seat && actorRoleId !== 'pithag' && !stepOutcomes.length && !stepDrafts.length && !stepSelectionRecorded && !stepInformationHandled && !stepOutcomeHandled"
          class="btn primary task-submit"
          type="button"
          :disabled="!connected || actionBusy || (selection?.players && night.selectedTargets.length !== selection.players) || (selection?.characters && !night.selectedCharacter)"
          @click="submitAction"
        >{{ actionLabel() }}</button>

        <OutcomeAdjudicator
          :outcomes="stepOutcomes"
          :choices="night.outcomeChoices"
          :connected="connected && isCurrent"
          :pending="pending"
          @update-choice="handleOutcomeChoice"
          @resolve="night.resolveOutcome"
        />
        <InformationEditor
          :drafts="stepDrafts"
          :results="night.informationResults"
          :claims="night.informationClaims"
          :roles="view.roles"
          :connected="connected && isCurrent"
          :pending="pending"
          @set-result="handleResultUpdate"
          @set-claims="handleClaimUpdate"
          @deliver="night.deliverInformation"
        />

        <section v-if="notices.length" class="night-card automatic-notices">
          <div class="night-card-heading"><h4>已自动发送</h4><span>无需确认</span></div>
          <p v-for="(notice, index) in notices" :key="notice.id || index">{{ noticeText(notice) }}</p>
        </section>

        <EffectHistory v-if="stepEffects.length" :effects="stepEffects" />
        <UndoPreview
          :previews="workflow.undo_previews || []"
          :selected="night.undoPreview"
          :connected="connected"
          :pending="pending"
          @preview="previewUndo"
          @confirm="confirmUndo"
          @close="night.clearUndoPreview()"
        />
      </template>
      <p v-else class="inline-note">本夜没有待处理任务。</p>
    </div>

    <div class="night-task-warning" aria-live="polite">
      <span v-if="omissions.length">还有 {{ omissions.length }} 项未完成：{{ omissions.map(omissionLabel).join('；') }}</span>
      <span v-else-if="error">{{ nightErrorMessage(error) }}</span>
    </div>
  </div>
</template>
