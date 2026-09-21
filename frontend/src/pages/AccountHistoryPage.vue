<script setup>
import { onMounted, ref } from 'vue'
import { api } from '../services/api.js'

const emit = defineEmits(['back'])
const records = ref(null)
const error = ref('')

async function load() {
  error.value = ''
  try {
    records.value = await api('/api/account/history')
  } catch (cause) {
    error.value = cause.message || '历史读取失败'
  }
}

onMounted(load)

function resultLabel(record) {
  if (!record.finished) return '未结算'
  return record.winner === 'good' ? '善良获胜' : '邪恶获胜'
}
</script>

<template>
  <main data-account-history class="page account-history">
    <header class="history-header">
      <button data-history-back class="btn" type="button" @click="emit('back')">返回本局</button>
      <h1>我的对局历史</h1>
    </header>
    <p class="inline-note">仅显示你自己账户参与的对局；推测历史只供本人查看。</p>
    <p v-if="error" class="error" role="alert">{{ error }} <button class="btn" type="button" @click="load">重试</button></p>
    <p v-else-if="records === null">读取中…</p>
    <p v-else-if="!records.length">还没有归档的对局。</p>
    <article v-for="record in records || []" :key="record.game_id" class="history-card">
      <h2>{{ record.script_id || '未知剧本' }} · {{ resultLabel(record) }}</h2>
      <p>座位：{{ record.seat ? `${record.seat} 号` : '未入座' }}</p>
      <p>角色：{{ record.roles?.length ? record.roles.map((role) => role.name).join(' → ') : '未分配' }}</p>
      <p>我的推测：{{ record.guesses?.length ? `${record.guesses.length} 条` : '暂无' }}</p>
      <details v-if="record.guesses?.length">
        <summary>查看我的推测记录</summary>
        <p v-for="item in record.guesses" :key="item.seq">{{ item.target }}号 · {{ item.category === 'role' ? '角色' : item.category === 'alignment' ? '阵营' : item.category === 'status' ? '状态' : '变化' }} · {{ item.data?.role || item.data?.alignment || item.data?.status || item.data?.kind || '已清除' }} · {{ ({ correct: '正确', incorrect: '错误', unverified: '无法核对' })[item.verdict] || '未结算' }}</p>
      </details>
    </article>
  </main>
</template>
