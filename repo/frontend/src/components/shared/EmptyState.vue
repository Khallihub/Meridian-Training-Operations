<script setup lang="ts">
defineProps<{ title?: string; description?: string }>()
</script>

<template>
  <div class="flex flex-col items-center justify-center py-16 text-center">
    <div class="h-16 w-16 rounded-full bg-muted flex items-center justify-center mb-4">
      <slot name="icon">
        <svg class="h-8 w-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0H4" />
        </svg>
      </slot>
    </div>
    <h3 class="text-sm font-medium text-foreground">{{ title ?? 'No results' }}</h3>
    <p v-if="description" class="text-sm text-muted-foreground mt-1">{{ description }}</p>
    <div class="mt-4">
      <slot />
    </div>
  </div>
</template>
