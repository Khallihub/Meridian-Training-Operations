<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()

onMounted(() => {
  // Apply persisted or system-preferred theme
  if (ui.theme === 'dark' || (!ui.theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    document.documentElement.classList.add('dark')
    ui.theme = 'dark'
  } else {
    document.documentElement.classList.remove('dark')
    ui.theme = 'light'
  }
})
</script>

<template>
  <RouterView />
</template>
