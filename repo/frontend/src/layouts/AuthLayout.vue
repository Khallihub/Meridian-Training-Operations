<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
import { Sun, Moon } from 'lucide-vue-next'

const ui = useUiStore()
</script>

<template>
  <div class="min-h-screen bg-background flex items-center justify-center p-4">
    <div class="absolute top-4 right-4">
      <button
        @click="ui.toggleTheme"
        class="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        :title="ui.theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
      >
        <Sun v-if="ui.theme === 'dark'" class="h-5 w-5" />
        <Moon v-else class="h-5 w-5" />
      </button>
    </div>
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-foreground">Meridian Training</h1>
        <p class="text-muted-foreground mt-1">Operations System</p>
      </div>
      <div class="bg-card border border-border rounded-lg shadow-sm p-8">
        <slot />
      </div>
    </div>
  </div>
</template>
