<script setup>
import { computed, ref } from 'vue'
import { teamLabel } from '../../presentation/player.js'
import { roleIconUrl } from '../../presentation/roleIcons.js'

const props = defineProps({ view: { type: Object, required: true } })
const hidden = ref(false)

const traveler = computed(() => props.view.traveler || null)
const role = computed(() => traveler.value?.role || props.view.role_changed || props.view.me?.role || null)
const team = computed(() => traveler.value?.align || props.view.team_changed || props.view.me?.role?.team || null)
const roleIcon = computed(() => roleIconUrl(role.value?.id))
const joinedLabel = computed(() => {
  if (!traveler.value) return ''
  const phase = traveler.value.joined_phase === 'day' ? '天' : '夜'
  return `第 ${traveler.value.joined_no} ${phase}加入`
})

const compositionLabels = ['镇民', '外来者', '爪牙', '恶魔']
const meetingLine = (items) => (items || []).map((item) => `${item.seat}号${item.name ? ` ${item.name}` : ''}`).join(' · ')
</script>

<template>
  <section class="identity-section">
    <div v-if="!role" class="identity-waiting">
      <p>{{ view.status === 'lobby' ? '已入座，等待说书人开始游戏…' : '等待说书人分配角色…' }}</p>
    </div>

    <button v-else-if="hidden" data-role-cover class="role-cover" type="button" @click="hidden = false">
      <span>🃏</span>
      <strong>身份已隐藏</strong>
      <small>点击恢复</small>
    </button>

    <template v-else>
      <button data-role-card class="role-card" :data-team="team" type="button" @click="hidden = true">
        <span class="role-team">{{ traveler ? `旅行者 · ${teamLabel(team)}` : teamLabel(team) }}</span>
        <img v-if="roleIcon" class="role-icon" :src="roleIcon" alt="" width="96" height="96" />
        <span v-if="role.en" class="role-en">{{ role.en }}</span>
        <strong>{{ role.name }}</strong>
        <span class="role-ability">{{ role.ability }}</span>
        <small v-if="traveler">{{ joinedLabel }} · 阵营只有你和说书人知道</small>
        <small v-if="(traveler || view.me)?.alive === false">☠ 你已死亡，白天仍可发言</small>
        <small>点击隐藏身份</small>
      </button>

      <div class="private-facts">
        <p v-if="view.role_changed">🔄 角色转变：你的角色已变为「{{ view.role_changed.name }}」</p>
        <p v-if="view.team_changed">⚖ 阵营转变：你的阵营已变为{{ teamLabel(view.team_changed) }}</p>
        <p v-if="view.bluffs?.length">🧪 伪装：{{ view.bluffs.map((item) => item.name).join(' · ') }}</p>
        <p v-if="view.demon_seats?.length">😈 恶魔：{{ meetingLine(view.demon_seats) }}</p>
        <p v-if="view.minion_seats?.length">🩸 爪牙：{{ meetingLine(view.minion_seats) }}</p>
        <p v-if="view.lunatic_seats?.length">🩻 疯子：{{ meetingLine(view.lunatic_seats) }}</p>
      </div>
    </template>

    <p v-if="view.my_mad" class="madness-note">🎭 你疯狂了：你必须声称自己是「{{ view.my_mad.role.name }}」，直到说书人解除。</p>

    <div v-if="view.composition?.length === 4" class="public-facts">
      <p>📋 {{ view.script }} · {{ view.player_count }} 人</p>
      <p>{{ compositionLabels.map((label, index) => `${label} ${view.composition[index]}`).join(' · ') }}</p>
      <p v-if="view.sentinel">🧙 哨兵在场：外来者数量可能比官方配比 +1 或 −1，也可能不变。</p>
      <p v-if="view.fabled?.length">🧙 传奇角色：{{ view.fabled.map((item) => item.name).join(' · ') }}</p>
    </div>
  </section>
</template>

<style scoped>
.identity-section { display: grid; gap: 12px; }
.identity-waiting, .public-facts, .private-facts, .madness-note { padding: 13px; border: 1px solid var(--line); border-radius: 14px; background: var(--panel); }
.role-card, .role-cover { width: 100%; min-height: 220px; padding: 20px; display: grid; place-items: center; gap: 10px; border: 2px solid var(--line); border-radius: 20px; background: color-mix(in srgb, var(--panel) 88%, var(--surface-tint)); color: var(--text); text-align: center; }
.role-card { --team-color: var(--line); border-color: var(--team-color); }
.role-card[data-team='townsfolk'], .role-card[data-team='outsider'], .role-card[data-team='good'] { --team-color: #3685c5; }
.role-card[data-team='minion'], .role-card[data-team='demon'], .role-card[data-team='evil'] { --team-color: #cf4149; }
.role-card .role-team { color: var(--team-color); }
.role-cover { border-color: #999da5; border-style: dashed; color: var(--dim); }
.role-card strong { font-size: 30px; }
.role-icon { width: 96px; height: 96px; object-fit: contain; }
.role-team { font-weight: 700; }
.role-en, .role-card small, .role-ability, .public-facts { color: var(--dim); }
.role-ability { line-height: 1.65; }
.role-cover span { font-size: 42px; }
.private-facts, .public-facts { display: grid; gap: 7px; font-size: 13px; line-height: 1.5; }
.madness-note { border-color: #8a5dab; color: #e5c2ff; line-height: 1.5; }
</style>
