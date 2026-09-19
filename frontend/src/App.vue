<script setup>
import JoinPage from './pages/JoinPage.vue'

function onJoined() {
  window.location.href = '/legacy/'
}
</script>

<template>
  <div data-app-shell>
    <JoinPage @joined="onJoined" />
  </div>
</template>
