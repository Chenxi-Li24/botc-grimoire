<script setup>
import { useStorytellerView } from '../../composables/useStorytellerView.js'

const props = defineProps({ password: { type: String, required: true } })
const emit = defineEmits(['auth-failure'])
const { view, connectionStatus } = useStorytellerView(props.password, {
  onAuthFailure: () => emit('auth-failure'),
})
</script>

<template>
  <main data-storyteller-live class="page center">
    <template v-if="view">
      <h1>说书人桌面版预览</h1>
      <p>房间 {{ view.room_code }}</p>
      <p>{{ connectionStatus }}</p>
      <a class="btn" href="/legacy/#/storyteller">打开完整控制台</a>
    </template>
    <p v-else>连接魔典…</p>
  </main>
</template>
