<script setup>
import { ref } from 'vue'
import StorytellerLiveView from '../components/storyteller/StorytellerLiveView.vue'
import StorytellerLogin from '../components/storyteller/StorytellerLogin.vue'
import { getStorytellerPassword } from '../services/session.js'

const password = ref(getStorytellerPassword())
</script>

<template>
  <div data-storyteller-page>
    <StorytellerLiveView
      v-if="password"
      :key="password"
      :password="password"
      @auth-failure="password = null"
    />
    <StorytellerLogin v-else @authenticated="password = $event" />
  </div>
</template>
